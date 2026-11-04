"""Local HTTP server for the launcher page. Binds to 127.0.0.1 only."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import sys
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import labs, printer, receipt
from .config import LAUNCHER_DIR, ROLES, StationConfig
from .orders import OrderCounter
from .sdk_session import SdkSessions, SessionError

STATIC_DIR = LAUNCHER_DIR / "static"
ALLOWED_HOSTS = {"localhost", "127.0.0.1"}
HOME_PAGE = {"station": "index.html", "fridge": "fridge.html"}


class Launcher:
    """Everything the request handler needs, shared across threads."""

    def __init__(self, config: StationConfig, sessions: SdkSessions | None = None):
        self.config = config
        self.content = labs.load()
        self.dishes = labs.by_id(self.content)
        self.sessions = sessions or SdkSessions(code_path=config.code_path)
        self.orders = OrderCounter(config.state_dir / f"fridge-{config.fridge_number}-order.txt")

    def dish(self, dish_id: str) -> dict:
        if dish_id not in self.dishes:
            raise LookupError(f"Unknown dish: {dish_id}")
        return self.dishes[dish_id]

    def start(self, dish_id: str) -> dict:
        dish = self.dish(dish_id)
        if dish["start"]["type"] == "sdk":
            return self.sessions.start()
        # Another dish starting means any earlier starter folder is abandoned.
        self.sessions.end()
        return {}

    def print_receipt(self, dish_id: str) -> dict:
        dish = self.dish(dish_id)
        width = self.config.print_width_dots
        data = receipt.escpos(dish, width)
        preview = f"/api/receipt-preview?dish={dish_id}"
        if self.config.dry_run:
            saved = printer.save_dry_run(self.config.out_dir, dish_id, data, receipt.preview_png(dish, width))
            return {"status": "dry_run", "saved": str(saved), "preview": preview}
        job = self.send(data, f"Chez Mona receipt: {dish['dish']}")
        return {"status": "sent", "job": job, "preview": preview}

    def send(self, data: bytes, title: str):
        if self.config.printer_connection == "queue":
            return printer.submit_raw(self.config.printer_queue, data, title)
        return printer.submit_usb(data, self.config.printer_usb_match)

    def print_ticket(self, dish_id: str) -> dict:
        dish = self.dish(dish_id)
        width = self.config.print_width_dots

        def use(number: int) -> dict:
            order = receipt.Order(self.config.fridge_number, number, datetime.now())
            data = receipt.ticket_escpos(dish, order, width)
            png = receipt.ticket_png(dish, order, width)
            result = {"order": order.label(), "preview": "data:image/png;base64," + base64.b64encode(png).decode()}
            if self.config.dry_run:
                saved = printer.save_dry_run(self.config.out_dir, f"ticket-{dish_id}", data, png)
                return {**result, "status": "dry_run", "saved": str(saved)}
            job = self.send(data, f"Chez Mona ticket {order.label()}: {dish['dish']}")
            return {**result, "status": "sent", "job": job}

        return self.orders.issue(use)

    def printer_status(self) -> dict:
        info = {"dry_run": self.config.dry_run, "printer": self.config.printer_label(), "problems": []}
        try:
            if self.config.printer_connection == "queue":
                info.update(printer.queue_status(self.config.printer_queue))
            else:
                info.update(printer.usb_status(self.config.printer_usb_match))
        except printer.PrintError as exc:
            info["error"] = str(exc)
        return info


class Handler(BaseHTTPRequestHandler):
    launcher: Launcher
    server_version = "ChezMona/1"

    def log_message(self, fmt, *args):
        if self.path.startswith("/api/") and self.command == "POST":
            sys.stderr.write(f"{self.command} {self.path} {args[1] if len(args) > 1 else ''}\n")

    def _host_ok(self) -> bool:
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        return host in ALLOWED_HOSTS

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: dict) -> None:
        self._send(status, json.dumps(payload).encode("utf-8"), "application/json")

    def do_GET(self):
        if not self._host_ok():
            return self._json(HTTPStatus.FORBIDDEN, {"error": "Forbidden host"})
        url = urlparse(self.path)
        if url.path == "/api/labs":
            return self._json(HTTPStatus.OK, {
                "dishes": self.launcher.content["dishes"],
                "station": self.launcher.config.public(),
            })
        if url.path == "/api/printer":
            return self._json(HTTPStatus.OK, self.launcher.printer_status())
        if url.path == "/api/receipt-preview":
            dish_id = parse_qs(url.query).get("dish", [""])[0]
            try:
                dish = self.launcher.dish(dish_id)
            except LookupError as exc:
                return self._json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
            png = receipt.preview_png(dish, self.launcher.config.print_width_dots)
            return self._send(HTTPStatus.OK, png, "image/png")
        return self._static(url.path)

    def _static(self, path: str) -> None:
        relative = HOME_PAGE[self.launcher.config.role] if path in ("/", "") else path.lstrip("/")
        target = (STATIC_DIR / relative).resolve()
        if not target.is_relative_to(STATIC_DIR.resolve()) or not target.is_file():
            return self._json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type.endswith("javascript"):
            content_type += "; charset=utf-8"
        self._send(HTTPStatus.OK, target.read_bytes(), content_type)

    def do_POST(self):
        # A JSON content type forces a CORS preflight, which this server never
        # answers, so other sites cannot drive these endpoints from a browser.
        if not self._host_ok() or not (self.headers.get("Content-Type") or "").startswith("application/json"):
            return self._json(HTTPStatus.FORBIDDEN, {"error": "Forbidden"})
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON"})
        routes = {
            "/api/session/start": lambda: self.launcher.start(body.get("dish", "")),
            "/api/session/reopen": self.launcher.sessions.reopen,
            "/api/session/end": self.launcher.sessions.end,
            "/api/print": lambda: self.launcher.print_receipt(body.get("dish", "")),
            "/api/ticket": lambda: self.launcher.print_ticket(body.get("dish", "")),
        }
        route = routes.get(urlparse(self.path).path)
        if not route:
            return self._json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
        try:
            return self._json(HTTPStatus.OK, route())
        except LookupError as exc:
            return self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except (SessionError, printer.PrintError) as exc:
            return self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
        except Exception as exc:  # Surface anything unexpected to staff instead of hanging.
            return self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"{type(exc).__name__}: {exc}"})


def make_server(launcher: Launcher, port: int) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"launcher": launcher})
    return ThreadingHTTPServer(("127.0.0.1", port), handler)


def parse_args(argv: list[str] | None = None) -> tuple[StationConfig, int]:
    parser = argparse.ArgumentParser(description="Chez Mona lab launcher")
    parser.add_argument("--config", type=Path, help="station config file (default: station.json)")
    parser.add_argument("--port", type=int, help="override the configured port")
    parser.add_argument("--role", choices=ROLES, help="override the configured role: station or fridge")
    parser.add_argument("--fridge", type=int, choices=range(1, 100), metavar="N",
                        help="fridge number printed on tickets (implies --role fridge)")
    args = parser.parse_args(argv)
    config = StationConfig.load(args.config)
    if args.role:
        config.role = args.role
    if args.fridge is not None:
        if args.role == "station":
            parser.error("--fridge only applies to a fridge")
        config.role = "fridge"
        config.fridge_number = args.fridge
    return config, args.port or config.port


def main(argv: list[str] | None = None) -> None:
    config, port = parse_args(argv)
    launcher = Launcher(config)
    if config.role == "station":
        removed = launcher.sessions.sweep()
        if removed:
            print(f"Removed {len(removed)} leftover starter folder(s).")
    server = make_server(launcher, port)
    mode = "dry run" if config.dry_run else f"printing to {config.printer_label()}"
    role = f"fridge {config.fridge_number}" if config.role == "fridge" else "cooking station"
    print(f"Chez Mona {role} on http://localhost:{port} ({mode}). Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        launcher.sessions.end()
        server.server_close()


if __name__ == "__main__":
    main()
