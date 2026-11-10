import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from chez_mona import stats


class StatsTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "data" / "events.jsonl"

    def tearDown(self):
        self.dir.cleanup()

    def test_summary_by_day_and_table(self):
        stats.record("started", "soup", self.path, datetime(2026, 11, 17, 9, 0))
        stats.record("started", "soup", self.path, datetime(2026, 11, 18, 9, 0))
        stats.record("completed", "soup", self.path, datetime(2026, 11, 18, 9, 20))
        with self.path.open("a", encoding="utf-8") as f:
            f.write('{"time": "2026-11-18T09:21:00", "event": "start')  # cut short by a crash
        stats.record("receipt", "soup", self.path, datetime(2026, 11, 18, 9, 21))

        day = stats.summary(["soup", "dip"], self.path, date(2026, 11, 18))
        self.assertEqual(day["soup"], {"started": 1, "completed": 1, "receipt": 1})
        self.assertEqual(day["dip"], {"started": 0, "completed": 0, "receipt": 0})
        self.assertEqual(stats.summary(["soup"], self.path)["soup"]["started"], 2)

        text = stats.table(day, {"soup": "Soup", "dip": "Dip"})
        self.assertIn("| Soup | 1 | 1 | 1 |", text)
        self.assertIn("| **Total** | **1** | **1** | **1** |", text)

    def test_missing_log_is_empty(self):
        self.assertEqual(stats.summary(["soup"], self.path)["soup"]["completed"], 0)


if __name__ == "__main__":
    unittest.main()
