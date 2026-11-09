"""Load and validate lab content from content/labs.json."""

from __future__ import annotations

import json
from pathlib import Path

import markdown

from .config import LAUNCHER_DIR

CONTENT_DIR = LAUNCHER_DIR / "content"
START_TYPES = {"none", "sdk", "open_url"}
ACTION_TYPES = {"open_url", "reopen_vscode"}


class ContentError(ValueError):
    pass


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise ContentError(message)


def validate(data: dict, content_dir: Path = CONTENT_DIR) -> None:
    dishes = data.get("dishes")
    _check(isinstance(dishes, list) and dishes, "labs.json needs a non-empty 'dishes' list")
    seen = set()
    for dish in dishes:
        did = dish.get("id", "?")
        _check(did not in seen, f"duplicate dish id {did}")
        seen.add(did)
        for key in ("id", "dish", "lab", "pitch"):
            _check(isinstance(dish.get(key), str) and dish[key], f"{did}: missing {key}")
        uses = dish.get("uses")
        _check(isinstance(uses, list) and 1 <= len(uses) <= 3
               and all(isinstance(u, str) and u.strip() for u in uses),
               f"{did}: uses needs 1 to 3 names")
        about = dish.get("about")
        _check(isinstance(about, list) and 1 <= len(about) <= 4
               and all(isinstance(p, str) and p.strip() for p in about),
               f"{did}: about needs 1 to 4 short points")
        _check(dish.get("start", {}).get("type") in START_TYPES, f"{did}: bad start type")
        if dish["start"]["type"] == "open_url":
            _check(dish["start"].get("url", "").startswith("https://"), f"{did}: start needs https url")
        _check(dish.get("steps"), f"{did}: needs steps")
        for i, step in enumerate(dish["steps"], 1):
            _check(step.get("text"), f"{did} step {i}: missing text")
            if "markdown" in step:
                _check((content_dir / step["markdown"]).is_file(), f"{did} step {i}: markdown file not found")
            action = step.get("action")
            if action:
                _check(action.get("type") in ACTION_TYPES, f"{did} step {i}: bad action type")
                _check(action.get("label"), f"{did} step {i}: action needs label")
                if action["type"] == "open_url":
                    _check(action.get("url", "").startswith("https://"), f"{did} step {i}: action needs https url")
        quiz = dish.get("quiz", [])
        _check(len(quiz) == 2, f"{did}: quiz needs exactly 2 questions")
        for i, q in enumerate(quiz, 1):
            for key in ("question", "answer", "hint"):
                _check(q.get(key), f"{did} question {i}: missing {key}")
            others = q.get("others", [])
            _check(len(others) == 3, f"{did} question {i}: needs 3 other choices")
            _check(len(set(others + [q["answer"]])) == 4, f"{did} question {i}: choices must be unique")
        _check(dish.get("wrap_up"), f"{did}: needs wrap_up")
        receipt = dish.get("receipt", {})
        learned = receipt.get("learned")
        _check(isinstance(learned, list) and 1 <= len(learned) <= 4
               and all(isinstance(p, str) and p.strip() for p in learned),
               f"{did}: receipt learned needs 1 to 4 short points")
        _check(receipt.get("qr", "").startswith("https://"), f"{did}: receipt needs https qr")


def load(path: Path | None = None, content_dir: Path = CONTENT_DIR) -> dict:
    """Return validated content with Markdown steps rendered to HTML."""
    path = path or content_dir / "labs.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    validate(data, content_dir)
    for dish in data["dishes"]:
        for step in dish["steps"]:
            if "markdown" in step:
                text = (content_dir / step["markdown"]).read_text(encoding="utf-8")
                step["html"] = markdown.markdown(text)
    return data


def by_id(data: dict) -> dict:
    return {dish["id"]: dish for dish in data["dishes"]}
