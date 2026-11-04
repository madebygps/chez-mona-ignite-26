import copy
import json
import tempfile
import unittest
from pathlib import Path

from chez_mona import labs
from chez_mona.config import StationConfig


class LabsTest(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((labs.CONTENT_DIR / "labs.json").read_text(encoding="utf-8"))

    def test_shipped_content_is_valid(self):
        loaded = labs.load()
        ids = [d["id"] for d in loaded["dishes"]]
        self.assertEqual(ids, ["omelette", "fried-chicken", "soup", "dip"])
        soup = labs.by_id(loaded)["soup"]
        self.assertTrue(all("html" in s for s in soup["steps"] if "markdown" in s))

    def assert_rejected(self, mutate):
        data = copy.deepcopy(self.data)
        mutate(data)
        with self.assertRaises(labs.ContentError):
            labs.validate(data)

    def test_rejects_bad_content(self):
        self.assert_rejected(lambda d: d["dishes"][0]["quiz"].pop())
        self.assert_rejected(lambda d: d["dishes"][0]["quiz"][0]["others"].append("Extra"))
        self.assert_rejected(lambda d: d["dishes"][0]["quiz"][0].update(others=["a", "a", "b"]))
        self.assert_rejected(lambda d: d["dishes"][3]["start"].update(url="http://example.com"))
        self.assert_rejected(lambda d: d["dishes"][2]["steps"][0].update(markdown="soup/missing.md"))
        self.assert_rejected(lambda d: d["dishes"][1].update(id="omelette"))
        self.assert_rejected(lambda d: d["dishes"][0]["receipt"].pop("qr"))


class ConfigTest(unittest.TestCase):
    def write(self, data):
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(data, handle)
        handle.close()
        self.addCleanup(Path(handle.name).unlink)
        return Path(handle.name)

    def test_example_loads(self):
        config = StationConfig.load(labs.LAUNCHER_DIR / "station.example.json")
        self.assertTrue(config.dry_run)
        self.assertEqual(config.print_width_dots, 576)

    def test_partial_idle_override(self):
        config = StationConfig.load(self.write({"idle_seconds": {"prompt": 10}}))
        self.assertEqual(config.idle_seconds, {"default": 120, "explore": 600, "prompt": 10})

    def test_rejects_unknown_key(self):
        with self.assertRaises(ValueError):
            StationConfig.load(self.write({"printer": "x"}))

    def test_rejects_bad_width(self):
        with self.assertRaises(ValueError):
            StationConfig.load(self.write({"print_width_dots": 570}))


if __name__ == "__main__":
    unittest.main()
