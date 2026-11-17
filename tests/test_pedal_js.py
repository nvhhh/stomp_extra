"""editor/static/pedal.js (direct Web MIDI mode) must encode exactly like nuxfw/jme.py.

Runs pedal.js in Node with a stub `window` and compares its message builders with the Python ones,
then drives its App against a simulated pedal (tests/pedal_sim.js): connect, live CC, chain, save,
export, and an IR import through the real conversion worker and WebAssembly module.
usage: python tests/test_pedal_js.py
"""
import json
import random
import struct
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nuxfw import jme  # noqa: E402

NODE = r"""
const fs = require('fs'), vm = require('vm');
const ctx = {window: {}, console, URL, TextEncoder, TextDecoder, Response, setTimeout, clearTimeout, performance,
             navigator: {}, document: {baseURI: 'http://x/'}};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), ctx);
const P = ctx.window.DirectPedal._internals, hex = b => Buffer.from(b).toString('hex');
const cases = JSON.parse(fs.readFileSync(0, 'utf8'));
const out = {};
out.pack7 = cases.pack7.map(h => hex(P.pack7(Buffer.from(h, 'hex'))));
out.unpack7 = cases.pack7.map(h => hex(P.unpack7(P.pack7(Buffer.from(h, 'hex')))));
out.header = cases.header.map(a => hex(P.bulkHeader(...a)));
out.bulk = cases.bulk.map(([cmd, a, b, c, h]) => P.bulkMessages(cmd, a, b, c, Uint8Array.from(Buffer.from(h, 'hex'))).map(hex));
out.ir = cases.names.map(n => hex(P.irEntry(n)));
out.nam = cases.names.filter(n => n !== null).map(n => hex(P.namNameRecord(n, 0.8125)));
out.export = hex(P.exportJmePreset(7, Uint8Array.from(Buffer.from(cases.record, 'hex'))));
process.stdout.write(JSON.stringify(out));
"""


def run_node(script, stdin, *args):
    r = subprocess.run(["node", "-e", script, str(ROOT / "editor/static/pedal.js"), *map(str, args)], input=stdin,
                       capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise RuntimeError(r.stderr)
    return r.stdout


class PedalJsTests(unittest.TestCase):
    def test_encoders_match_python(self):
        rnd = random.Random(1)
        blobs = [bytes(rnd.randrange(256) for _ in range(n)) for n in (0, 1, 7, 8, 98, 136, 137, 300, 8192)]
        record = bytes(rnd.randrange(128) for _ in range(98))
        names = [None, "Marshall Box 57", "Ünïcode name too long for slot", "x" * 40]
        cases = {"pack7": [b.hex() for b in blobs],
                 "header": [[0, 0, 0, 0, 0], [5, 3, 1, 136, 8192], [98, 0, 0, 0xFFFF, 0x12345678]],
                 "bulk": [[jme.CMD_IR_DATA, 4, 0, 0, blobs[-1].hex()], [jme.CMD_PRESET, 12, 0, 0, record.hex()],
                          [jme.CMD_NAM, 0, 13, jme.NAM_NAME, blobs[4].hex()]],
                 "names": names, "record": record.hex()}
        out = json.loads(run_node(NODE, json.dumps(cases)))
        self.assertEqual(out["pack7"], [jme.pack7(b).hex() for b in blobs])
        self.assertEqual(out["unpack7"], [b.hex() for b in blobs])
        self.assertEqual(out["header"], [jme.bulk_header(*a).hex() for a in cases["header"]])
        self.assertEqual(out["bulk"], [[m.hex() for m in jme.bulk_messages(c, a, b, d, bytes.fromhex(h))]
                                       for c, a, b, d, h in cases["bulk"]])
        self.assertEqual(out["ir"], [jme.ir_entry(n).hex() for n in names])
        self.assertEqual(out["nam"], [jme.nam_name_record(n, 0.8125).hex() for n in names if n is not None])
        self.assertEqual(out["export"], jme.export_jmepreset(7, record).hex())

    def test_app_against_simulated_pedal(self):
        ir = next(iter(sorted((Path.home() / "Downloads").rglob("*57 E - 24bit - 48kHz - 500ms.wav"))), None)
        if ir is None:
            self.skipTest("test IR not found in Downloads")
        script = (ROOT / "tests" / "pedal_sim.js").read_text(encoding="utf-8")
        out = json.loads(run_node(script, "", ROOT / "editor/static/convert-worker.js",
                                  ROOT / "editor/static/stomp_convert.wasm", ir))
        self.assertTrue(out["connected"], out["error"])
        self.assertEqual(out["info"], {"firmware": "V1.1.1", "model": "JME-01", "build": "202606041731", "extra": "V0"})
        self.assertEqual((out["current"], out["presets"]), (4, ["Preset 1", "Preset 99"]))
        self.assertEqual(out["ir"][:3], [None, "Marshall Box - 9", None])
        self.assertEqual((out["nam0"], out["nam_count"], out["split"]), ("USER AMP 01", 20, True))
        self.assertEqual(out["cc"], {"ok": True})
        self.assertEqual(out["vol"], f"{77:02x}")
        self.assertEqual(out["chain"], {"ok": True})
        self.assertEqual(out["save"], {"ok": True})
        saved = bytes.fromhex(out["saved"])
        self.assertEqual(saved[82:98], b"Web MIDI test".ljust(16, b"\0"))
        self.assertEqual((saved[66], list(saved[70:78])), (77, [0, 6, 1, 2, 7, 3, 4, 5]))
        self.assertEqual(out["exp"], 'attachment; filename="P04 Preset 4.jmePreset"')
        self.assertEqual(out["ir_up"], {"ok": True})
        self.assertIsNone(out["err"])
        self.assertEqual(out["ir_after"], {"slot": 2, "used": True, "name": "Test IR"})
        from nuxfw import irconv
        self.assertEqual(out["ir_data"], irconv.wav_to_coeffs(ir.read_bytes(), "app").hex())
        self.assertIn("needs the Python bridge", out["nam_app"]["error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
