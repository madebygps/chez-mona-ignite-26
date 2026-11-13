import contextlib
import http.client
import io
import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from unittest import mock

from PIL import Image

from chez_mona import printer, stats
from chez_mona.config import StationConfig
from chez_mona.server import Launcher, make_server, parse_args


class FakeSessions:
    def __init__(self):
        self.calls = []

    def start(self):
        self.calls.append("start")
        return {"folder": "x"}

    def open_vscode(self):
        self.calls.append("open_vscode")
        return {}

    def end(self):
        self.calls.append("end")
        return {"ended": False}

    def sweep(self):
        return []


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Never touch a real printer from the tests.
        cls.printer_patch = mock.patch.object(printer, "submit_usb", lambda data: None)
        cls.printer_patch.start()
        config = StationConfig()
        cls.sessions = FakeSessions()
        cls.stats_dir = tempfile.TemporaryDirectory()
        cls.stats_path = Path(cls.stats_dir.name) / "events.jsonl"
        cls.server = make_server(Launcher(config, sessions=cls.sessions, stats_path=cls.stats_path), 0)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.printer_patch.stop()
        cls.stats_dir.cleanup()

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
        config = StationConfig(role="fridge")
        with self.assertRaises(OSError):
            make_server(Launcher(config, sessions=FakeSessions()), self.port).server_close()

    def test_labs_and_static(self):
        status, _, data = self.request("GET", "/api/labs")
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(data)["dishes"]), 4)
        status, content_type, _ = self.request("GET", "/")
        self.assertEqual((status, content_type), (200, "text/html; charset=utf-8"))

    def test_launcher_icons(self):
        status, content_type, data = self.request("GET", "/favicon.svg")
        self.assertEqual((status, content_type), (200, "image/svg+xml"))
        self.assertIn(b"<svg", data)
        status, content_type, data = self.request("GET", "/favicon.ico")
        self.assertEqual(status, 200)
        self.assertIn(content_type, ("image/vnd.microsoft.icon", "image/x-icon"))
        with Image.open(io.BytesIO(data)) as icon:
            self.assertEqual(icon.format, "ICO")
            self.assertTrue({
                (16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48),
                (64, 64), (96, 96), (128, 128), (256, 256),
            } <= icon.ico.sizes())

    def test_rejects_other_hosts_and_traversal(self):
        self.assertEqual(self.request("GET", "/api/labs", headers={"Host": "evil.example"})[0], 403)
        self.assertEqual(self.request("GET", "/../chez_mona/server.py")[0], 404)
        self.assertEqual(self.request("GET", "/%2e%2e/pyproject.toml")[0], 404)

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
        status, _, data = self.request("POST", "/api/print", {"dish": "fusilli"})
        self.assertEqual((status, json.loads(data)["status"]), (200, "sent"))
        self.assertEqual(self.request("POST", "/api/print", {"dish": "pizza"})[0], 400)
        self.assertEqual(self.request("POST", "/api/print",         {"dish": "fusilli", "hints": [0, 2]})[0], 200)
        for hints in ([0], [0, -1], [0, 9], [0, "1"], [True, 0], "0,0"):
                    self.assertEqual(self.request("POST", "/api/print", {"dish": "fusilli", "hints": hints})[0], 400, hints)

    def test_print_sends_ticket(self):
        result = json.loads(self.request("POST", "/api/ticket", {"dish": "soup"})[2])
        self.assertEqual(result["status"], "sent")
        self.assertNotIn("order", result)
        self.assertEqual(self.request("POST", "/api/ticket", {"dish": "pizza"})[0], 400)

    def test_fridge_role_serves_fridge_page(self):
        launcher = self.server.RequestHandlerClass.launcher
        launcher.config.role = "fridge"
        try:
            _, _, data = self.request("GET", "/")
            self.assertIn(b"fridge.js", data)
            self.assertIn(b'href="/favicon.svg"', data)
            self.assertIn(b'href="/favicon.ico"', data)
        finally:
            launcher.config.role = "station"
        _, _, data = self.request("GET", "/")
        self.assertIn(b"app.js", data)
        self.assertIn(b'href="/favicon.svg"', data)
        self.assertIn(b'href="/favicon.ico"', data)

    def test_print_sends_the_receipt(self):
        sent = []
        with mock.patch.object(printer, "submit_usb", lambda data: sent.append(data) or {}):
            result = json.loads(self.request("POST", "/api/print", {"dish": "dip"})[2])
        self.assertNotIn("check", result)
        self.assertIn(b"AUTOFIX ARTICHOKE DIP", sent[0])
        self.assertNotIn(b"No.", sent[0])
        self.assertTrue(result["image"].startswith("data:image/png;base64,"))

    def test_receipt_numbers_continue_across_dishes_days_and_restarts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            stats.record("receipt", "soup", path, datetime(2026, 1, 1))
            stats.record("completed", "soup", path)
            launcher = Launcher(StationConfig(), sessions=FakeSessions(), stats_path=path)
            with mock.patch.object(printer, "submit_usb") as submit:
                launcher.print_receipt("dip")
                self.assertIn(b"Receipt #002", submit.call_args.args[0])
                submit.side_effect = printer.PrintError("Out of paper")
                with self.assertRaises(printer.PrintError):
                    launcher.print_receipt("soup")
                submit.side_effect = None
                launcher = Launcher(StationConfig(), sessions=FakeSessions(), stats_path=path)
                launcher.print_receipt("dip")
                self.assertIn(b"Receipt #003", submit.call_args.args[0])

    def test_concurrent_receipts_get_separate_numbers(self):
        with tempfile.TemporaryDirectory() as directory:
            launcher = Launcher(StationConfig(), sessions=FakeSessions(),
                                stats_path=Path(directory) / "events.jsonl")
            with mock.patch.object(printer, "submit_usb") as submit:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    list(pool.map(launcher.print_receipt, ["soup", "dip"]))
                self.assertIn(b"Receipt #001", submit.call_args_list[0].args[0])
                self.assertIn(b"Receipt #002", submit.call_args_list[1].args[0])

    def test_printer_status_reports_errors(self):
        def missing():
            raise printer.PrintError("No USB receipt printer is connected.")

        with mock.patch.object(printer, "usb_status", missing):
            status = json.loads(self.request("GET", "/api/printer")[2])
        self.assertEqual(status["printer"], "USB printer")
        self.assertIn("No USB receipt printer", status["error"])

    def test_stats_count_starts_completions_and_receipts(self):
        def today(dish_id):
            labs = json.loads(self.request("GET", "/api/stats")[2])["labs"]
            return next(lab for lab in labs if lab["id"] == dish_id)

        before = today("soup")
        self.request("POST", "/api/session/start", {"dish": "soup"})
        self.assertEqual(self.request("POST", "/api/complete", {"dish": "soup"})[0], 200)
        self.assertEqual(self.request("POST", "/api/complete", {"dish": "pizza"})[0], 400)
        self.request("POST", "/api/print", {"dish": "soup"})

        def broken(data):
            raise printer.PrintError("Out of paper")

        with mock.patch.object(printer, "submit_usb", broken):
            self.request("POST", "/api/print", {"dish": "soup"})
        after = today("soup")
        for event in ("started", "completed", "receipt"):
            self.assertEqual(after[event], before[event] + 1, event)


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
            for bad in (["--role", "oven"],):
                with self.assertRaises(SystemExit, msg=bad):
                    parse_args(bad)
