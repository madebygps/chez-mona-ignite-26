import tempfile
import unittest
from pathlib import Path
from unittest import mock

from chez_mona import sdk_session
from chez_mona.sdk_session import FOLDER_PREFIX, SdkSessions, SessionError


class FakeVsCode:
    def __init__(self):
        self.launches = []
        self.closed = []
        self.open = set()

    def launch(self, code, folder, new_window=True):
        self.launches.append((folder.name, new_window))
        self.open.add(folder.name)

    def close(self, token):
        self.closed.append(token)
        self.open.discard(token)
        return {"asked": 1, "still_open": 0}

    def find(self, token):
        return [1] if token in self.open else []


class SdkSessionsTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.guests = root / "guests"
        self.code = root / "code.cmd"
        self.code.write_text("")
        self.vscode = FakeVsCode()
        self.sessions = SdkSessions(
            code_path=str(self.code),
            guests_dir=self.guests,
            launcher=self.vscode.launch,
            closer=self.vscode.close,
            finder=self.vscode.find,
        )

    def test_start_copies_starter_without_opening_a_window(self):
        folder = Path(self.sessions.start()["folder"])
        self.assertTrue(folder.name.startswith(FOLDER_PREFIX))
        self.assertTrue((folder / "main.py").is_file())
        self.assertTrue((folder / ".vscode" / "settings.json").is_file())
        self.assertFalse(any(p.name in {"__pycache__", ".venv"} for p in folder.rglob("*")))
        self.assertEqual(self.vscode.launches, [])

    def test_open_vscode_opens_new_window_or_focuses_existing(self):
        folder = Path(self.sessions.start()["folder"])
        self.sessions.open_vscode()
        self.sessions.open_vscode()
        self.vscode.open.clear()
        self.sessions.open_vscode()
        self.assertEqual(self.vscode.launches, [(folder.name, True), (folder.name, False), (folder.name, True)])

    def test_end_closes_and_deletes(self):
        folder = Path(self.sessions.start()["folder"])
        result = self.sessions.end()
        self.assertTrue(result["deleted"])
        self.assertFalse(result["window_still_open"])
        self.assertFalse(folder.exists())
        self.assertIn(folder.name, self.vscode.closed)
        self.assertEqual(self.sessions.end(), {"ended": False})
        with self.assertRaises(SessionError):
            self.sessions.open_vscode()

    def test_second_start_replaces_first(self):
        first = Path(self.sessions.start()["folder"])
        second = Path(self.sessions.start()["folder"])
        self.assertFalse(first.exists())
        self.assertTrue(second.exists())

    def test_sweep_removes_only_leftover_guest_folders(self):
        self.guests.mkdir(parents=True)
        (self.guests / f"{FOLDER_PREFIX}old").mkdir()
        (self.guests / "keep-me").mkdir()
        self.assertEqual(self.sessions.sweep(), [f"{FOLDER_PREFIX}old"])
        self.assertTrue((self.guests / "keep-me").exists())

    def test_missing_vscode_is_reported(self):
        missing = SessionError("VS Code was not found.")
        with mock.patch.object(sdk_session, "find_code", side_effect=missing):
            with self.assertRaises(SessionError):
                self.sessions.start()
        self.assertFalse(any(self.guests.glob(f"{FOLDER_PREFIX}*")))


if __name__ == "__main__":
    unittest.main()
