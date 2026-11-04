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


def default_state_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "ChezMona"


@dataclass
class StationConfig:
    port: int = 8765
    role: str = "station"
    fridge_number: int = 1
    dry_run: bool = True
    printer_queue: str = "Chez Mona Receipt"
    paper_mm: int = 80
    print_width_dots: int = 576
    code_path: str = ""
    idle_seconds: dict = field(
        default_factory=lambda: {"default": 120, "explore": 600, "prompt": 30}
    )
    out_dir: Path = LAUNCHER_DIR / "out"
    state_dir: Path = field(default_factory=default_state_dir)

    @classmethod
    def load(cls, path: Path | None = None) -> "StationConfig":
        path = path or (STATION_FILE if STATION_FILE.exists() else EXAMPLE_FILE)
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        config = cls()
        for key, value in data.items():
            if key == "idle_seconds":
                config.idle_seconds = {**config.idle_seconds, **value}
            elif key in ("out_dir", "state_dir"):
                setattr(config, key, Path(value))
            elif hasattr(config, key):
                setattr(config, key, value)
            else:
                raise ValueError(f"Unknown station setting: {key}")
        if config.print_width_dots % 8:
            raise ValueError("print_width_dots must be a multiple of 8")
        if config.role not in ROLES:
            raise ValueError(f"role must be one of: {', '.join(ROLES)}")
        return config

    def public(self) -> dict:
        """Settings the browser page needs."""
        return {
            "role": self.role,
            "fridge_number": self.fridge_number,
            "dry_run": self.dry_run,
            "idle_seconds": self.idle_seconds,
        }
