import contextlib
import http.client
import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from chez_mona import printer
from chez_mona.config import StationConfig
from chez_mona.server import Launcher, make_server, parse_args


class FakeSessions:
    def __init__(self):
        self.calls = []

    def start(self):
        self.calls.append("start")
        return {"folder": "x"}

    def reopen(self):
        self.calls.append("reopen")
        return {}

    def end(self):
        self.calls.append("end")
        return {"ended": False}

    def sweep(self):
        return []


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        # Never touch a real printer from the tests.
        cls.printer_patch = mock.patch.object(printer, "submit_usb", lambda data, match: None)
        cls.printer_patch.start()
        config = StationConfig(state_dir=Path(cls.tmp.name))
        cls.sessions = FakeSessions()
        cls.server = make_server(Launcher(config, sessions=cls.sessions), 0)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.printer_patch.stop()
        cls.tmp.cleanup()

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {"Host": f"localhost:{self.port}", **(headers or {})}
        payload = None
        if body is not None:
            payload = json.dumps(body)
            headers.setdefault("Content-Type", "application/json")
        conn.request(method, path, payload, headers)
        response = conn.getresponse()
        data = response.read()
        conn.close()
        return response.status, response.getheader("Content-Type"), data

    def test_port_in_use_is_refused(self):
        config = StationConfig(state_dir=Path(self.tmp.name), role="fridge")
        with self.assertRaises(OSError):
            make_server(Launcher(config, sessions=FakeSessions()), self.port).server_close()

    def test_labs_and_static(self):
        status, _, data = self.request("GET", "/api/labs")
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(data)["dishes"]), 4)
        status, content_type, _ = self.request("GET", "/")
        self.assertEqual((status, content_type), (200, "text/html; charset=utf-8"))

    def test_rejects_other_hosts_and_traversal(self):
        self.assertEqual(self.request("GET", "/api/labs", headers={"Host": "evil.example"})[0], 403)
        self.assertEqual(self.request("GET", "/../chez_mona/server.py")[0], 404)
        self.assertEqual(self.request("GET", "/%2e%2e/station.example.json")[0], 404)

    def test_post_requires_json(self):
        status, _, _ = self.request("POST", "/api/session/end", "{}", {"Content-Type": "text/plain"})
        self.assertEqual(status, 403)

    def test_start_routes_by_dish(self):
        self.sessions.calls.clear()
        self.assertEqual(self.request("POST", "/api/session/start", {"dish": "fried-chicken"})[0], 200)
        self.assertEqual(self.request("POST", "/api/session/start", {"dish": "dip"})[0], 200)
        self.assertEqual(self.sessions.calls, ["start", "end"])
        self.assertEqual(self.request("POST", "/api/session/start", {"dish": "pizza"})[0], 400)

    def test_print_sends_receipt(self):
        status, _, data = self.request("POST", "/api/print", {"dish": "omelette"})
        first = json.loads(data)
        self.assertEqual((status, first["status"]), (200, "sent"))
        self.assertEqual(self.request("POST", "/api/print", {"dish": "pizza"})[0], 400)
        status, _, data = self.request("POST", "/api/print", {"dish": "soup", "hints": [0, 2]})
        self.assertEqual(status, 200)
        self.assertEqual(int(json.loads(data)["check"]), int(first["check"]) + 1)
        for hints in ([0], [0, -1], [0, 9], [0, "1"], [True, 0], "0,0"):
            self.assertEqual(self.request("POST", "/api/print", {"dish": "soup", "hints": hints})[0], 400, hints)

    def test_ticket_numbers_advance_only_on_success(self):
        launcher = self.server.RequestHandlerClass.launcher
        first = json.loads(self.request("POST", "/api/ticket", {"dish": "soup"})[2])
        self.assertEqual(first["status"], "sent")
        self.assertEqual(self.request("POST", "/api/ticket", {"dish": "pizza"})[0], 400)

        def fail(number):
            raise RuntimeError("printer off")

        with self.assertRaises(RuntimeError):
            launcher.orders.issue(fail)
        second = json.loads(self.request("POST", "/api/ticket", {"dish": "dip"})[2])
        self.assertEqual(int(second["order"]), int(first["order"]) + 1)

    def test_fridge_role_serves_fridge_page(self):
        launcher = self.server.RequestHandlerClass.launcher
        launcher.config.role = "fridge"
        try:
            _, _, data = self.request("GET", "/")
            self.assertIn(b"fridge.js", data)
        finally:
            launcher.config.role = "station"
        _, _, data = self.request("GET", "/")
        self.assertIn(b"app.js", data)

    def test_print_uses_configured_connection(self):
        launcher = self.server.RequestHandlerClass.launcher
        sent = []
        with mock.patch.object(printer, "submit_usb", lambda data, match: sent.append(("usb", match)) or {}), \
                mock.patch.object(printer, "submit_raw", lambda queue, data, title: sent.append(("queue", queue)) or 7):
            self.assertEqual(json.loads(self.request("POST", "/api/print", {"dish": "dip"})[2])["status"], "sent")
            with mock.patch.object(launcher.config, "printer_connection", "queue"):
                result = json.loads(self.request("POST", "/api/ticket", {"dish": "dip"})[2])
        self.assertEqual(result["job"], 7)
        self.assertEqual(sent, [("usb", ""), ("queue", "Chez Mona Receipt")])

    def test_printer_status_reports_errors(self):
        def missing(match):
            raise printer.PrintError("No USB receipt printer is connected.")

        with mock.patch.object(printer, "usb_status", missing):
            status = json.loads(self.request("GET", "/api/printer")[2])
        self.assertEqual(status["printer"], "USB printer")
        self.assertIn("No USB receipt printer", status["error"])


if __name__ == "__main__":
    unittest.main()


class ParseArgsTest(unittest.TestCase):
    def test_role_from_command_line(self):
        config, port = parse_args(["--role", "station", "--port", "9000"])
        self.assertEqual((config.role, port), ("station", 9000))
        config, port = parse_args(["--role", "fridge"])
        self.assertEqual((config.role, port), ("fridge", 8766))
        _, port = parse_args(["--role", "station"])
        self.assertEqual(port, 8765)
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parse_args(["--role", "oven"])
