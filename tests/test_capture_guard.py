"""Synthetic DWT deadline tests; these do not establish actual hardware timing."""
import json
import struct
import unittest
from unittest.mock import patch
import test_capture_solid_fill as t
b=t.b
IMAGE=b.master('build/soran-cfw-0.4.3-guard-diag-on-1.1.1.bin')
META=json.loads((b.ROOT/'patches/fx-capture-guard/symbols.json').read_text())

class GuardTests(unittest.TestCase):
    def test_deadline_latches_and_skips_remaining_processing(self):
        for trip in (0,1,2):
            u=t.d.setup(IMAGE,META)
            u.mem_write(0x60ede000,(b.ROOT/'backups/fx01-crash-metadata.bin').read_bytes())
            u.mem_write(0x60edf000,(b.ROOT/'backups/fx01-crash-coefficients.bin').read_bytes())
            u.mem_write(b.EDIT+7,b'\0');u.mem_write(b.EDIT+67,b'\x60')
            fn=b.word(u,0x2000bd40)
            for _ in range(100): b.audio(u,fn,0)
            u.mem_write(0x3e104,struct.pack('<II',0xffff0000,100000))
            u.mem_write(0x3e114,struct.pack('<I',1))
            cores=[]
            def hook(uc,pc,size,ctx):
                if pc==META['symbols']['capture_core']: cores.append(pc)
                if pc==META['symbols']['capture_budget_guard']:
                    channel=uc.reg_read(b.UC_ARM_REG_R1)
                    elapsed=98000 if channel==trip else 1000
                    uc.mem_write(0xe0001004,struct.pack('<I',(0xffff0000+elapsed)&0xffffffff))
            u.hook_add(b.UC_HOOK_CODE,hook);u.ctl_remove_cache(0,0x40000)
            result=b.audio(u,fn,0)
            self.assertEqual(len(cores),trip)
            self.assertEqual(b.word(u,0x3e024),3)
            self.assertEqual(b.word(u,0x3e03c),trip)
            self.assertEqual(result,bytes(u.mem_read(b.IN,32)+u.mem_read(b.OUT,32)))
            for _ in range(3): b.audio(u,fn,0)
            self.assertEqual(len(cores),trip)

    def test_safe_capture_and_other_regressions(self):
        with patch.object(t,'IMAGE',IMAGE),patch.object(t,'META',META):
            t.SolidFillTests().test_all_twenty_capture_pages_and_buffer_selectors()
            t.SolidFillTests().test_inherited_regressions()

if __name__=='__main__': unittest.main(verbosity=2)
