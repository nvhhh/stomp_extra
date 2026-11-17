"""Execute the split-bank firmware, including bank isolation and cache regressions."""
import json
import struct
import unittest
from unittest.mock import patch
import test_fx_cache as cache
import test_fx_controls as c

b = c.base
IMAGE = b.master('build/soran-cfw-0.4.0-split-dev-on-1.1.1.bin')
META = json.loads((b.ROOT/'patches/fx-split-captures/symbols.json').read_text())

def make():
    with patch.object(cache.d, 'IMAGE', IMAGE), patch.object(cache.d, 'META', META):
        u = cache.d.make()
    # Stock image stops in the final original capture sector. Map the extension
    # explicitly; erased flash must never be confused with a valid capture.
    u.mem_map(0x60ede000, 0x1e000)
    u.mem_write(0x60ede000, b'\xff'*0x1e000)
    return u

class SplitTests(unittest.TestCase):
    def test_stock_protocol_accepts_twenty_and_rejects_twenty_one(self):
        for slot in (0,9,10,14,19,20,127):
            for write in (False,True):
                u=make(); accepted=[]
                # Stop after the actual decoded slot bound, before flash I/O.
                address=0xafb0 if write else 0xb08e
                def reached(uc,pc,size,user):
                    accepted.append(True)
                    uc.emu_stop()
                def reply(uc,pc,size,user):
                    uc.reg_write(b.UC_ARM_REG_PC,uc.reg_read(b.UC_ARM_REG_LR))
                u.hook_add(b.UC_HOOK_CODE,reached,begin=address,end=address)
                u.hook_add(b.UC_HOOK_CODE,reply,begin=0xa2ee,end=0xa2ee)
                u.ctl_remove_cache(0,0x40000)
                msg=(b.jme.bulk_messages(0x58,0,slot,3,b.jme.nam_name_record('test',1))[0]
                     if write else b.jme.sysex(0x58,0,b.jme.pack7(b.jme.bulk_header(0,slot,4))))
                u.mem_write(b.PARAM,msg)
                u.reg_write(b.UC_ARM_REG_SP,b.SP)
                u.reg_write(b.UC_ARM_REG_LR,b.STOP|1)
                for reg,val in zip((b.UC_ARM_REG_R0,b.UC_ARM_REG_R1,b.UC_ARM_REG_R2),(b.PARAM,len(msg),1)):
                    u.reg_write(reg,val)
                u.emu_start(0x9fc1,b.STOP,count=100000)
                self.assertEqual(bool(accepted),slot<20,(slot,write))

    def test_storage_count_and_amp_descriptors(self):
        u = make()
        self.assertEqual(bytes(u.mem_read(0x20010ba5,1)), b'\x14')
        self.assertEqual(IMAGE[0x258ec:0x258ec+40*32], b.STOCK[0x258ec:0x258ec+40*32])
        # AMP processor and its native selector remain stock.
        self.assertEqual(IMAGE[0x105c4:0x10900], b.STOCK[0x105c4:0x10900])

    def test_all_fx_coefficients_are_from_second_bank(self):
        u = make()
        for slot in range(10):
            amp = struct.pack('<2048f', *([0.125]*2048))
            fx = struct.pack('<2048f', *([0.25+slot/100]*2048))
            u.mem_write(0x60ec1000+slot*0x3000, amp)
            u.mem_write(0x60ec1000+(slot+10)*0x3000, fx)
            u.mem_write(0x3e020, bytes(32))
            for _ in range(90):
                b.call(u, META['symbols']['capture_init_step'], (slot,0x81fa0000,0x3e020))
                if u.reg_read(b.UC_ARM_REG_R0): break
            else: self.fail('initialization did not finish')
            for offset in (0x34,0x3134):
                self.assertEqual(bytes(u.mem_read(0x81fa0000+offset,8192)),fx)
            self.assertEqual(bytes(u.mem_read(0x60ec1000+slot*0x3000,8192)),amp)

    def test_empty_fx_never_falls_back_to_amp(self):
        u=make()
        for slot,spare,carrier,table in [(7,67,0,0x2000bd40),(3,68,5,0x2000be7c)]:
            u.mem_write(b.EDIT+slot,bytes([carrier]))
            for index in range(10):
                u.mem_write(0x60ec0000+index*0x3000+33,b'\x01')
                u.mem_write(b.EDIT+spare,bytes([0x60+index]))
                actual=b.audio(u,b.word(u,table+carrier*4),carrier)
                self.assertEqual(actual,bytes(u.mem_read(b.IN,32)+u.mem_read(b.OUT,32)))

    def test_fx_display_names_and_wheel(self):
        u=make()
        names=META['symbols']['fx_bank_names']
        for i in range(10):
            self.assertEqual(bytes(u.mem_read(names+i*32,32)).rstrip(b'\0'), f'FX {i+1:02d}'.encode())
        with patch.object(c,'make',make),patch.object(c,'META',META),patch.object(c,'IMAGE',IMAGE):
            c.ControlsTests().test_wheel_round_trip()
            c.ControlsTests().test_native_dispatch()

    def test_capability_reply(self):
        u=make(); replies=[]
        def reply(uc,addr,size,user):
            replies.append(bytes(uc.mem_read(uc.reg_read(b.UC_ARM_REG_R0),uc.reg_read(b.UC_ARM_REG_R1))))
            uc.reg_write(b.UC_ARM_REG_PC,uc.reg_read(b.UC_ARM_REG_LR))
        u.hook_add(b.UC_HOOK_CODE,reply,begin=0xa2ee,end=0xa2ee)
        u.ctl_remove_cache(0,0x40000)
        msg=b.jme.sysex(0x30,0)
        u.mem_write(b.PARAM,msg)
        b.call(u,META['symbols']['command'],(b.PARAM,len(msg),1))
        self.assertEqual(replies[0][7:11],b'FXA\x03')

    def test_cache_timing_usb_and_three_effect_regressions(self):
        with patch.object(cache,'IMAGE',IMAGE),patch.object(cache,'META',META):
            cache.CacheTests().test_exact_region_and_preserved_registers()
            cache.CacheTests().test_diagnostic_and_three_effect_regressions()

if __name__ == '__main__': unittest.main(verbosity=2)
