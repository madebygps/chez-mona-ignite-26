"""Fried Chicken lab: per-guest copy of the SDK starter, opened and closed in VS Code."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Callable

from .config import REPO_DIR

STARTER_DIR = REPO_DIR / "copilot-sdk"
GUESTS_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "ChezMona" / "guests"
FOLDER_PREFIX = "chez-mona-fried-chicken-"
COPY_IGNORE = shutil.ignore_patterns("__pycache__", ".venv", ".git", "*.pyc")
WORKSPACE_SETTINGS = {
    # Keeps closing the window from stopping on an unsaved-changes prompt.
    "files.autoSave": "afterDelay",
    "files.exclude": {".vscode": True},
}


class SessionError(RuntimeError):
    pass


def find_code(configured: str = "") -> str:
    """Return the path of the VS Code command line launcher."""
    candidates = [configured] if configured else []
    on_path = shutil.which("code")
    if on_path:
        candidates.append(on_path)
    local = os.environ.get("LOCALAPPDATA", "")
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    candidates += [
        os.path.join(local, "Programs", "Microsoft VS Code", "bin", "code.cmd"),
        os.path.join(program_files, "Microsoft VS Code", "bin", "code.cmd"),
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    raise SessionError("VS Code was not found. Install it, then restart the launcher.")


def launch_code(code: str, folder: Path, new_window: bool = True) -> None:
    """Open folder and its main.py. Without new_window, VS Code focuses the window
    that already shows the folder."""
    window_flag = "--new-window" if new_window else "--reuse-window"
    args = [code, window_flag, "--disable-workspace-trust", str(folder), str(folder / "main.py")]
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    subprocess.Popen(
        args,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )


def _vscode_windows(token: str) -> list[int]:
    """Top-level VS Code windows whose title contains token."""
    if sys.platform != "win32":
        return []
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    found: list[int] = []
    proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length:
                buffer = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buffer, length + 1)
                title = buffer.value
                if token in title and "Visual Studio Code" in title:
                    found.append(hwnd)
        return True

    user32.EnumWindows(proc(callback), 0)
    return found


def close_vscode_windows(token: str, timeout: float = 5.0) -> dict:
    """Ask the VS Code windows showing token to close. Returns counts."""
    windows = _vscode_windows(token)
    if windows and sys.platform == "win32":
        import ctypes

        WM_CLOSE = 0x0010
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        for hwnd in windows:
            user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and _vscode_windows(token):
            time.sleep(0.25)
    return {"asked": len(windows), "still_open": len(_vscode_windows(token))}


def _on_rm_error(func, path, _exc):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError:
        pass


def remove_folder(folder: Path, attempts: int = 10, delay: float = 0.5) -> bool:
    for _ in range(attempts):
        if not folder.exists():
            return True
        shutil.rmtree(folder, onexc=_on_rm_error)
        if not folder.exists():
            return True
        time.sleep(delay)
    return not folder.exists()


class SdkSessions:
    """At most one Fried Chicken guest folder per laptop."""

    def __init__(
        self,
        code_path: str = "",
        starter_dir: Path = STARTER_DIR,
        guests_dir: Path = GUESTS_DIR,
        launcher: Callable[..., None] = launch_code,
        closer: Callable[[str], dict] = close_vscode_windows,
        finder: Callable[[str], list] = _vscode_windows,
    ):
        self.finder = finder
        self.code_path = code_path
        self.starter_dir = starter_dir
        self.guests_dir = guests_dir
        self.launcher = launcher
        self.closer = closer
        self.active: Path | None = None
        self.lock = threading.Lock()

    def sweep(self) -> list[str]:
        """Delete guest folders left over from earlier runs."""
        removed = []
        if self.guests_dir.is_dir():
            for child in self.guests_dir.iterdir():
                if child.is_dir() and child.name.startswith(FOLDER_PREFIX) and child != self.active:
                    self.closer(child.name)
                    if remove_folder(child, attempts=2):
                        removed.append(child.name)
        return removed

    def start(self) -> dict:
        with self.lock:
            if self.active:
                self._end_locked()
            self.sweep()
            find_code(self.code_path)
            folder = self.guests_dir / f"{FOLDER_PREFIX}{uuid.uuid4().hex[:8]}"
            shutil.copytree(self.starter_dir, folder, ignore=COPY_IGNORE)
            settings = folder / ".vscode" / "settings.json"
            settings.parent.mkdir(exist_ok=True)
            settings.write_text(json.dumps(WORKSPACE_SETTINGS, indent=2), encoding="utf-8")
            self.active = folder
            return {"folder": str(folder)}

    def open_vscode(self) -> dict:
        """Focus the guest's VS Code window, or open a new one if there is none."""
        with self.lock:
            if not self.active or not self.active.is_dir():
                raise SessionError("There is no starter folder to open. Start the lab again.")
            code = find_code(self.code_path)
            already_open = bool(self.finder(self.active.name))
            try:
                self.launcher(code, self.active, new_window=not already_open)
            except OSError as exc:
                raise SessionError(f"Could not start VS Code: {exc}") from exc
            return {"folder": str(self.active)}

    def end(self) -> dict:
        with self.lock:
            return self._end_locked()

    def _end_locked(self) -> dict:
        if not self.active:
            return {"ended": False}
        folder = self.active
        closed = self.closer(folder.name)
        deleted = remove_folder(folder)
        self.active = None
        return {
            "ended": True,
            "folder": str(folder),
            "window_still_open": closed["still_open"] > 0,
            "deleted": deleted,
        }
