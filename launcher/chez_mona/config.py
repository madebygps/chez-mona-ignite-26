"""Station configuration: the role, and a fridge's letter, given on the command line."""

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


def clean_letter(letter: str) -> str:
    """A fridge's letter, A or B, which prefixes its order numbers."""
    letter = str(letter).strip().upper()
    if not re.fullmatch(r"[A-Z]?", letter):
        raise ValueError("The fridge letter must be one letter, for example A")
    return letter


@dataclass
class StationConfig:
    role: str = "station"
    letter: str = ""
    idle_seconds: dict = field(
        default_factory=lambda: {"default": 120, "explore": 600, "prompt": 30}
    )
    state_dir: Path = field(default_factory=default_state_dir)

    def __post_init__(self):
        if self.role not in ROLES:
            raise ValueError(f"role must be one of: {', '.join(ROLES)}")
        self.letter = clean_letter(self.letter)
        if self.letter and self.role != "fridge":
            raise ValueError("Only fridges take a letter")

    def server_port(self) -> int:
        """The role's own port, so a station and a fridge never clash on one laptop."""
        return DEFAULT_PORTS[self.role]

    def public(self) -> dict:
        """Settings the browser page needs."""
        return {
            "role": self.role,
            "idle_seconds": self.idle_seconds,
        }
