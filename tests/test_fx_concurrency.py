"""Regression for cached BD2 / Red Comp / Red Comp, using stock parent DSP.

Executes the shipped 0.3.1 machine code. This is functional emulation, not
hardware timing, interrupt scheduling, MPU or cache validation.
"""
import math
import struct
import unittest
import test_fx_controls as controls

b = controls.base
# parent, object, slot, native carrier / model
BLOCKS = [(0x140f0, 0x2000bc10, 0, 7),
          (0x15108, 0x2000bd08, 7, 0),
          (0x14368, 0x2000be44, 3, 5)]


def setup():
    u = controls.make()
    record = bytearray(98)
    record[14:18] = bytes([33, 39, 66, 0])
    record[37:41] = record[50:54] = bytes([50]*4)
    record[67:69] = b'\x50\x50'
    for _, obj, slot, model in BLOCKS:
        record[slot] = model
        # Stable native selection; extra DSP initializes through real wrappers.
        u.mem_write(obj, bytes([model, model]))
    u.mem_write(b.EDIT, bytes(record))
    b.init_stock(u, 7)
    return u


class ConcurrencyTests(unittest.TestCase):
    def test_three_parent_blocks_match_independent_engines(self):
        combined = setup()
        isolated = [setup() for _ in BLOCKS]
        for block in range(220):
            data = struct.pack('<8f', *[0.1*((i*7+block)%13-6) for i in range(8)])
            for n, (parent, _, _, _) in enumerate(BLOCKS):
                results = []
                for u in (combined, isolated[n]):
                    u.mem_write(b.IN, data)
                    u.mem_write(b.OUT, data)
                    b.call(u, parent, (b.IN, b.OUT, b.LEFT, b.RIGHT))
                    results.append(bytes(u.mem_read(b.LEFT,32)+u.mem_read(b.RIGHT,32)))
                self.assertEqual(results[0], results[1], (block, n))
                self.assertTrue(all(math.isfinite(v) for v in struct.unpack('<16f', results[0])))
        for meta in (0x3e020, 0x3e040):
            self.assertEqual(b.word(combined, meta+4), 8)


if __name__ == '__main__':
    unittest.main(verbosity=2)
