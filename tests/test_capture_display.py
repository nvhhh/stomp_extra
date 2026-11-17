"""Render real stock glyph assets into framebuffer, including dirty prior pages."""
import json
import struct
import unittest
from unittest.mock import patch
import test_split_captures as s

b=s.b
IMAGE=b.master('build/soran-cfw-0.4.1-display-on-1.1.1.bin')
META=json.loads((b.ROOT/'patches/fx-split-display-fix/symbols.json').read_text())

def setup(image,meta):
    with patch.object(s,'IMAGE',image),patch.object(s,'META',meta): u=s.make()
    b.call(u,0x11b78)  # Real sprite offsets and glyph metrics, not zero RAM.
    u.mem_write(0x200101f8,struct.pack('<I',0x2001040c))
    u.mem_write(0x2001040c+0x6e,b'\x83')
    return u

def render(u,slot,index,dirty):
    u.mem_write(0x80000000,bytes([dirty])*(320*240*4))
    u.mem_write(0x2001040c+10,bytes([slot]))
    u.mem_write(b.EDIT+slot,bytes([0 if slot==7 else 5]))
    u.mem_write(b.EDIT+(67 if slot==7 else 68),bytes([0x60+index]))
    u.mem_write(b.EDIT+(37 if slot==7 else 50),bytes([50]*4))
    b.call(u,0x1fc56)
    b.call(u,0x1f59c,stop=0x1f458)
    b.call(u,0x1fa94,(0,120))
    return bytes(u.mem_read(0x80000000,320*240*2))

class DisplayTests(unittest.TestCase):
    def test_old_image_keeps_previous_pixels_new_image_clears_them(self):
        old=setup(s.IMAGE,s.META)
        self.assertNotEqual(render(old,7,0,0),render(old,7,0,0x55))
        new=setup(IMAGE,META)
        for slot in (7,3):
            for index in (0,9):
                clean=render(new,slot,index,0)
                self.assertEqual(clean,render(new,slot,index,0x55),(slot,index))
                self.assertEqual(struct.unpack('<H',new.mem_read(0x2001d0b4+0xc6,2))[0],0x396+index)
                self.assertEqual(bytes(new.mem_read(0x2000f3ec,5)),f'FX {index+1:02d}'.encode())

    def test_split_bank_and_dsp_regressions(self):
        with patch.object(s,'IMAGE',IMAGE),patch.object(s,'META',META):
            for name in unittest.defaultTestLoader.getTestCaseNames(s.SplitTests):
                with self.subTest(name=name): getattr(s.SplitTests(),name)()

if __name__=='__main__': unittest.main(verbosity=2)
