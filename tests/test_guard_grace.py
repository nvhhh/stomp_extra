"""Capture guard start-up grace (0.6.2-grace-test): 0.6.0 plus a grace window in both overload guards.

A capture's first callbacks after initialization can run slightly over the 100,000-cycle block.
On 0.6.0 two such callbacks in a row latched the capture dry. With --guard-grace, for
GRACE_CALLBACKS after a capture starts processing, overruns below GRACE_HARD latch only after
GRACE_STREAK in a row; at or above GRACE_HARD, and after the window, the 0.6.0 rules apply.
Everything else (audio, MPU, kernel) is 0.6.0.

usage: python tests/test_guard_grace.py
"""
import json
import struct
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'patches/fx-controls'))
import test_capture_fast as f  # noqa: E402
import diagnostics as diag  # noqa: E402

b = f.b
ROOT = b.ROOT
NEW = b.master('build/soran-cfw-0.6.2-grace-test-on-1.1.1.bin')
NEW_META = json.loads((ROOT / 'patches/fx-guard-grace/symbols.json').read_text())
EQ, MOD = 0x3e020, 0x3e040          # capture metadata: key, stage, grace, -, cursor, before, after, checkpoint
STREAK, IN_GRACE = 0x3e11c, 0x3e120
GRACE, HARD, LIMIT = diag.GRACE_CALLBACKS, diag.GRACE_HARD, diag.GRACE_STREAK


def word(u, addr):
    return b.word(u, addr)


class Rig:
    def __init__(self):
        self.u = f.g.t.d.setup(NEW, NEW_META)
        self.u.mem_write(0x3e104, struct.pack('<II', 1000, 100000))

    def meta(self, base, key, stage, grace=None):
        self.u.mem_write(base, struct.pack('<II', key, stage))
        if grace is not None:
            self.u.mem_write(base + 8, struct.pack('<I', grace))

    def finish(self, elapsed):
        """End of one audio callback that took `elapsed` cycles (runs both whole-callback checks)."""
        self.u.mem_write(0xe0001004, struct.pack('<I', 1000 + elapsed))
        b.call(self.u, NEW_META['symbols']['diagnostic_end'], stop=0xde20)

    def channel(self, base, elapsed, channel=1):
        """Per-channel check inside the capture; returns 1 if it latched dry."""
        self.u.mem_write(0x3e114, struct.pack('<I', 1))          # busy: inside an audio callback
        self.u.mem_write(0xe0001004, struct.pack('<I', 1000 + elapsed))
        b.call(self.u, NEW_META['symbols']['capture_budget_guard'], (base, channel))
        return self.u.reg_read(b.UC_ARM_REG_R0)


class GraceTests(unittest.TestCase):
    def test_window_loads_while_initializing_and_counts_down_while_processing(self):
        r = Rig()
        r.meta(EQ, 17, 0, 0)
        r.finish(50000)
        self.assertEqual(word(r.u, EQ + 8), GRACE)
        r.meta(EQ, 17, 1)
        for _ in range(10):
            r.finish(50000)
        self.assertEqual(word(r.u, EQ + 8), GRACE - 10)
        self.assertEqual(word(r.u, IN_GRACE), 1)

    def test_transient_overruns_tolerated_then_streak_limit_latches(self):
        r = Rig()
        r.meta(EQ, 17, 1, GRACE)
        for _ in range(LIMIT - 1):
            r.finish(108000)
        self.assertEqual(word(r.u, EQ + 4), 1)                         # still processing
        r.finish(90000)                                                # one block in budget resets the streak
        self.assertEqual(word(r.u, STREAK), 0)
        for _ in range(LIMIT - 1):
            r.finish(114999)
        self.assertEqual(word(r.u, EQ + 4), 1)
        r.finish(110000)                                               # 16th in a row
        self.assertEqual((word(r.u, EQ + 4), word(r.u, EQ + 28), word(r.u, EQ + 24)), (3, 3, 110000))

    def test_hard_overruns_latch_like_060_during_grace(self):
        r = Rig()
        r.meta(EQ, 17, 1, GRACE)
        r.finish(HARD); self.assertEqual(word(r.u, EQ + 4), 1)
        r.finish(HARD); self.assertEqual(word(r.u, EQ + 4), 3)
        r = Rig()
        r.meta(EQ, 17, 1, GRACE)
        r.finish(105000); r.finish(HARD + 5000)                        # soft then hard: 2 in a row
        self.assertEqual(word(r.u, EQ + 4), 3)

    def test_after_window_060_rules(self):
        r = Rig()
        r.meta(EQ, 17, 1, 3)
        for _ in range(3):
            r.finish(50000)                                            # the 3 callbacks of the window
        self.assertEqual((word(r.u, EQ + 8), word(r.u, IN_GRACE)), (0, 1))
        r.finish(50000)
        self.assertEqual((word(r.u, EQ + 8), word(r.u, IN_GRACE)), (0, 0))
        r.finish(101000); self.assertEqual(word(r.u, EQ + 4), 1)
        r.finish(101000); self.assertEqual(word(r.u, EQ + 4), 3)

    def test_one_capture_in_grace_covers_both_slots(self):
        """The window is per capture, the tolerance is per callback: a second capture starting
        while the first runs steady also lets the first ride out the shared spike."""
        r = Rig()
        r.meta(EQ, 17, 1, 0)
        r.meta(MOD, 18, 1, GRACE)
        for _ in range(LIMIT - 1):
            r.finish(106000)
        self.assertEqual((word(r.u, EQ + 4), word(r.u, MOD + 4)), (1, 1))
        r.finish(106000)
        self.assertEqual((word(r.u, EQ + 4), word(r.u, MOD + 4)), (3, 3))

    def test_native_models_untouched(self):
        r = Rig()
        r.meta(EQ, 3, 0, 0)                                            # built-in OD model 2 in EQ
        r.meta(MOD, 7, 5, 0)
        r.finish(50000)
        self.assertEqual((word(r.u, EQ + 8), word(r.u, MOD + 8)), (0, 0))
        r.finish(120000); r.finish(120000)
        self.assertEqual((word(r.u, EQ + 4), word(r.u, MOD + 4)), (0, 5))

    def test_channel_guard(self):
        r = Rig()
        r.meta(EQ, 17, 1, GRACE)
        self.assertEqual(r.channel(EQ, 99000), 0)                     # over 95,000 but in grace
        self.assertEqual(word(r.u, EQ + 4), 1)
        self.assertEqual(r.channel(EQ, HARD), 1)                      # hard limit still applies
        self.assertEqual((word(r.u, EQ + 4), word(r.u, EQ + 28)), (3, 1))
        r.meta(EQ, 17, 1, 0)
        self.assertEqual(r.channel(EQ, 99000), 1)                     # outside grace: 0.6.0 rule
        r.meta(EQ, 17, 1, 0)
        self.assertEqual(r.channel(EQ, 94000), 0)


class Regression060Tests(unittest.TestCase):
    """0.6.0's capture and long-IR suites against this image (grace counters start at 0)."""

    def test_060_suites(self):
        import test_capture_partitioned as P
        import test_long_ir as L
        import test_split_captures as s
        import test_fx_cache as cache
        c = P.c
        with patch.object(P, 'IMAGE', NEW), patch.object(P, 'META', NEW_META), \
             patch.object(L, 'NEW', NEW), patch.object(L, 'NEW_META', NEW_META), \
             patch.object(L, 'LOAD', NEW_META['symbols']['cab_load']):
            for name in ('test_builtins_after_capture_reuse_tcm_safely', 'test_real_fft_dc_nyquist_and_roundtrip',
                         'test_assembly_callee_saved_float_registers', 'test_whole_callback_guard',
                         'test_channel_guard_uses_fixed_deadline', 'test_mono_fast_path_and_initialization_deferral',
                         'test_split_bank_initialization_and_bounds', 'test_fir_impulse_tail_and_random',
                         'test_actual_capture_independent_stereo', 'test_both_slots_simultaneously_and_switch_reset',
                         'test_balanced_instruction_profile'):
                getattr(P.PartitionTests(), name)()
            for name in ('test_user_ir_plays_first_1024_samples', 'test_builtin_cab_bit_identical_to_052',
                         'test_registers_preserved', 'test_full_cab_processor_load_sequence',
                         'test_switching_ir_clears_history', 'test_mpu_region_covers_cab_state',
                         'test_instruction_profile'):
                getattr(L.LongIrTests(), name)()
            with patch.object(P.f.g, 'IMAGE', NEW), patch.object(P.f.g, 'META', NEW_META):
                P.f.g.GuardTests().test_deadline_latches_and_skips_remaining_processing()
            with patch.object(P.f.g.t, 'IMAGE', NEW), patch.object(P.f.g.t, 'META', NEW_META):
                P.f.g.t.SolidFillTests().test_all_twenty_capture_pages_and_buffer_selectors()
            with patch.object(c, 'IMAGE', NEW), patch.object(c, 'META', NEW_META):
                c.ChainFirTests().test_checkpoint_usb_transport_and_read_only()
                c.ChainFirTests().test_amp_and_cab_parent_output_parity()
                c.ChainFirTests().test_cab_384_taps_and_fp_register_preservation()
            with patch.object(P.f, 'IMAGE', NEW), patch.object(P.f, 'META', NEW_META):
                P.f.FastTests().test_fir_exact_history_wrap_and_aliasing()
            with patch.object(s, 'IMAGE', NEW), patch.object(s, 'META', NEW_META):
                for name in ('test_stock_protocol_accepts_twenty_and_rejects_twenty_one',
                             'test_storage_count_and_amp_descriptors', 'test_empty_fx_never_falls_back_to_amp',
                             'test_fx_display_names_and_wheel', 'test_capability_reply'):
                    getattr(s.SplitTests(), name)()
            with patch.object(cache, 'IMAGE', NEW), patch.object(cache, 'META', NEW_META):
                cache.CacheTests().test_diagnostic_and_three_effect_regressions()


if __name__ == '__main__':
    unittest.main(verbosity=2)
