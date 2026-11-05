"""Station configuration: the role and number given on the command line."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

LAUNCHER_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = LAUNCHER_DIR.parent
ROLES = ("station", "fridge")
DEFAULT_PORTS = {"station": 8765, "fridge": 8766}


def default_state_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "ChezMona"


def clean_number(number: str) -> str:
    """The laptop's number, 1 to 6 for a station or A or B for a fridge."""
    number = str(number).strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{0,3}", number):
        raise ValueError("The number must be up to 3 letters or digits, for example 3 or A")
    return number


@dataclass
class StationConfig:
    role: str = "station"
    number: str = ""
    idle_seconds: dict = field(
        default_factory=lambda: {"default": 120, "explore": 600, "prompt": 30}
    )
    state_dir: Path = field(default_factory=default_state_dir)

    def __post_init__(self):
        if self.role not in ROLES:
            raise ValueError(f"role must be one of: {', '.join(ROLES)}")
        self.number = clean_number(self.number)

    def station_name(self) -> str:
        """Printed on the receipt's guest check."""
        return f"Station {self.number}" if self.role == "station" and self.number else ""

    def server_port(self) -> int:
        """The role's own port, so a station and a fridge never clash on one laptop."""
        return DEFAULT_PORTS[self.role]

    def public(self) -> dict:
        """Settings the browser page needs."""
        return {
            "role": self.role,
            "idle_seconds": self.idle_seconds,
        }
