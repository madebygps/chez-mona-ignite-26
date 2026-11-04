"""Station configuration: per-laptop settings read from station.json."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

LAUNCHER_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = LAUNCHER_DIR.parent
STATION_FILE = LAUNCHER_DIR / "station.json"
EXAMPLE_FILE = LAUNCHER_DIR / "station.example.json"
ROLES = ("station", "fridge")
DEFAULT_PORTS = {"station": 8765, "fridge": 8766}
CONNECTIONS = ("usb", "queue")


def default_state_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "ChezMona"


@dataclass
class StationConfig:
    port: int | None = None
    role: str = "station"
    printer_connection: str = "usb"
    printer_usb_match: str = ""
    printer_queue: str = "Chez Mona Receipt"
    paper_mm: int = 80
    print_width_dots: int = 576
    code_path: str = ""
    idle_seconds: dict = field(
        default_factory=lambda: {"default": 120, "explore": 600, "prompt": 30}
    )
    state_dir: Path = field(default_factory=default_state_dir)

    @classmethod
    def load(cls, path: Path | None = None) -> "StationConfig":
        path = path or (STATION_FILE if STATION_FILE.exists() else EXAMPLE_FILE)
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        config = cls()
        for key, value in data.items():
            if key == "idle_seconds":
                config.idle_seconds = {**config.idle_seconds, **value}
            elif key == "state_dir":
                config.state_dir = Path(value)
            elif hasattr(config, key):
                setattr(config, key, value)
            else:
                raise ValueError(f"Unknown station setting: {key}")
        if config.print_width_dots % 8:
            raise ValueError("print_width_dots must be a multiple of 8")
        if config.role not in ROLES:
            raise ValueError(f"role must be one of: {', '.join(ROLES)}")
        if config.printer_connection not in CONNECTIONS:
            raise ValueError(f"printer_connection must be one of: {', '.join(CONNECTIONS)}")
        return config

    def server_port(self) -> int:
        """The configured port, or the role's own default so a station and a fridge never clash."""
        return self.port or DEFAULT_PORTS[self.role]

    def printer_label(self) -> str:
        if self.printer_connection == "queue":
            return f"queue '{self.printer_queue}'"
        return "USB printer" + (f" matching '{self.printer_usb_match}'" if self.printer_usb_match else "")

    def public(self) -> dict:
        """Settings the browser page needs."""
        return {
            "role": self.role,
            "idle_seconds": self.idle_seconds,
        }
