"""Execute the development wheel and converted-capture code in Unicorn."""
import json
import struct
import unittest
import math
from unittest.mock import patch
import test_fx_anywhere as base

META = json.loads((base.ROOT/'patches/fx-controls/symbols.json').read_text())
IMAGE = base.master('build/soran-cfw-0.3.1-dev-on-1.1.1.bin')


def make():
    with patch.object(base, 'META', META), patch.object(base, 'PATCHED', IMAGE):
        u = base.make()
    u.mem_write(0x200101f4, struct.pack('<I', base.EDIT))
    return u


class ControlsTests(unittest.TestCase):
    def test_wheel_defaults_do_not_use_unaligned_word_accesses(self):
        # Unicorn does not enforce the target's memory attributes. Inspect the
        # effective address BEFORE each custom word access, without memory hooks
        # (which alter execution of the vendor's IT-block memcpy in Unicorn).
        from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, arm_const
        from unicorn import arm_const as regs
        decoder=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
        decoder.detail=True
        def watch(u):
            violations=[]
            def instruction(uc,pc,size,context):
                if not 0x38100 <= pc < 0x3b000: return
                ins=next(decoder.disasm(bytes(uc.mem_read(pc,size)),pc))
                if ins.mnemonic not in ('ldr','ldr.w','str','str.w'): return
                for op in ins.operands:
                    if op.type != arm_const.ARM_OP_MEM: continue
                    mem=op.mem
                    if ins.reg_name(mem.base)=='pc': continue
                    def value(reg):
                        return uc.reg_read(getattr(regs,'UC_ARM_REG_'+ins.reg_name(reg).upper())) if reg else 0
                    address=value(mem.base)+value(mem.index)+mem.disp
                    if address%4:
                        violations.append((pc,address))
            u.hook_add(base.UC_HOOK_CODE,instruction)
            return violations
        # Prove the regression detects the shipped image at the reported step.
        old=base.make(False)
        old.mem_write(0,base.master('build/soran-cfw-0.3.0-dev-on-1.1.1.bin'))
        old.mem_write(0x200101f4,struct.pack('<I',base.EDIT))
        old.mem_write(base.EDIT+7,b'\x01')
        old.mem_write(0x2001f769,b'\x02')
        failures=watch(old)
        base.call(old,0x4ae0,(7,))
        self.assertTrue(any(address==0x2907a for _,address in failures))
        for slot,spare,count,param in [(7,67,2,37),(3,68,13,50)]:
            u=make()
            failures=watch(u)
            u.mem_write(base.EDIT+slot,bytes([count-1]))
            for model in range(26):
                u.mem_write(0x2001f769,b'\x02')
                base.call(u,0x4ae0,(slot,))
                self.assertEqual(u.mem_read(base.EDIT+spare,1)[0],0x50+model)
                expected=base.STOCK[0x2907a+model*7:0x2907e+model*7] if model<16 else bytes([50]*4)
                self.assertEqual(bytes(u.mem_read(base.EDIT+param,4)),expected)
            self.assertEqual(failures,[])

    def test_capture_commands_recall_and_chain(self):
        u=make()
        replies=[]
        def reply(uc,addr,size,user):
            replies.append(bytes(uc.mem_read(uc.reg_read(base.UC_ARM_REG_R0),uc.reg_read(base.UC_ARM_REG_R1))))
            uc.reg_write(base.UC_ARM_REG_PC,uc.reg_read(base.UC_ARM_REG_LR))
        u.hook_add(base.UC_HOOK_CODE,reply,begin=0xa2ee,end=0xa2ee)
        def send(msg):
            u.mem_write(base.PARAM,msg)
            base.call(u,META['symbols']['command'],(base.PARAM,len(msg),1))
        send(base.jme.sysex(0x30,0))
        self.assertEqual(replies.pop()[7:11],b'FXA\x02')
        for slot,spare,meta in [(7,67,0x3e020),(3,68,0x3e040)]:
            for model in range(26):
                u.mem_write(meta,struct.pack('<I',99))
                send(base.jme.sysex(0x30,1,bytes([slot,model+1])))
                self.assertEqual(u.mem_read(base.EDIT+spare,1)[0],model+0x50)
                self.assertEqual(base.word(u,meta),0)
                self.assertEqual(replies.pop()[6],3)
        before=bytes(u.mem_read(base.EDIT,98))
        for data in [b'\x04\x11',b'\x07\x1b',b'\x02\x11',b'\x03',b'\x07\x11\0']:
            send(base.jme.sysex(0x30,1,data))
        self.assertFalse(replies)
        self.assertEqual(before,bytes(u.mem_read(base.EDIT,98)))
        u.mem_write(0x2002979c+17*128,before)
        u.mem_write(base.EDIT,bytes(98))
        base.call(u,0x4f1e,(17,))
        self.assertEqual(before,bytes(u.mem_read(base.EDIT,98)))
        import test_chain
        with patch.object(base,'META',META),patch.object(base,'PATCHED',IMAGE):
            test_chain.ChainTests().test_actual_vendor_handlers_and_dispatch()

    def test_capture_slot_isolation_and_empty_slots(self):
        u=make()
        reference=base.make(False)
        base.call(reference,0x1078c,(0,))
        coefficients=bytes(reference.mem_read(0x200086e8+0x34,8192))
        for model in range(10):
            u.mem_write(0x60ec0000+model*0x3000+33,b'\x01')
            u.mem_write(0x60ec1000+model*0x3000,coefficients)
        amp_before=bytes(u.mem_read(0x20008450,0x3800))
        funcs=[]
        for slot,spare,carrier,table in [(7,67,0,0x2000bd40),(3,68,5,0x2000be7c)]:
            u.mem_write(base.EDIT+slot,bytes([carrier]))
            funcs.append(base.word(u,table+4*carrier))
        for model in range(10):
            u.mem_write(base.EDIT+67,bytes([0x60+model,0x60+model]))
            for block in range(90):
                left=base.audio(u,funcs[0],0,params=(50,50,0,0))
                right=base.audio(u,funcs[1],5,params=(50,50,0,0))
                self.assertEqual(left,right,(model,block))
                self.assertTrue(all(math.isfinite(v) for v in struct.unpack('<16f',left)))
            self.assertTrue(any(left))
        self.assertEqual(amp_before,bytes(u.mem_read(0x20008450,0x3800)))
        u.mem_write(0x60ec0000+9*0x3000+33,b'\x00')
        dry=base.audio(u,funcs[0],0)
        self.assertEqual(dry,bytes(u.mem_read(base.IN,32)+u.mem_read(base.OUT,32)))

    def test_invalid_capture_is_dry(self):
        u=make()
        u.mem_write(base.EDIT+7,b'\0')
        u.mem_write(base.EDIT+67,b'\x60')
        u.mem_write(0x60ec0000+33,b'\x01')
        u.mem_write(0x60ec1000,struct.pack('<I',0x7fc00000))
        fn=base.word(u,0x2000bd40)
        for _ in range(90): actual=base.audio(u,fn,0)
        self.assertEqual(actual,bytes(u.mem_read(base.IN,32)+u.mem_read(base.OUT,32)))
        self.assertEqual(base.word(u,0x3e024),2)

    def test_native_dispatch(self):
        for slot,spare,carrier,table,count in base.SLOTS:
            for model in range(count):
                for marker in [0,0x4f,0x6a,0xff]+([0x60] if model!=carrier else []):
                    u=make()
                    original=struct.unpack_from('<I',base.RAM,table-0x20000000+model*4)[0]
                    u.mem_write(base.EDIT+spare,bytes([marker]))
                    u.mem_write(base.EDIT+slot,bytes([model]))
                    base.call(u,base.word(u,table+4*model),(11,22,33,44),(base.PARAM,0),stop=original&~1)
                    self.assertEqual([u.reg_read(r) for r in [base.UC_ARM_REG_R0,base.UC_ARM_REG_R1,
                                                             base.UC_ARM_REG_R2,base.UC_ARM_REG_R3]], [11,22,33,44])

    def test_od_regressions_on_new_image(self):
        names=[n for n in unittest.defaultTestLoader.getTestCaseNames(base.FirmwareTests)
               if n not in ('test_command_validation_and_transport','test_protected_regions_identical',
                            'test_native_dispatch_preserves_arguments')]
        with patch.object(base,'META',META),patch.object(base,'PATCHED',IMAGE):
            for name in names:
                with self.subTest(name=name): getattr(base.FirmwareTests(),name)()

    def test_display_and_parameter_bounds(self):
        for slot, spare, carrier, param in [(7,67,0,37),(3,68,5,50)]:
            for model in range(26):
                u=make()
                settings=0x2001040c
                u.mem_write(0x200101f8,struct.pack('<I',settings))
                u.mem_write(settings+10,bytes([slot]))
                u.mem_write(settings+0x6e,b'\x83')
                u.mem_write(base.EDIT+slot,bytes([carrier]))
                u.mem_write(base.EDIT+spare,bytes([0x50+model]))
                u.mem_write(base.EDIT+param,bytes([50,50,50,50]))
                base.call(u,0x4bfe,(slot,))
                count=u.reg_read(base.UC_ARM_REG_R0)
                self.assertEqual(count,2 if model>=16 else base.STOCK[0x28ca5+model*7])
                if model>=16:
                    u.mem_write(0x60ec0000+(model-16)*0x3000,b'Test Capture\0'+bytes(19))
                base.call(u,0x1f59c,stop=0x1f458)
                commands=bytes(u.mem_read(0x2001d0b4,0xc00))
                if model<16:
                    expected=struct.unpack('<H',u.mem_read(0x20012c34+model*8+2,2))[0]
                    self.assertEqual(struct.unpack_from('<H',commands,6)[0],expected)
                else:
                    self.assertEqual(struct.unpack_from('<H',commands,6)[0],65535)
                    # The native text path receives the capture's actual user name.
                    self.assertEqual(bytes(u.mem_read(0x2000f3dc+16,12)),b'Test Capture')
                for index in range(1,count+1):
                    u.mem_write(settings+0x6e,bytes([0x83+index]))
                    u.mem_write(0x2001f769,b'\x02')
                    u.mem_write(base.EDIT+param+index-1,b'\x64')
                    base.call(u,0x4ce0,(slot,))
                    limit=99 if model>=16 else base.STOCK[0x28ca5+model*7+index]
                    self.assertEqual(u.mem_read(base.EDIT+param+index-1,1)[0],limit)

    def test_wheel_round_trip(self):
        for slot, spare, carrier, count in [(7,67,0,2),(3,68,5,13)]:
            u = make()
            u.mem_write(base.EDIT+slot, b'\x40')
            for direction, indexes in [(2,range(1,count+26)),(1,range(count+24,-1,-1))]:
                for i in indexes:
                    u.mem_write(0x2001f769, bytes([direction]))
                    base.call(u,0x4ae0,(slot,))
                    rec = bytes(u.mem_read(base.EDIT,98))
                    self.assertEqual(rec[slot], 0x40 | (i if i<count else carrier))
                    self.assertEqual(rec[spare],0 if i<count else 0x50+i-count)
                    self.assertEqual(rec[70:78],bytes(8))

    def test_capture_core_matches_stock_without_global_mutation(self):
        # Coefficients from an actual built-in capture exercise both FIR stages.
        stock, custom = base.make(False), make()
        base.call(stock,0x1078c,(0,))
        state = bytes(stock.mem_read(0x200086e8,0x303c))
        custom.mem_write(0x81fa0000,state)
        custom.mem_write(0x3b000,bytes(stock.mem_read(0x20000000,8)))
        scratch_before = bytes(custom.mem_read(0x20000000,0x8c))
        for drive in [0,50,99,100]:
            stock.mem_write(0x200084ec,struct.pack('<f',drive))
            for block in range(5):
                data = struct.pack('<8f',*[0.1*((i*7+block)%13-6) for i in range(8)])
                stock.mem_write(base.IN,data)
                custom.mem_write(base.IN,data)
                base.call(stock,0x17bd4,(base.IN,base.OUT,0,0x200086e8),(8,))
                base.call(custom,META['symbols']['capture_core'],
                          (base.IN,base.OUT,drive,0x81fa0000),(0x3b000,))
                self.assertEqual(bytes(stock.mem_read(base.OUT,32)),bytes(custom.mem_read(base.OUT,32)))
        self.assertEqual(scratch_before,bytes(custom.mem_read(0x20000000,0x8c)))

    def test_capture_initializer_is_bounded_and_separate(self):
        u=make()
        # Distinct deterministic coefficient data in all ten user slots.
        for model in range(10):
            data=struct.pack('<2048f',*[float((i+model)%17)/100 for i in range(2048)])
            u.mem_write(0x60ec1000+model*0x3000,data)
            meta=0x3e020
            u.mem_write(meta,bytes(32))
            u.mem_write(0x81fa0000,b'\xaa'*0x8000)
            calls=0
            while True:
                writes=[]
                hook=u.hook_add(base.UC_HOOK_MEM_WRITE,lambda uc,access,addr,size,val,ctx:writes.append((addr,size)))
                base.call(u,META['symbols']['capture_init_step'],(model,0x81fa0000,meta))
                u.hook_del(hook)
                self.assertLessEqual(sum(size for addr,size in writes if 0x81fa0000<=addr<0x81fa8000),512)
                calls+=1
                if u.reg_read(base.UC_ARM_REG_R0): break
                self.assertLess(calls,100)
            for offset in [0x34,0x3134]:
                self.assertEqual(bytes(u.mem_read(0x81fa0000+offset,8192)),data)
            self.assertEqual(bytes(u.mem_read(0x81fa6200,0x1e00)),b'\xaa'*0x1e00)


if __name__=='__main__': unittest.main(verbosity=2)
