"""Lab stats for this laptop: an append-only event log and a daily summary.

Run `uv run python -m chez_mona.stats` from launcher/ to print today's counts.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import threading
from datetime import date, datetime
from pathlib import Path

from . import labs
from .config import LAUNCHER_DIR

LOG_PATH = LAUNCHER_DIR / "data" / "events.jsonl"
EVENTS = ("started", "completed", "receipt")

_lock = threading.Lock()


def record(event: str, dish_id: str, path: Path = LOG_PATH, when: datetime | None = None) -> None:
    """Add one event to the log. A logging failure never stops the guest flow."""
    line = json.dumps({"time": (when or datetime.now()).isoformat(timespec="seconds"),
                       "event": event, "dish": dish_id}) + "\n"
    try:
        with _lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a+b") as f:
                if f.tell():
                    f.seek(-1, 2)
                    if f.read(1) != b"\n":
                        line = "\n" + line  # a crash left a half line; keep this event on its own
                f.write(line.encode("utf-8"))
    except OSError as exc:
        print(f"Could not write lab stats: {exc}", file=sys.stderr)


def read(path: Path = LOG_PATH) -> list[dict]:
    if not path.is_file():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue  # a line cut short by a crash
        if isinstance(event, dict) and event.get("event") in EVENTS:
            events.append(event)
    return events


def summary(dish_ids: list[str], path: Path = LOG_PATH, day: date | None = None) -> dict[str, dict[str, int]]:
    """Counts per dish and event, for one day or (day=None) for all days."""
    counts = {d: dict.fromkeys(EVENTS, 0) for d in dish_ids}
    prefix = day.isoformat() if day else ""
    for event in read(path):
        if str(event.get("time", "")).startswith(prefix):
            counts.setdefault(event.get("dish"), dict.fromkeys(EVENTS, 0))[event["event"]] += 1
    return counts


def table(counts: dict[str, dict[str, int]], names: dict[str, str]) -> str:
    """A Markdown table, ready to paste into a GitHub issue."""
    rows = ["| Lab | Started | Completed | Receipts |", "|---|---:|---:|---:|"]
    totals = dict.fromkeys(EVENTS, 0)
    for dish_id, c in sorted(counts.items(), key=lambda item: -item[1]["completed"]):
        rows.append(f"| {names.get(dish_id, dish_id)} | {c['started']} | {c['completed']} | {c['receipt']} |")
        for e in EVENTS:
            totals[e] += c[e]
    rows.append(f"| **Total** | **{totals['started']}** | **{totals['completed']}** | **{totals['receipt']}** |")
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Show Chez Mona lab stats for this laptop")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--day", type=date.fromisoformat, help="a day as YYYY-MM-DD (default: today)")
    group.add_argument("--all", action="store_true", help="every day in the log")
    args = parser.parse_args(argv)
    day = None if args.all else (args.day or date.today())
    dishes = labs.load()["dishes"]
    counts = summary([d["id"] for d in dishes], day=day)
    names = {d["id"]: d["dish"] for d in dishes}
    print(f"Chez Mona lab stats: {socket.gethostname()}, {day.isoformat() if day else 'all days'}\n")
    print(table(counts, names))


if __name__ == "__main__":
    main()
