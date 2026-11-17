"""Bit-exact FIR and full capture parity; instruction counts are not CPU cycles."""
import json
import random
import struct
import unittest
from unittest.mock import patch
import test_capture_guard as g
b=g.b
IMAGE=b.master('build/soran-cfw-0.4.4-fast-diag-on-1.1.1.bin')
META=json.loads((b.ROOT/'patches/fx-capture-fast/symbols.json').read_text())

class FastTests(unittest.TestCase):
    def test_fir_exact_history_wrap_and_aliasing(self):
        rng=random.Random(5719)
        old=g.t.d.setup(g.IMAGE,g.META);new=g.t.d.setup(IMAGE,META)
        for start in (0,1,4,7,127,504,508,511):
            for alias in (False,True):
                data=[rng.uniform(-2,2) for _ in range(512)]
                coeff=[rng.uniform(-1,1) for _ in range(512)]
                for u in (old,new):
                    u.mem_write(0x20060000,struct.pack('<512f',*data))
                    u.mem_write(0x20061000,struct.pack('<512f',*coeff))
                    u.mem_write(0x20062000,struct.pack('<I',start))
                for block in range(4):
                    samples=struct.pack('<8f',*[rng.uniform(-1,1) for _ in range(8)])
                    out=b.IN if alias else b.OUT
                    for u,fn in ((old,0x13f84),(new,META['symbols']['capture_fir8'])):
                        u.mem_write(b.IN,samples)
                        b.call(u,fn,(b.IN,out,0x20061000,0x20060000),(0x20062000,512,512,8))
                    self.assertEqual(bytes(old.mem_read(out,32)),bytes(new.mem_read(out,32)),(start,alias,block))
                    self.assertEqual(bytes(old.mem_read(0x20060000,2048)),bytes(new.mem_read(0x20060000,2048)))
                    self.assertEqual(b.word(old,0x20062000),b.word(new,0x20062000))

    def test_exact_fx01_stereo_output_and_profile(self):
        old=g.t.d.setup(g.IMAGE,g.META);new=g.t.d.setup(IMAGE,META)
        for u in (old,new):
            u.mem_write(0x60ede000,(b.ROOT/'backups/fx01-crash-metadata.bin').read_bytes())
            u.mem_write(0x60edf000,(b.ROOT/'backups/fx01-crash-coefficients.bin').read_bytes())
            u.mem_write(b.EDIT+7,b'\0');u.mem_write(b.EDIT+67,b'\x60')
        funcs=[b.word(u,0x2000bd40) for u in (old,new)]
        rng=random.Random(115)
        for block in range(250):
            params=(block%100, (block*3)%100, 0, 0)
            left=struct.pack('<8f',*[rng.uniform(-.2,.2) for _ in range(8)])
            right=struct.pack('<8f',*[rng.uniform(-.2,.2) for _ in range(8)])
            outputs=[]
            for u,fn in zip((old,new),funcs):
                u.mem_write(b.IN,left);u.mem_write(b.OUT,right)
                u.mem_write(b.PARAM,bytes([0,0,0,*params,0]))
                b.call(u,fn,(b.IN,b.OUT,b.LEFT,b.RIGHT),(b.PARAM,0))
                outputs.append(bytes(u.mem_read(b.LEFT,32)+u.mem_read(b.RIGHT,32)))
            self.assertEqual(*outputs, f'block {block}')
        counts=[]
        for u,fn in zip((old,new),funcs):
            n=[0]
            def count(*args): n[0]+=1
            u.hook_add(b.UC_HOOK_CODE,count);u.ctl_remove_cache(0,0x40000)
            b.audio(u,fn,0)
            counts.append(n[0])
        self.assertLess(counts[1],counts[0])
        print('Stereo wrapper instruction counts (not cycles):',counts)
        (b.ROOT/'work/fx01-fast-profile.json').write_text(json.dumps({'old_instructions':counts[0],'new_instructions':counts[1],'hardware_cycles_unverified':True},indent=2))

    def test_guard_display_and_bank_regressions(self):
        with patch.object(g,'IMAGE',IMAGE),patch.object(g,'META',META):
            g.GuardTests().test_deadline_latches_and_skips_remaining_processing()
            g.GuardTests().test_safe_capture_and_other_regressions()

if __name__=='__main__': unittest.main(verbosity=2)
