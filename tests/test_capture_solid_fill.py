"""Regression: capture background must fill pixels, never copy memory address 0."""
import json
import struct
import unittest
from unittest.mock import patch
import test_capture_display as d

b=d.b
IMAGE=b.master('build/soran-cfw-0.4.2-display-on-1.1.1.bin')
META=json.loads((b.ROOT/'patches/fx-split-solid-fill/symbols.json').read_text())

class SolidFillTests(unittest.TestCase):
    def test_reproduce_bad_bitmap_then_verify_real_fill(self):
        for image,meta,fixed in [(d.IMAGE,d.META,False),(IMAGE,META,True)]:
            u=d.setup(image,meta); calls=[]
            def entry(uc,pc,size,user):
                if pc in (0x12128,0x12188):
                    args=[uc.reg_read(r) for r in (b.UC_ARM_REG_R0,b.UC_ARM_REG_R1,b.UC_ARM_REG_R2,b.UC_ARM_REG_R3)]
                    arg5=b.word(uc,uc.reg_read(b.UC_ARM_REG_SP))
                    calls.append((pc,args,arg5))
            u.hook_add(b.UC_HOOK_CODE,entry,begin=0x12128,end=0x12188)
            u.ctl_remove_cache(0,0x40000)
            pixels=d.render(u,7,0,0x55)
            if not fixed:
                self.assertIn((0x12188,[0,0,320,240],0),calls)
            else:
                self.assertIn((0x12128,[0,0,240,320],0),calls)
                self.assertFalse(any(pc==0x12188 for pc,_,_ in calls))
                self.assertEqual(struct.unpack('<6H',u.mem_read(0x2001d0b4,12)),(0,0,3,0,240,320))
                # The bottom 80 rows contain no controls and must be black.
                for x in range(320):
                    self.assertEqual(pixels[(x*240+160)*2:(x*240+240)*2],bytes(160))
                self.assertNotEqual(pixels,bytes(len(pixels)))

    def test_all_twenty_capture_pages_and_buffer_selectors(self):
        u=d.setup(IMAGE,META)
        for slot in (7,3):
            for index in range(10):
                first=d.render(u,slot,index,0x55)
                self.assertEqual(first,d.render(u,slot,index,0xaa))
                # Both stock display-list comparison buffers use the same
                # framebuffer. Exercise the alternate selector too.
                b.call(u,0x1fc56)
                b.call(u,0x1f59c,stop=0x1f458)
                b.call(u,0x1fa94,(1,120))
                self.assertEqual(first,bytes(u.mem_read(0x80000000,320*240*2)))

    def test_inherited_regressions(self):
        with patch.object(d,'IMAGE',IMAGE),patch.object(d,'META',META):
            d.DisplayTests().test_old_image_keeps_previous_pixels_new_image_clears_them()
            d.DisplayTests().test_split_bank_and_dsp_regressions()

if __name__=='__main__': unittest.main(verbosity=2)
