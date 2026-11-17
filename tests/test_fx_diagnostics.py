"""Synthetic counters validate telemetry arithmetic, not hardware utilization."""
import json
import struct
import unittest
from unittest.mock import patch
import test_fx_controls as c
import test_fx_concurrency as concurrency
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS
from unicorn.arm_const import UC_ARM_REG_MSP, UC_ARM_REG_PSP, UC_CPU_ARM_CORTEX_M7

b = c.base
META = json.loads((b.ROOT/'patches/fx-diagnostics/symbols.json').read_text())
IMAGE = b.master('build/soran-cfw-0.3.3-diag-on-1.1.1.bin')
BASE, FAULT = 0x3e100, 0x3e180

def make():
    u = b.make(False)
    u.mem_write(0, IMAGE)
    u.ctl_remove_cache(0, 0x40000)
    u.mem_map(0xe0000000, 0x100000)
    u.mem_map(0x401ec000, 0x1000)
    b.call(u, META['symbols']['boot'], stop=0x76fc)
    u.mem_write(0x200101f4,struct.pack('<I',b.EDIT))
    return u

def put(u, a, v):
    u.mem_write(a, struct.pack('<I',v))

class DiagnosticTests(unittest.TestCase):
    def test_timing_wraparound_and_peak(self):
        u = make()
        self.assertEqual(b.word(u,0xe000edfc)&0x1000000,0x1000000)
        self.assertEqual(b.word(u,0xe0001000)&1,1)
        for start,end in [(0xffffff00,0xfffffff0),(0x100,0x280)]:
            put(u,0xe0001004,start)
            b.call(u,META['symbols']['diagnostic_begin'])
            self.assertEqual(b.word(u,BASE+20),1)
            put(u,0xe0001004,end)
            put(u,0x401ec024,165)
            b.call(u,META['symbols']['diagnostic_end'])
            self.assertEqual(b.word(u,BASE+20),0)
            self.assertEqual(b.word(u,BASE+12),(end-start)&0xffffffff)
        self.assertEqual(b.word(u,BASE),2)
        self.assertEqual(b.word(u,BASE+8),512)
        self.assertEqual(b.word(u,BASE+16),384)
        # The original end routine still returns its normalized timer value.
        self.assertEqual(u.reg_read(b.UC_ARM_REG_S0),0x3f800000)

    def test_query_encoding_and_reject_write(self):
        u=make()
        replies=[]
        def reply(uc,pc,size,context):
            size=uc.reg_read(b.UC_ARM_REG_R3)
            replies.append(bytes(uc.mem_read(uc.reg_read(b.UC_ARM_REG_R2),size)))
            uc.reg_write(b.UC_ARM_REG_PC,uc.reg_read(b.UC_ARM_REG_LR))
        u.hook_add(b.UC_HOOK_CODE,reply,begin=0x5248,end=0x5248)
        put(u,BASE,0xffffffff)
        msg=b.jme.sysex(0x31,0)
        u.mem_write(b.PARAM,msg)
        b.call(u,META['symbols']['diagnostic_read'],(b.PARAM,len(msg)))
        payload=replies.pop()
        self.assertEqual(len(payload),84)
        self.assertEqual(payload[:4],b'DGT1')
        self.assertTrue(all(x<128 for x in payload))
        self.assertEqual(sum(v<<(7*i) for i,v in enumerate(payload[4:9])),0xffffffff)
        self.assertEqual(payload[4:9],payload[-5:])
        u.mem_write(b.PARAM,b.jme.sysex(0x31,1))
        b.call(u,META['symbols']['diagnostic_read'],(b.PARAM,8))
        self.assertEqual(replies,[])

    def test_full_dispatch_and_usb_transport(self):
        u=make()
        replies=[]
        def send(uc,pc,size,context):
            length=uc.reg_read(b.UC_ARM_REG_R1)
            replies.append((bytes(uc.mem_read(uc.reg_read(b.UC_ARM_REG_R0),length)),
                            uc.reg_read(b.UC_ARM_REG_R2)))
            uc.reg_write(b.UC_ARM_REG_PC,uc.reg_read(b.UC_ARM_REG_LR))
        u.hook_add(b.UC_HOOK_CODE,send,begin=0xa2ee,end=0xa2ee)
        msg=b.jme.sysex(0x31,0)
        u.mem_write(b.PARAM,msg)
        for transport in (0,1,2):
            b.call(u,0x9fc0,(b.PARAM,len(msg),transport))
            packet,actual=replies.pop()
            self.assertEqual(actual,transport)
            self.assertEqual(packet[:11],b.jme.sysex(0x31,2)[:7]+b'DGT1')
            self.assertEqual(packet[-1],0xf7)
            self.assertEqual(len(packet),92)
        # The shipped 0.3.2 built the packet but supplied its signature as the
        # fifth argument (transport), reproducing the hardware no-reply symptom.
        old=b.master('build/soran-cfw-0.3.2-diag-on-1.1.1.bin')
        u.mem_write(0,old)
        u.ctl_remove_cache(0,0x40000)
        # Reinstall the historical handler address: newer payloads may place
        # diagnostics at a different address (e.g. split-bank name tables).
        old_symbols=json.loads((b.ROOT/'patches/fx-diagnostics/symbols.json').read_text())
        # 0.3.2 and 0.3.3 diagnostic_read share their entry address.
        command=0x20010cbc+0x485+0x31*9
        for off in (0,4):
            put(u,command+off,old_symbols['symbols']['diagnostic_read']|1)
        b.call(u,0x9fc0,(b.PARAM,len(msg),1))
        self.assertEqual(replies.pop()[1],0x31544744)

    def test_fault_breadcrumbs_without_stack_access(self):
        u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS)
        u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M7)
        u.mem_map(0,0x40000)
        u.mem_map(0xe000e000,0x1000)
        u.mem_write(0,IMAGE)
        u.reg_write(UC_ARM_REG_MSP,0x2003a000)
        u.reg_write(UC_ARM_REG_PSP,0x20039000)
        u.reg_write(b.UC_ARM_REG_LR,0xfffffff9)
        for a,v in [(0xe000ed28,0x8200),(0xe000ed2c,0x40000000),
                    (0xe000ed34,0x1234),(0xe000ed38,0xdeadbeef)]:
            put(u,a,v)
        u.emu_start(META['symbols']['diagnostic_fault']|1,0,count=100)
        values=struct.unpack('<9I',u.mem_read(FAULT,36))
        self.assertEqual(values[:2],(0x314c5446,0xfffffff9))
        self.assertEqual(values[3:],(0x2003a000,0x20039000,0x8200,0x40000000,0x1234,0xdeadbeef))
        for off in (12,16,20,24):
            self.assertEqual(b.word(u,off),META['symbols']['diagnostic_fault']|1)

    def test_three_effect_regression(self):
        with patch.object(c,'make',make):
            concurrency.ConcurrencyTests().test_three_parent_blocks_match_independent_engines()


if __name__=='__main__': unittest.main(verbosity=2)
