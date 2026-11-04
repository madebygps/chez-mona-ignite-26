"""Fridge order numbers, kept in a small file so they survive restarts."""

from __future__ import annotations

import threading
from pathlib import Path


class OrderCounter:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()

    def last(self) -> int:
        try:
            return int(self.path.read_text(encoding="utf-8").strip() or 0)
        except (FileNotFoundError, ValueError):
            return 0

    def issue(self, use) -> object:
        """Call use(number) with the next number and keep it only if use succeeds,
        so a failed print gives the same number to the next attempt."""
        with self.lock:
            number = self.last() % 999 + 1
            result = use(number)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(str(number), encoding="utf-8")
            return result
