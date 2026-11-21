"""0.6.3: 0.6.2 plus the stall profiler (main-loop heartbeat, stall sampling in the audio callback),
the preset-settle hold (EQ/MOD captures dry from a preset recall until the redraw is over) and the
debt guard (captures latch dry when audio falls more than 4 blocks behind).

usage: python tests/test_stall_profiler.py
"""
import json
import struct
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'patches/fx-controls'))
import test_fx_controls as c  # noqa: E402
import diagnostics as diag  # noqa: E402
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS  # noqa: E402
from unicorn.arm_const import UC_ARM_REG_SP, UC_ARM_REG_MSP, UC_ARM_REG_PSP, UC_CPU_ARM_CORTEX_M7  # noqa: E402

b = c.base
ROOT = b.ROOT
NEW = b.master('build/soran-cfw-0.6.3-on-1.1.1.bin')
OLD = b.master('build/soran-cfw-0.6.2-grace-test-on-1.1.1.bin')
META = json.loads((ROOT / 'patches/fx-settle/symbols.json').read_text())
S = META['symbols']
P, T, N, I = diag.PROF, diag.PROF_THRESHOLD, diag.PROF_SAMPLES, diag.PROF_INTERVAL
FRAME = 0x20030000


def make():
    u = b.make(False)
    u.mem_write(0, NEW)
    u.ctl_remove_cache(0, 0x40000)
    u.mem_map(0xe0000000, 0x100000)
    u.mem_map(0x401ec000, 0x1000)
    b.call(u, S['boot'], stop=0x76fc)
    u.mem_write(0x200101f4, struct.pack('<I', b.EDIT))
    return u


def put(u, a, v):
    u.mem_write(a, struct.pack('<I', v & 0xffffffff))


def word(u, a):
    return b.word(u, a)


def frame(u, base, pc, lr):
    u.mem_write(base, struct.pack('<8I', 0, 1, 2, 3, 12, lr, pc, 0x01000000))


def callback(u, gap=100000):
    """Audio callback entry as on hardware: exception frame at FRAME, EXC_RETURN in LR,
    0x12278's real prologue, then the diagnostic_begin hook (stops at its tail call)."""
    put(u, diag.BASE + 4, 0x1000)
    put(u, 0xe0001004, 0x1000 + gap)
    put(u, diag.BASE + 20, 0)
    u.reg_write(UC_ARM_REG_SP, FRAME)
    u.reg_write(b.UC_ARM_REG_LR, 0xfffffff9)
    u.emu_start(0x12279, 0xde12, count=200000)
    assert u.reg_read(b.UC_ARM_REG_PC) == 0xde12


def heartbeat(u):
    """One main-loop spin (the hook itself is tested separately)."""
    put(u, P, word(u, P) + 1)


class ProfilerTests(unittest.TestCase):
    def test_hooks_installed(self):
        bl = lambda at: (struct.unpack_from('<H', NEW, at)[0], struct.unpack_from('<H', NEW, at + 2)[0])
        for at, target in ((0x7778, S['profile_heartbeat']), (0x1228c, S['diagnostic_begin'])):
            hi, lo = bl(at)
            s = (hi >> 10) & 1
            j1, j2 = (lo >> 13) & 1, (lo >> 11) & 1
            off = (s << 24) | ((~(j1 ^ s) & 1) << 23) | ((~(j2 ^ s) & 1) << 22) | ((hi & 0x3ff) << 12) | ((lo & 0x7ff) << 1)
            if s:
                off -= 1 << 25
            self.assertEqual(at + 4 + off, target & ~1)
        # Outside the payload, 0.6.3 differs from 0.6.2 only inside this patch's declared ops
        # (hook targets move because the payload grew); 0x7778 and 0x4f1e are the new hooks.
        import tomllib
        ops = tomllib.loads((ROOT / 'patches/fx-settle/patch.toml').read_text())['op']
        spans = set()
        for op in ops:
            if op['kind'] in ('bl', 'word', 'bytes'):
                size = len(op['data']) // 2 if op['kind'] == 'bytes' else 4
                spans.update(range(int(op['offset']), int(op['offset']) + size))
        diff = {a for a in range(0x36d10) if NEW[a] != OLD[a]}
        self.assertTrue(diff <= spans)
        self.assertTrue(set(range(0x7778, 0x777c)) <= diff and set(range(0x4f1e, 0x4f22)) <= diff)
        old_ops = tomllib.loads((ROOT / 'patches/fx-guard-grace/patch.toml').read_text())['op']
        self.assertEqual(sorted(int(o['offset']) for o in ops if o['kind'] != 'blob'),
                         sorted([int(o['offset']) for o in old_ops if o['kind'] != 'blob'] + [0x7778, 0x4f1e]))

    def test_heartbeat_counts_and_returns_to_spin(self):
        u = make()
        seen = []
        u.hook_add(b.UC_HOOK_CODE, lambda uc, pc, size, ctx: (seen.append(pc), uc.emu_stop()), begin=0x2750, end=0x2750)
        u.reg_write(b.UC_ARM_REG_R0, 0x11); u.reg_write(b.UC_ARM_REG_R1, 0x22)
        u.reg_write(b.UC_ARM_REG_LR, 0x777d)
        u.reg_write(UC_ARM_REG_SP, FRAME)
        u.emu_start(S['profile_heartbeat'] | 1, 0, count=50)
        self.assertEqual(seen, [0x2750])
        self.assertEqual(word(u, P), 1)
        self.assertEqual((u.reg_read(b.UC_ARM_REG_R0), u.reg_read(b.UC_ARM_REG_R1), u.reg_read(b.UC_ARM_REG_LR)),
                         (0x11, 0x22, 0x777d))

    def test_no_samples_while_main_loop_runs(self):
        u = make()
        frame(u, FRAME, 0x1234, 0x5679)
        for _ in range(T + 30):
            heartbeat(u)
            callback(u)
        self.assertEqual([word(u, P + 4*k) for k in (2, 3, 4, 6)], [0, 0, 0, 0])

    def test_stall_samples_real_frame_and_keeps_longest(self):
        u = make()
        frame(u, FRAME, 0xbf6f, 0xbfd9)                       # main loop inside the flash writer
        for k in range(T - 1):
            callback(u, gap=150000 if k == 50 else 100000)
        self.assertEqual(word(u, P + 12), 0)
        callback(u)                                            # T-th stalled callback: first sample
        self.assertEqual(word(u, P + 12), 1)
        self.assertEqual(struct.unpack('<4I', u.mem_read(diag.PROF_CUR, 16)), (0xbf6f, 0xbfd9, 0xfffffff9, 150000))
        for _ in range(I * 3):
            callback(u)
        self.assertEqual(word(u, P + 12), 4)
        stall = word(u, P + 8)
        self.assertEqual(stall, T + I * 3)
        heartbeat(u); callback(u)                              # main loop runs again: finalize
        self.assertEqual([word(u, P + 4*k) for k in (2, 4, 5, 6, 10)], [0, stall, 4, 1, stall])
        self.assertEqual(bytes(u.mem_read(diag.PROF_BEST, 64)), bytes(u.mem_read(diag.PROF_CUR, 64)))
        self.assertEqual(word(u, P + 44), 150000)
        # A shorter stall later does not replace the longest one.
        frame(u, FRAME, 0x2222, 0x3333)
        for _ in range(T + 2):
            callback(u)
        heartbeat(u); callback(u)
        self.assertEqual([word(u, P + 4*k) for k in (4, 6, 10)], [stall, 2, T + 2])
        self.assertEqual(word(u, diag.PROF_BEST), 0xbf6f)

    def test_sample_buffer_bounded(self):
        u = make()
        frame(u, FRAME, 0x4444, 0x5555)
        for _ in range(T + I * (N + 10)):
            callback(u)
        self.assertEqual(word(u, P + 12), N)
        self.assertEqual(word(u, diag.PROF_BEST), 0)            # nothing past the record yet
        self.assertEqual(bytes(u.mem_read(diag.PROF_END, 64)), bytes(64))

    def test_psp_frame_on_cortex_m7(self):
        u = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M7)
        u.mem_map(0, 0x40000); u.mem_map(0x20000000, 0x40000); u.mem_map(0xe0000000, 0x100000)
        u.mem_write(0, NEW)
        put(u, P + 8, T - 1)
        msp_frame, psp_frame = 0x2003a000, 0x20039000
        frame(u, psp_frame, 0x7777, 0x8889)
        u.reg_write(UC_ARM_REG_PSP, psp_frame)
        put(u, msp_frame - 4, 0xfffffffd)                       # EXC_RETURN pushed by 0x12278
        u.reg_write(UC_ARM_REG_MSP, msp_frame - 48)             # 0x12278's 48-byte frame
        u.reg_write(b.UC_ARM_REG_LR, 0x12291)
        u.emu_start(S['diagnostic_begin'] | 1, 0xde12, count=500)
        self.assertEqual(struct.unpack('<3I', u.mem_read(diag.PROF_CUR, 12)), (0x7777, 0x8889, 0xfffffffd))

    def test_read_command_pages(self):
        u = make()
        replies = []
        def reply(uc, pc, size, ctx):
            replies.append(bytes(uc.mem_read(uc.reg_read(b.UC_ARM_REG_R2), uc.reg_read(b.UC_ARM_REG_R3))))
            uc.reg_write(b.UC_ARM_REG_PC, uc.reg_read(b.UC_ARM_REG_LR))
        u.hook_add(b.UC_HOOK_CODE, reply, begin=0x5248, end=0x5248)
        for k in range(diag.PROF_PAGES * 16):
            put(u, P + 4*k, 0x9e3779b9 * (k + 1))
        for page in (0, 5, diag.PROF_PAGES - 1):
            msg = b.jme.sysex(0x33, 0, bytes([page]))
            u.mem_write(b.PARAM, msg)
            b.call(u, S['profile_read'], (b.PARAM, len(msg)))
            payload = replies.pop()
            self.assertEqual((len(payload), payload[:4]), (84, b'PRF1'))
            self.assertTrue(all(x < 128 for x in payload))
            values = [sum(v << (7*i) for i, v in enumerate(payload[4+5*k:9+5*k])) for k in range(16)]
            self.assertEqual(values, [(0x9e3779b9 * (page*16 + k + 1)) & 0xffffffff for k in range(16)])
        for msg in (b.jme.sysex(0x33, 0, bytes([diag.PROF_PAGES])), b.jme.sysex(0x33, 1, b'\0'), b.jme.sysex(0x33, 0)):
            u.mem_write(b.PARAM, msg)
            b.call(u, S['profile_read'], (b.PARAM, len(msg)))
        self.assertEqual(replies, [])
        command = 0x20010cbc + 0x485 + 0x33*9
        self.assertEqual((word(u, command), word(u, command + 4)), (S['profile_read'] | 1, S['profile_read'] | 1))

    def test_boot_clears_profiler(self):
        u = make()
        self.assertEqual(bytes(u.mem_read(P, diag.PROF_END - P)), bytes(diag.PROF_END - P))


def recall(u, index):
    b.call(u, S['settle_recall'] | 1, (index,))


class SettleTests(unittest.TestCase):
    def test_recall_starts_hold_and_copies_preset_like_stock(self):
        u = make()
        rec = bytes(range(98))
        u.mem_write(0x2002979c + 17*128, rec)
        recall(u, 17)
        self.assertEqual(bytes(u.mem_read(b.EDIT, 98)), rec)
        self.assertEqual([word(u, P + 4*k) for k in (12, 13, 14, 15)], [diag.SETTLE_MAX, 0, 0, 1])
        put(u, P + 48, 0)
        before = bytes(u.mem_read(b.EDIT, 98))
        recall(u, 99)                                          # stock ignores index >= 99
        self.assertEqual(bytes(u.mem_read(b.EDIT, 98)), before)
        self.assertEqual((word(u, P + 48), word(u, P + 60)), (0, 1))

    def test_hold_until_redraw_then_quiet(self):
        u = make()
        frame(u, FRAME, 0xd4d6, 0x1fc4d)
        recall(u, 3)
        for _ in range(200):                                   # main loop running, no redraw yet: hold
            heartbeat(u); callback(u)
        self.assertEqual(word(u, P + 48), diag.SETTLE_MAX - 200)
        for _ in range(diag.SETTLE_BUSY + 5):                  # the redraw: main loop stalled
            callback(u)
        self.assertEqual(word(u, P + 56), 1)
        for _ in range(diag.SETTLE_IDLE - 1):
            heartbeat(u); callback(u)
        self.assertGreater(word(u, P + 48), 0)
        heartbeat(u); callback(u)
        self.assertEqual([word(u, P + 4*k) for k in (12, 19, 20)], [0, 1, 0])

    def test_short_main_loop_tasks_do_not_end_or_restart_quiet(self):
        u = make()
        recall(u, 3)
        for _ in range(diag.SETTLE_BUSY):
            callback(u)
        for k in range(diag.SETTLE_IDLE * 2):                  # quiet, with brief (< 2 ms) tasks
            if k % 8:
                heartbeat(u)
            callback(u)
        self.assertEqual([word(u, P + 4*k) for k in (12, 19)], [0, 1])
        u = make()
        recall(u, 3)
        for _ in range(diag.SETTLE_BUSY):
            callback(u)
        for _ in range(diag.SETTLE_IDLE - 15):
            heartbeat(u); callback(u)
        for _ in range(diag.SETTLE_QUIET):                     # a 2 ms main-loop task restarts quiet
            callback(u)
        heartbeat(u); callback(u)
        self.assertEqual(word(u, P + 52), 1)
        self.assertGreater(word(u, P + 48), 0)

    def test_hold_limit(self):
        u = make()
        recall(u, 3)
        for _ in range(diag.SETTLE_MAX):
            heartbeat(u); callback(u)
        self.assertEqual([word(u, P + 4*k) for k in (12, 19, 20)], [0, 0, 1])

    def test_capture_dry_and_not_initialized_while_held(self):
        import test_capture_solid_fill as t
        u = t.d.setup(NEW, META)
        u.mem_write(0x60ede000, (ROOT / 'backups/fx01-crash-metadata.bin').read_bytes())
        u.mem_write(0x60edf000, (ROOT / 'backups/fx01-crash-coefficients.bin').read_bytes())
        u.mem_write(b.EDIT + 7, b'\0'); u.mem_write(b.EDIT + 67, b'\x60')
        fn = word(u, 0x2000bd40)
        put(u, diag.SETTLE, 500)
        for _ in range(20):
            result = b.audio(u, fn, 0)
            self.assertEqual(result, bytes(u.mem_read(b.IN, 32) + u.mem_read(b.OUT, 32)))
        self.assertEqual((word(u, 0x3e020), word(u, 0x3e024), word(u, 0x3e030)), (17, 0, 0))
        put(u, diag.SETTLE, 0)
        for _ in range(200):
            result = b.audio(u, fn, 0)
        self.assertEqual(word(u, 0x3e024), 1)
        self.assertNotEqual(result, bytes(u.mem_read(b.IN, 32) + u.mem_read(b.OUT, 32)))
        put(u, diag.SETTLE, 500)                               # a later recall: dry again, state kept
        result = b.audio(u, fn, 0)
        self.assertEqual(result, bytes(u.mem_read(b.IN, 32) + u.mem_read(b.OUT, 32)))
        self.assertEqual(word(u, 0x3e024), 1)


class DebtTests(unittest.TestCase):
    def setUp(self):
        import test_guard_grace as g
        self.g = g
        self.patches = [patch.object(g, 'NEW', NEW), patch.object(g, 'NEW_META', META)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def rig(self):
        return self.g.Rig()

    def test_alternating_overruns_latch_by_debt(self):
        for grace in (0, diag.GRACE_CALLBACKS):
            r = self.rig()
            r.meta(0x3e020, 17, 1, grace)
            n = 0
            while word(r.u, 0x3e024) == 1 and n < 400:
                r.finish(112000); r.finish(97000); n += 1       # never two overruns in a row
            self.assertEqual(word(r.u, 0x3e024), 3, grace)
            self.assertEqual(n, -(-diag.DEBT_LIMIT // 9000))
            self.assertEqual((word(r.u, P + 72), word(r.u, P + 64), word(r.u, 0x3e03c)), (1, 0, 3))

    def test_in_budget_audio_has_no_debt(self):
        r = self.rig()
        r.meta(0x3e020, 17, 1, 0)
        for elapsed in [99999, 60000, 100000, 95000] * 200:
            r.finish(elapsed)
        self.assertEqual((word(r.u, 0x3e024), word(r.u, P + 64), word(r.u, P + 68)), (1, 0, 0))

    def test_debt_recovers_below_limit(self):
        r = self.rig()
        r.meta(0x3e020, 17, 1, diag.GRACE_CALLBACKS)
        for _ in range(10):
            r.finish(114000)                                    # 140k behind (grace streak < 16)
        self.assertEqual(word(r.u, P + 64), 140000)
        for _ in range(10):
            r.finish(80000)
        self.assertEqual((word(r.u, P + 64), word(r.u, P + 68), word(r.u, 0x3e024)), (0, 140000, 1))


class Regression062Tests(unittest.TestCase):
    """0.6.2's grace tests and its 0.6.0 regression suites against this image."""

    def test_062_suites(self):
        import test_guard_grace as g
        with patch.object(g, 'NEW', NEW), patch.object(g, 'NEW_META', META):
            for name in dir(g.GraceTests):
                if name.startswith('test_'):
                    getattr(g.GraceTests(), name)()
            g.Regression060Tests().test_060_suites()


if __name__ == '__main__':
    unittest.main(verbosity=2)
