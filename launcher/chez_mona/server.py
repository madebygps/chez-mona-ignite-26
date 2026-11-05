"""Local HTTP server for the launcher page. Binds to 127.0.0.1 only."""

from __future__ import annotations

import argparse
import json
import mimetypes
import socket
import sys
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from . import labs, printer, receipt
from .config import LAUNCHER_DIR, ROLES, StationConfig

from .sdk_session import SdkSessions, SessionError

STATIC_DIR = LAUNCHER_DIR / "static"
ALLOWED_HOSTS = {"localhost", "127.0.0.1"}
HOME_PAGE = {"station": "index.html", "fridge": "fridge.html"}
MAX_BODY = 64 * 1024


def check_hints(hints, questions: int) -> list[int] | None:
    """Wrong answers per question from the quiz page. None when the page did not send them."""
    if hints is None:
        return None
    valid = (isinstance(hints, list) and len(hints) == questions
             and all(type(n) is int and 0 <= n <= 3 for n in hints))
    if not valid:
        raise LookupError(f"hints must list wrong answers (0 to 3) for each of the {questions} questions")
    return hints


class Launcher:
    """Everything the request handler needs, shared across threads."""

    def __init__(self, config: StationConfig, sessions: SdkSessions | None = None):
        self.config = config
        self.content = labs.load()
        self.dishes = labs.by_id(self.content)
        self.sessions = sessions or SdkSessions()

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

    def print_receipt(self, dish_id: str, hints=None) -> dict:
        dish = self.dish(dish_id)
        hints = check_hints(hints, len(dish["quiz"]))
        job = printer.submit_usb(receipt.escpos(dish, receipt.Check(datetime.now(), hints)))
        return {"status": "sent", "job": job}

    def print_ticket(self, dish_id: str) -> dict:
        dish = self.dish(dish_id)
        job = printer.submit_usb(receipt.ticket_escpos(dish, datetime.now()))
        return {"status": "sent", "job": job}

    def printer_status(self) -> dict:
        info = {"printer": "USB printer", "problems": []}
        try:
            info.update(printer.usb_status())
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
        length = min(int(self.headers.get("Content-Length") or 0), MAX_BODY)
        # Read the body even when rejecting, or Windows resets the connection
        # before the client sees the response.
        raw = self.rfile.read(length)
        # A JSON content type forces a CORS preflight, which this server never
        # answers, so other sites cannot drive these endpoints from a browser.
        if not self._host_ok() or not (self.headers.get("Content-Type") or "").startswith("application/json"):
            return self._json(HTTPStatus.FORBIDDEN, {"error": "Forbidden"})
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return self._json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON"})
        routes = {
            "/api/session/start": lambda: self.launcher.start(body.get("dish", "")),
            "/api/session/reopen": self.launcher.sessions.reopen,
            "/api/session/end": self.launcher.sessions.end,
            "/api/print": lambda: self.launcher.print_receipt(body.get("dish", ""), body.get("hints")),
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


class LauncherServer(ThreadingHTTPServer):
    # On Windows, SO_REUSEADDR lets a second launcher share a busy port, so claim it exclusively.
    allow_reuse_address = sys.platform != "win32"

    def server_bind(self) -> None:
        if sys.platform == "win32":
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def make_server(launcher: Launcher, port: int) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"launcher": launcher})
    return LauncherServer(("127.0.0.1", port), handler)


def parse_args(argv: list[str] | None = None) -> tuple[StationConfig, int]:
    parser = argparse.ArgumentParser(description="Chez Mona lab launcher")
    parser.add_argument("--role", choices=ROLES, default="station", help="station or fridge")
    parser.add_argument("--port", type=int, help="override the role's default port")
    args = parser.parse_args(argv)
    config = StationConfig(role=args.role)
    return config, args.port or config.server_port()


def main(argv: list[str] | None = None) -> None:
    config, port = parse_args(argv)
    launcher = Launcher(config)
    if config.role == "station":
        removed = launcher.sessions.sweep()
        if removed:
            print(f"Removed {len(removed)} leftover starter folder(s).")
    try:
        server = make_server(launcher, port)
    except OSError as exc:
        sys.exit(f"Port {port} is already in use ({exc.strerror}). Close the other Chez Mona window first.")
    role = "fridge" if config.role == "fridge" else "cooking station"
    print(f"Chez Mona {role} on http://localhost:{port}, printing to the USB printer. Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        launcher.sessions.end()
        server.server_close()


if __name__ == "__main__":
    main()
