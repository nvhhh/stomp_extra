"""Long cab IRs (0.6.0-longir-test): run the built firmware's CAB FIR path in the emulator.

User IR slots (active CAB index 240..249) must play the IR's first 1024 samples exactly;
built-in cabs must stay bit-identical to 0.5.2; switching IRs must not leak ring history.
Instruction counts are emulator instructions, not hardware cycles.

usage: python tests/test_long_ir.py
"""
import glob
import json
import random
import struct
import sys
import unittest
from pathlib import Path

import numpy as np
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_D8, UC_ARM_REG_D9, UC_ARM_REG_D10, UC_ARM_REG_D11, UC_ARM_REG_D12

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_capture_fast as f  # noqa: E402

b = f.b
ROOT = b.ROOT
NEW = b.master('build/soran-cfw-0.6.0-longir-test-on-1.1.1.bin')
NEW_META = json.loads((ROOT / 'patches/fx-long-ir/symbols.json').read_text())
OLD = b.master('build/soran-cfw-0.5.2-deadline-on-1.1.1.bin')
OLD_META = json.loads((ROOT / 'patches/fx-partition-fir/symbols.json').read_text())

OBJ = 0x20004998            # stock CAB state
COEFFS = OBJ + 0x128        # 2048 uploaded floats (reversed IR)
RING_ARG, POS = OBJ + 0x2128, OBJ + 0x110
LONG_RING = 0x81fb8000


def setup(image, meta):
    return f.g.t.d.setup(image, meta)


def ir_upload(path=None, seed=None):
    """8192-byte IR upload: real WAV (Stomp Manager 'app' layout) or a random IR."""
    if path:
        sys.path.insert(0, str(ROOT))
        from nuxfw import irconv
        return irconv.wav_to_coeffs(Path(path).read_bytes(), 'app')
    rng = random.Random(seed)
    return struct.pack('<2048f', *[rng.uniform(-1, 1) * 0.999 ** k for k in range(2048)][::-1])


def run(u, fn, index, upload, blocks, set_coeffs=True):
    """Feed `blocks` (lists of 8 floats) through the CAB FIR call path; returns output samples."""
    u.mem_write(OBJ + 2, struct.pack('<H', index))
    if set_coeffs:                     # what the firmware's IR loader does: copy, clear ring
        u.mem_write(COEFFS, upload)
        u.mem_write(RING_ARG, bytes(0x800))
        u.mem_write(POS, bytes(4))
    out = []
    for blk in blocks:
        u.mem_write(b.IN, struct.pack('<8f', *blk))
        b.call(u, fn, (b.IN, b.OUT, OBJ + 0x1b28, RING_ARG), (POS, 0x200, 0x180, 8))
        out.extend(struct.unpack('<8f', u.mem_read(b.OUT, 32)))
    return np.array(out)


def reference(upload, taps, x):
    """Stock FIR semantics: IR in time order (upload reversed), one-sample delay."""
    h = np.frombuffer(upload, '<f4').astype(np.float64)[::-1][:taps]
    return np.concatenate([[0.0], np.convolve(x, h)])[:len(x)]


def blocks_of(x):
    return [list(x[i:i + 8]) for i in range(0, len(x), 8)]


class LongIrTests(unittest.TestCase):
    def test_user_ir_plays_first_1024_samples(self):
        wav = next(iter(glob.glob(str(Path.home() / 'Downloads/**/*57 E - 24bit - 48kHz - 500ms.wav'), recursive=True)), None)
        for label, upload in (('real IR', ir_upload(wav)) if wav else ('random IR', ir_upload(seed=1)),
                              ('random IR', ir_upload(seed=2))):
            u = setup(NEW, NEW_META)
            x = np.random.default_rng(7).uniform(-0.5, 0.5, 8 * 400)   # 3200 samples: several ring wraps
            y = run(u, NEW_META['symbols']['cab_long_fir'], 247, upload, blocks_of(x))
            ref = reference(upload, 1024, x)
            err = np.abs(y - ref).max() / np.abs(ref).max()
            self.assertLess(err, 1e-5, label)
            # and it is genuinely longer than the stock 384 taps
            self.assertGreater(np.abs(y - reference(upload, 384, x)).max() / np.abs(ref).max(), 1e-4, label)

    def test_builtin_cab_bit_identical_to_052(self):
        x = np.random.default_rng(11).uniform(-0.5, 0.5, 8 * 150)
        upload = ir_upload(seed=3)
        outs = []
        for image, meta, fn in ((OLD, OLD_META, OLD_META['symbols']['capture_fir8']),
                                (NEW, NEW_META, NEW_META['symbols']['cab_long_fir'])):
            outs.append(run(setup(image, meta), fn, 10 * 8 + 3, upload, blocks_of(x)))
        self.assertTrue(np.array_equal(outs[0], outs[1]))
        # stock CAB runs 384 taps on a 512-sample ring: the oldest 384 entries -> 128 extra samples delay
        ref = np.concatenate([np.zeros(128), reference(upload, 384, x)])[:len(x)]
        self.assertLess(np.abs(outs[1] - ref).max() / np.abs(ref).max(), 1e-5)

    def test_switching_ir_clears_history(self):
        u = setup(NEW, NEW_META)
        fn = NEW_META['symbols']['cab_long_fir']
        a, c = ir_upload(seed=4), ir_upload(seed=5)
        run(u, fn, 241, a, blocks_of(np.ones(8 * 200)))                 # fill ring with IR A history
        x = np.random.default_rng(3).uniform(-0.5, 0.5, 8 * 160)
        y = run(u, fn, 242, c, blocks_of(x))                             # new active IR
        ref = reference(c, 1024, x)                                      # zero history
        self.assertLess(np.abs(y - ref).max() / np.abs(ref).max(), 1e-5)
        # built-in in between, then back to a user IR: also starts from zero history
        run(u, fn, 5, a, blocks_of(np.ones(8 * 50)))
        y = run(u, fn, 242, c, blocks_of(x))
        self.assertLess(np.abs(y - ref).max() / np.abs(ref).max(), 1e-5)

    def test_registers_preserved(self):
        u = setup(NEW, NEW_META)
        regs = (UC_ARM_REG_D8, UC_ARM_REG_D9, UC_ARM_REG_D10, UC_ARM_REG_D11, UC_ARM_REG_D12)
        for i, r in enumerate(regs):
            u.reg_write(r, 0x1234567800000000 + i)
        run(u, NEW_META['symbols']['cab_long_fir'], 245, ir_upload(seed=6), blocks_of(np.ones(8)))
        self.assertEqual([u.reg_read(r) for r in regs], [0x1234567800000000 + i for i in range(5)])

    def test_full_cab_processor_load_sequence(self):
        """Whole CAB processor (0x14bd0) + main-loop IR loader (0x1500c), as on the pedal."""
        rec0 = bytearray.fromhex(json.loads((ROOT / 'work/fx01-before-fast-test.json').read_text())['edit'])

        def run_parent(image, meta, model, ir=None, slot=7, blocks=600):
            u = setup(image, meta)
            rec = bytearray(rec0)
            rec[2] = model & 0x3f
            u.mem_write(b.EDIT, bytes(rec))
            if ir is not None:
                u.mem_write(0x60e41000 + slot * 0x3000, ir)            # the user slot's stored IR
            rng, out = np.random.default_rng(1), []
            for _ in range(blocks):
                data = struct.pack('<8f', *rng.uniform(-0.3, 0.3, 8))
                u.mem_write(b.IN, data)
                u.mem_write(b.OUT, data)
                b.call(u, 0x14bd0, (b.IN, b.OUT, b.LEFT, b.RIGHT))
                b.call(u, 0x1500c)
                u.mem_write(0x2001f775, b'\0')                         # load-complete signal from other tasks
                out.append(bytes(u.mem_read(b.LEFT, 32) + u.mem_read(b.RIGHT, 32)))
            return out, struct.unpack('<HH', u.mem_read(OBJ, 4))

        old, _ = run_parent(OLD, OLD_META, 12)
        new, state = run_parent(NEW, NEW_META, 12)
        self.assertEqual(old, new)                                       # built-in cab: bit-identical
        ir = ir_upload(seed=12)
        old, _ = run_parent(OLD, OLD_META, 37, ir)
        new, state = run_parent(NEW, NEW_META, 37, ir)
        self.assertEqual(state, (247, 247))                              # user IR slot 8 loaded and active
        y = np.frombuffer(b''.join(new), '<f4')
        self.assertTrue(np.isfinite(y).all() and np.abs(y[-800:]).max() > 0)
        self.assertNotEqual(old, new)                                    # longer IR actually plays

    def test_instruction_profile(self):
        counts = {}
        for label, image, meta, fn, index in (
                ('0.5.2 user IR (384 taps)', OLD, OLD_META, OLD_META['symbols']['capture_fir8'], 247),
                ('long-IR user IR (1024 taps)', NEW, NEW_META, NEW_META['symbols']['cab_long_fir'], 247),
                ('long-IR built-in cab', NEW, NEW_META, NEW_META['symbols']['cab_long_fir'], 83)):
            u = setup(image, meta)
            n, on = [0], [False]
            u.hook_add(UC_HOOK_CODE, lambda *a: on[0] and n.__setitem__(0, n[0] + 1))
            run(u, fn, index, ir_upload(seed=8), blocks_of(np.ones(8 * 4)))   # warm up (ring clear done)
            on[0] = True
            run(u, fn, index, ir_upload(seed=8), blocks_of(np.ones(8)), set_coeffs=False)
            counts[label] = n[0]
        for k, v in counts.items():
            print(f'     {k}: {v} instructions per 8-sample callback')
        self.assertLess(counts['long-IR built-in cab'] - counts['0.5.2 user IR (384 taps)'], 40)


if __name__ == '__main__':
    unittest.main(verbosity=2)
