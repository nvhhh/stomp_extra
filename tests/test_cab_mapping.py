"""Cab parameter mapping: catalog positions -> CC numbers and record offsets (no hardware needed).

The cab block is the same for every cab model: count byte at record offset 29, then
MIC, POSITION, LOW CUT, HIGH CUT, VOLUME at offsets 30..34 (CC 26..30). User IR cabs
(models 30..39) only show LOW CUT, HIGH CUT and VOLUME, but those stay at positions 2..4.

Pedal evidence (custom firmware 0.5.2, 2026-11-17):
- Selecting an IR slot with CC 2 makes the pedal load [0, 0, 0, 100, 50] into offsets 30..34
  and echo CC 26=0, CC 28=0, CC 30=50 (low cut 20 Hz, high cut 20 kHz, volume 50, as
  Stomp Manager shows for an IR slot).
- Presets with an IR cab saved by Stomp Manager hold [0, 0, 0, 100, 60] and [0, 0, 0, 100, 90].

usage: python -m unittest test_cab_mapping   (from tests/)   or   python tests/test_cab_mapping.py
"""
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from editor.server import App, CATALOG, cc_offset  # noqa: E402

CAB = next(m for m in CATALOG["modules"] if m["key"] == "CAB")
BUILTIN = ["MIC", "POSITION", "LOW CUT(Hz)", "HIGH CUT(Hz)", "VOLUME"]
IR = ["LOW CUT(Hz)", "HIGH CUT(Hz)", "VOLUME"]


def model(index, mod=CAB):
    return next(m for m in mod["models"] if m["index"] == index)


def shown(rec, mod=CAB):
    """What the editor shows: index.html reads rec[count_offset + 1 + pos]."""
    m = model(rec[mod["slot"]] & 63, mod)
    return {p["label"]: rec[mod["count_offset"] + 1 + p["pos"]] for p in m["params"]}


def record(cab_model, block):
    rec = bytearray(98)
    rec[2] = cab_model
    rec[29] = 5
    rec[30:30 + len(block)] = bytes(block)
    return bytes(rec)


class CabMappingTests(unittest.TestCase):
    def test_every_param_has_a_unique_position_inside_its_block(self):
        for mod in CATALOG["modules"]:
            for m in mod["models"]:
                pos = [p["pos"] for p in m["params"]]
                self.assertEqual(len(pos), len(set(pos)), (mod["key"], m["index"]))
                self.assertTrue(all(0 <= x < mod["capacity"] for x in pos), (mod["key"], m["index"], pos))
                if not (mod["key"] == "CAB" and m["user"]):
                    self.assertEqual(pos, list(range(len(pos))), (mod["key"], m["index"]))

    def test_builtin_cabs_use_cc_26_to_30(self):
        for i in range(30):
            m = model(i)
            self.assertIsNone(m["user"])
            self.assertEqual([p["label"] for p in m["params"]], BUILTIN)
            for p, cc, off in zip(m["params"], range(26, 31), range(30, 35)):
                self.assertEqual(CAB["cc_base"] + p["pos"], cc)
                self.assertEqual(cc_offset(cc), off)
            self.assertEqual(m["params"][0]["options"][4], "SM57")
            self.assertEqual(m["params"][1]["options"], ["EDGE", "MIDDLE", "CENTER"])

    def test_user_ir_cabs_use_cc_28_to_30(self):
        for i in range(30, 40):
            m = model(i)
            self.assertEqual(m["user"], {"kind": "ir", "slot": i - 30})
            self.assertEqual([p["label"] for p in m["params"]], IR)
            self.assertEqual([CAB["cc_base"] + p["pos"] for p in m["params"]], [28, 29, 30])
            self.assertEqual([cc_offset(CAB["cc_base"] + p["pos"]) for p in m["params"]], [32, 33, 34])

    def test_pedal_records_read_back_as_the_pedal_shows_them(self):
        # Defaults the pedal loads when an IR slot is selected.
        self.assertEqual(shown(record(30, [0, 0, 0, 100, 50])),
                         {"LOW CUT(Hz)": 0, "HIGH CUT(Hz)": 100, "VOLUME": 50})
        # Stomp Manager preset with an IR cab.
        self.assertEqual(shown(record(30, [0, 0, 0, 100, 60]))["VOLUME"], 60)
        # Factory preset with a built-in cab (MIC SM7B, POSITION CENTER).
        self.assertEqual(shown(record(5, [6, 2, 0, 100, 50])),
                         {"MIC": 6, "POSITION": 2, "LOW CUT(Hz)": 0, "HIGH CUT(Hz)": 100, "VOLUME": 50})
        # Bypass bit does not change the model.
        self.assertEqual(shown(record(31 | 0x40, [0, 0, 0, 100, 81]))["VOLUME"], 81)

    def test_cc_echo_updates_the_ir_value_the_editor_shows(self):
        app = App.__new__(App)
        app.cond = threading.Condition()
        app.version = 0
        app.s = {"edit": record(30, [0, 0, 0, 100, 50]).hex(), "dirty": False}
        vol = model(30)["params"][2]
        app.set_byte(cc_offset(CAB["cc_base"] + vol["pos"]), 73, dirty=False)
        self.assertEqual(shown(bytes.fromhex(app.s["edit"]))["VOLUME"], 73)

    def test_editor_page_uses_param_positions(self):
        html = (ROOT / "editor/static/index.html").read_text(encoding="utf-8")
        self.assertIn("mod.cc_base + paramPos(p,i)", html)
        self.assertNotRegex(html, r"const cc = mod\.cc_base \+ i\b")
        self.assertRegex(html, r"const paramPos = \(p,i\) => Number\.isInteger\(p\.pos\) \? p\.pos : i;")
        # Values are read back through the same position: offset = count_offset + 1 + (cc - cc_base).
        self.assertIn("rec[mod.count_offset + 1 + (+el.dataset.cc - mod.cc_base)]", html)

    def test_catalog_json_matches_catalog_build(self):
        src = ROOT / "work/sm_models.json"
        if not src.exists():
            self.skipTest("work/sm_models.json (Stomp Manager scrape) not present")
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "catalog.json"
            subprocess.run([sys.executable, str(ROOT / "editor/catalog_build.py"), str(src), str(out)],
                           check=True, capture_output=True)
            self.assertEqual(json.loads(out.read_text(encoding="utf-8")), CATALOG)

    def test_catalog_build_ir_layout_without_scrape(self):
        spec = importlib.util.spec_from_file_location("catalog_build", ROOT / "editor/catalog_build.py")
        cb = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cb)
        params = cb.params_for("CAB", "", cb.IR_CAB_LABELS, cb.IR_CAB_FIRST_POS)
        self.assertEqual([(p["label"], p["pos"]) for p in params],
                         [("LOW CUT(Hz)", 2), ("HIGH CUT(Hz)", 3), ("VOLUME", 4)])
        built = cb.params_for("CAB", "Twin 212", ["MIC", "E906", "POSITION", "EDGE", *IR])
        self.assertEqual([(p["label"], p["pos"]) for p in built], list(zip(BUILTIN, range(5))))


if __name__ == "__main__":
    unittest.main()
