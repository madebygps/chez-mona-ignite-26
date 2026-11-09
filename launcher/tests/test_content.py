import copy
import json
import unittest

from chez_mona import labs
from chez_mona.config import StationConfig


class LabsTest(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((labs.CONTENT_DIR / "labs.json").read_text(encoding="utf-8"))

    def test_shipped_content_is_valid(self):
        loaded = labs.load()
        ids = [d["id"] for d in loaded["dishes"]]
        self.assertEqual(ids, ["omelette", "fried-chicken", "soup", "dip"])

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
        self.assert_rejected(lambda d: d["dishes"][0]["receipt"].update(learned="One string"))
        self.assert_rejected(lambda d: d["dishes"][0]["receipt"].update(learned=[]))
        self.assert_rejected(lambda d: d["dishes"][0]["receipt"].update(learned=["a", "b", "c", "d", "e"]))
        self.assert_rejected(lambda d: d["dishes"][0]["receipt"].update(learned=["ok", " "]))
        self.assert_rejected(lambda d: d["dishes"][0].pop("pitch"))
        self.assert_rejected(lambda d: d["dishes"][0]["steps"][0].update(body=" "))
        self.assert_rejected(lambda d: d["dishes"][0]["steps"][0].update(image="steps/missing.png", alt="x"))
        self.assert_rejected(lambda d: d["dishes"][0]["steps"][1].pop("alt"))
        self.assert_rejected(lambda d: d["dishes"][0]["steps"][2].update(prompt=" "))
        self.assert_rejected(lambda d: d["dishes"][0].update(uses=[]))
        self.assert_rejected(lambda d: d["dishes"][0].update(uses="GitHub.com"))
        self.assert_rejected(lambda d: d["dishes"][0].update(about=[]))
        self.assert_rejected(lambda d: d["dishes"][0].update(about="One string"))


class ConfigTest(unittest.TestCase):
    def test_defaults(self):
        config = StationConfig()
        self.assertEqual((config.role, config.server_port()), ("station", 8765))
        self.assertEqual(config.idle_seconds, {"default": 120, "explore": 600, "prompt": 30})

    def test_rejects_unknown_role(self):
        with self.assertRaises(ValueError):
            StationConfig(role="oven")


if __name__ == "__main__":
    unittest.main()
