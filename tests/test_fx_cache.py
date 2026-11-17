"""Validate exact MPU footprint/startup hook and diagnostic/DSP regressions.

Unicorn does not simulate cache performance; hardware timing is still required.
"""
import json
import struct
import unittest
from unittest.mock import patch
import test_fx_diagnostics as d

b=d.b
IMAGE=b.master('build/soran-cfw-0.3.4-cache-diag-on-1.1.1.bin')
META=json.loads((b.ROOT/'patches/fx-cache-diagnostics/symbols.json').read_text())

class CacheTests(unittest.TestCase):
    def test_exact_region_and_preserved_registers(self):
        for regions in (8,16):
            with patch.object(d,'IMAGE',IMAGE),patch.object(d,'META',META):
                u=d.make()
            d.put(u,0xe000ed90,regions<<8)
            registers=[b.UC_ARM_REG_R0,b.UC_ARM_REG_R1,b.UC_ARM_REG_R2,b.UC_ARM_REG_R3]
            b.call(u,0xc3d6,(11,22,33,44),stop=0xc3da)
            self.assertEqual([u.reg_read(r) for r in registers],[11,22,33,44])
            if regions==8:
                self.assertEqual(b.word(u,0xe000ed9c),0)
                self.assertEqual(b.word(u,0xe000eda0),0)
                continue
            rbar=b.word(u,0xe000ed9c); rasr=b.word(u,0xe000eda0)
            self.assertEqual(rbar,0x81fa001a)
            self.assertEqual(rasr,0x1303c021)
            base=rbar&~31; size=1<<(((rasr>>1)&31)+1)
            self.assertEqual(base%size,0)
            self.assertEqual((rasr>>16)&63,3) # TEX=0, S=0, C=1, B=1
            self.assertEqual((rasr>>28)&1,1) # no executable data
            enabled=[]
            for i in range(8):
                if not rasr&(1<<(8+i)):
                    enabled.append((base+i*size//8,base+(i+1)*size//8))
            self.assertEqual(enabled[0][0],0x81fa0000)
            self.assertEqual(enabled[-1][1],0x81fb8000)
            self.assertEqual(sum(hi-lo for lo,hi in enabled),3*0x8000)
            self.assertLess(0x81f9d900,enabled[0][0])

    def test_diagnostic_and_three_effect_regressions(self):
        with patch.object(d,'IMAGE',IMAGE),patch.object(d,'META',META):
            checks=d.DiagnosticTests()
            checks.test_timing_wraparound_and_peak()
            checks.test_query_encoding_and_reject_write()
            checks.test_full_dispatch_and_usb_transport()
            checks.test_fault_breadcrumbs_without_stack_access()
            checks.test_three_effect_regression()

if __name__=='__main__': unittest.main(verbosity=2)
