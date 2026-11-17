"""Parity for scheduled capture/AMP/CAB filtering and read-only checkpoint USB."""
import json
import random
import struct
import unittest
from unittest.mock import patch
import test_capture_fast as f
b=f.b
IMAGE=b.master('build/soran-cfw-0.4.5-chain-diag-on-1.1.1.bin')
META=json.loads((b.ROOT/'patches/fx-chain-fir/symbols.json').read_text())

class ChainFirTests(unittest.TestCase):
    def test_capture_and_guard_parity(self):
        with patch.object(f,'IMAGE',IMAGE),patch.object(f,'META',META):
            f.FastTests().test_fir_exact_history_wrap_and_aliasing()
            f.FastTests().test_exact_fx01_stereo_output_and_profile()
            f.FastTests().test_guard_display_and_bank_regressions()

    def test_cab_384_taps_and_fp_register_preservation(self):
        from unicorn.arm_const import UC_ARM_REG_D8,UC_ARM_REG_D9,UC_ARM_REG_D10,UC_ARM_REG_D11,UC_ARM_REG_D12
        rng=random.Random(315)
        old=f.g.t.d.setup(f.IMAGE,f.META);new=f.g.t.d.setup(IMAGE,META)
        regs=(UC_ARM_REG_D8,UC_ARM_REG_D9,UC_ARM_REG_D10,UC_ARM_REG_D11,UC_ARM_REG_D12)
        for pos in (0,1,4,504,508,511):
            for u in (old,new):
                u.mem_write(0x20060000,struct.pack('<512f',*([.125]*512)))
                u.mem_write(0x20062000,struct.pack('<I',pos))
            coeff=struct.pack('<384f',*[rng.uniform(-1,1) for _ in range(384)])
            inputs=struct.pack('<8f',*[rng.uniform(-1,1) for _ in range(8)])
            for u,fn in ((old,0x13f84),(new,META['symbols']['capture_fir8'])):
                u.mem_write(0x20061000,coeff);u.mem_write(b.IN,inputs)
                for i,r in enumerate(regs):u.reg_write(r,0x1234567800000000+i)
                b.call(u,fn,(b.IN,b.OUT,0x20061000,0x20060000),(0x20062000,512,384,8))
                self.assertEqual([u.reg_read(r) for r in regs],[0x1234567800000000+i for i in range(5)])
            self.assertEqual(bytes(old.mem_read(b.OUT,32)),bytes(new.mem_read(b.OUT,32)))

    def test_amp_and_cab_parent_output_parity(self):
        rec=bytearray.fromhex(json.loads((b.ROOT/'work/fx01-before-fast-test.json').read_text())['edit'])
        for model in (0,14,29):
            engines=[f.g.t.d.setup(f.IMAGE,f.META),f.g.t.d.setup(IMAGE,META)]
            rec[1]=rec[2]=model
            for u in engines:
                u.mem_write(b.EDIT,bytes(rec))
                for obj,slot in [(0x2000bc10,0),(0x2000bd08,7),(0x2000be44,3),(0x2000bf30,5),(0x2000bb2c,4),(0x20004998,2),(0x20008450,1)]:
                    u.mem_write(obj,bytes([rec[slot]&63]*2))
                b.call(u,0xe0b2)
            for block in range(100):
                data=struct.pack('<8f',*[.1*((i*7+block)%13-6) for i in range(8)])
                for parent in (0x105c4,0x14bd0):
                    out=[]
                    for u in engines:
                        u.mem_write(b.IN,data);u.mem_write(b.OUT,data)
                        b.call(u,parent,(b.IN,b.OUT,b.LEFT,b.RIGHT))
                        out.append(bytes(u.mem_read(b.LEFT,32)+u.mem_read(b.RIGHT,32)))
                    self.assertEqual(*out,(model,block,parent))

    def test_checkpoint_usb_transport_and_read_only(self):
        u=f.g.t.d.setup(IMAGE,META);replies=[]
        values=[17,3,70000,132546,2,0,0,0,0,0]
        for n,base in enumerate((0x3e020,0x3e040)):
            for off,val in zip((0,4,20,24,28),values[n*5:n*5+5]):u.mem_write(base+off,struct.pack('<I',val))
        def reply(uc,pc,size,ctx):
            replies.append((bytes(uc.mem_read(uc.reg_read(b.UC_ARM_REG_R0),uc.reg_read(b.UC_ARM_REG_R1))),uc.reg_read(b.UC_ARM_REG_R2)))
            uc.reg_write(b.UC_ARM_REG_PC,uc.reg_read(b.UC_ARM_REG_LR))
        u.hook_add(b.UC_HOOK_CODE,reply,begin=0xa2ee,end=0xa2ee);u.ctl_remove_cache(0,0x40000)
        for transport in (0,1,2):
            msg=b.jme.sysex(0x32,0);u.mem_write(b.PARAM,msg)
            b.call(u,0x9fc0,(b.PARAM,len(msg),transport))
            packet,actual=replies.pop();self.assertEqual(actual,transport)
            self.assertEqual(packet[7:11],b'CGC1')
            payload=packet[11:-1]
            decoded=[sum(x<<(7*j) for j,x in enumerate(payload[i:i+5])) for i in range(0,50,5)]
            self.assertEqual(decoded,values)
        before=bytes(u.mem_read(0x3e020,64))
        for msg in (b.jme.sysex(0x32,1),b.jme.sysex(0x32,0,b'\0')):
            u.mem_write(b.PARAM,msg);b.call(u,0x9fc0,(b.PARAM,len(msg),1))
        self.assertEqual(replies,[]);self.assertEqual(before,bytes(u.mem_read(0x3e020,64)))

if __name__=='__main__':unittest.main(verbosity=2)
