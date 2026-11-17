"""Execute the actual patched Thumb code, not a Python routing approximation."""
import json
import math
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from nuxfw.container import Firmware
from nuxfw import layout, jme
from tools.emu_init import initialize

STOP, SP = 0x7fff0, 0x2007f000
IN, OUT, LEFT, RIGHT, PARAM = 0x20070000,0x20071000,0x20072000,0x20072100,0x20073000
EDIT = 0x200102a0
SLOTS = [(7,67,0,0x2000bd40,2), (3,68,5,0x2000be7c,13), (4,69,2,0x2000bb70,7)]
META = json.loads((ROOT/'patches/fx-anywhere/symbols.json').read_text())

def master(path):
    img = Firmware.parse((ROOT/path).read_bytes()).image
    start = layout.region('master').start
    return img[start:start+0x40000]

STOCK = master('firmware/stock/JME-EN_V1.1.1_modified.bin')
PATCHED = master('build/soran-cfw-0.2.0-fx-on-1.1.1.bin')
RAM = bytes(initialize(STOCK).mem_read(0x20000000,0x40000))
FLASH = Firmware.parse((ROOT/'firmware/stock/JME-EN_V1.1.1_modified.bin').read_bytes()).image

def make(patched=True):
    # Unicorn's M7 model lacks double precision VFP used by the vendor DSP.
    # A15 executes the same Thumb/VFP instructions; this does not model M7 timing.
    u = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_A15)
    for base,size in [(0,0x80000),(0x20000000,0x80000),(0x20200000,0x100000),(0x80000000,0x2000000)]:
        u.mem_map(base,size)
    u.mem_write(0, PATCHED if patched else STOCK)
    u.mem_write(0x20000000,RAM)
    u.mem_map(0x60040000,(len(FLASH)+4095)&~4095)
    u.mem_write(0x60040000,FLASH)
    # Explicitly enable the FPU, as hardware startup does.
    u.reg_write(UC_ARM_REG_C1_C0_2, 0xf << 20)
    u.reg_write(UC_ARM_REG_FPEXC, 0x40000000)
    # main() copies the shared DSP gain/lookup tables after IAR data initialization.
    call(u,0xdd44)
    if patched:
        call(u, META['symbols']['boot'], stop=0x76fc)
    return u

def call(u,fn,args=(),stack=(),stop=STOP):
    u.reg_write(UC_ARM_REG_SP,SP)
    u.reg_write(UC_ARM_REG_LR,STOP|1)
    for reg,val in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],args):
        u.reg_write(reg,val)
    if stack: u.mem_write(SP,struct.pack('<'+'I'*len(stack),*stack))
    u.emu_start(fn|1,stop,count=3_000_000)
    assert u.reg_read(UC_ARM_REG_PC)==stop, f'budget exhausted at {u.reg_read(UC_ARM_REG_PC):#x}'
    assert u.reg_read(UC_ARM_REG_SP)==SP, 'unbalanced stack'

def word(u,addr): return struct.unpack('<I',u.mem_read(addr,4))[0]

def audio(u, fn, model, instance=0, params=(50,50,50,50)):
    u.mem_write(PARAM,bytes([0,0,model,*params,0]))
    u.mem_write(IN,struct.pack('<64f',*[0.1*((i*37%17)-8)/8 for i in range(64)]))
    call(u,fn,(IN,OUT,LEFT,RIGHT),(PARAM,instance))
    return bytes(u.mem_read(LEFT,32)+u.mem_read(RIGHT,32))

def init_stock(u,model):
    call(u,0x14244,(model,0))

def prepare(u,n,model):
    slot,spare,carrier,table,_=SLOTS[n-1]
    u.mem_write(EDIT+spare,bytes([0x50+model]))
    u.mem_write(EDIT+slot,bytes([carrier]))
    # Initialize in bounded chunks without running a DSP block yet.
    meta=0x3e000+n*32
    u.mem_write(meta,struct.pack('<II',model+1,0))
    u.mem_write(meta+16,bytes(4))
    for _ in range(200):
        call(u,META['symbols']['initialize_step'],(model,0x3a000+n*0x1000,0x81f98000+n*0x8000,meta))
        if u.reg_read(UC_ARM_REG_R0): return
    raise AssertionError('initialization did not complete')

class FirmwareTests(unittest.TestCase):
    def test_boot_installs_and_original_instance(self):
        u=make()
        for addr,value in META['installs']: self.assertEqual(word(u,addr),value)
        self.assertEqual(word(u,0x38100),0x2003e000)
        self.assertEqual(word(u,0x38110),0x20200000)

    def test_all_models_match_stock_in_all_slots(self):
        for model in range(16):
            stock=make(False)
            init_stock(stock,model)
            fn=word(stock,0x2000bc48+4*model)
            cases=[(51,50,50,50),(0,99,30,70),(99,20,80,10)]
            expected=[audio(stock,fn,model,params=p) for p in cases]
            samples=struct.unpack('<48f',b''.join(expected))
            self.assertTrue(all(math.isfinite(x) for x in samples),model)
            self.assertTrue(any(x != 0 for x in samples),model)
            for slot,spare,carrier,table,_ in SLOTS:
                with self.subTest(model=model,slot=slot):
                    u=make()
                    prepare(u,[s[0] for s in SLOTS].index(slot)+1,model)
                    actual=[audio(u,word(u,table+4*carrier),carrier,params=p) for p in cases]
                    self.assertEqual(actual,expected)
                    self.assertEqual(bytes(u.mem_read(0x2003e000,0x1000)),bytes(0x1000))
                    self.assertEqual(bytes(u.mem_read(0x20200000,0x8000)),bytes(0x8000))

    def test_native_dispatch_preserves_arguments(self):
        for slot,spare,carrier,table,count in SLOTS:
            for model in range(count):
                for marker in [0,1,0x4f,0x60,0xff] + ([0x56] if model!=carrier else []):
                    u=make()
                    original=struct.unpack_from('<I',RAM,table-0x20000000+model*4)[0]
                    u.mem_write(EDIT+spare,bytes([marker]))
                    u.mem_write(EDIT+slot,bytes([model]))
                    call(u,word(u,table+4*model),(11,22,33,44),(PARAM,0),stop=original&~1)
                    for reg,val in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],[11,22,33,44]):
                        self.assertEqual(u.reg_read(reg),val)
                    self.assertEqual(word(u,SP),PARAM)
                    self.assertEqual(word(u,SP+4),0)

    def test_four_instances_do_not_share_state(self):
        u=make()
        # Interleave different algorithms/parameters, comparing with isolated stock engines.
        engines=[]
        for n,model in enumerate([5,6,8,15]):
            s=make(False)
            init_stock(s,model)
            engines.append((s,word(s,0x2000bc48+4*model),model))
            if n:
                prepare(u,n,model)
            else: init_stock(u,model)
        for block in range(12):
            for n,(s,fn,model) in enumerate(engines):
                params=tuple((block*17+n*13+i*19)%100 for i in range(4))
                expected=audio(s,fn,model,params=params)
                if n:
                    _,_,carrier,table,_=SLOTS[n-1]
                    actual=audio(u,word(u,table+4*carrier),carrier,params=params)
                else: actual=audio(u,fn,model,params=params)
                self.assertEqual(actual,expected,(block,n))

    def test_model_change_resets_instance(self):
        u=make()
        slot,spare,carrier,table,_=SLOTS[0]
        u.mem_write(EDIT+slot,bytes([carrier]))
        for model in [6,8,6,15,5]:
            u.mem_write(EDIT+spare,bytes([0x50+model]))
            s=make(False)
            init_stock(s,model)
            expected=audio(s,word(s,0x2000bc48+4*model),model)
            for block in range(200):
                actual=audio(u,word(u,table+4*carrier),carrier)
                if word(u,0x3e024)==8: break
                self.assertEqual(actual,bytes(u.mem_read(IN,32)+u.mem_read(OUT,32)))
            else: self.fail('model never initialized')
            self.assertEqual(actual,expected)

    def test_repeated_same_model_instances(self):
        for model in [0,6]:
            u=make()
            refs=[make(False) for _ in range(4)]
            for s in refs: init_stock(s,model)
            init_stock(u,model)
            for n in range(1,4): prepare(u,n,model)
            for block in range(8):
                for n,s in enumerate(refs):
                    params=tuple((n*23+block*7+i*17)%100 for i in range(4))
                    expected=audio(s,word(s,0x2000bc48+4*model),model,params=params)
                    if n:
                        _,_,carrier,table,_=SLOTS[n-1]
                        actual=audio(u,word(u,table+4*carrier),carrier,params=params)
                    else:
                        actual=audio(u,word(u,0x2000bc48+4*model),model,params=params)
                    self.assertEqual(actual,expected,(model,block,n))

    def test_initialization_has_bounded_writes_and_exact_coefficients(self):
        u=make()
        for model in range(16):
            s=make(False)
            init_stock(s,model)
            meta=0x3e020
            u.mem_write(meta,bytes(32))
            writes=[]
            hook=u.hook_add(UC_HOOK_MEM_WRITE,lambda uc,access,addr,size,value,user:
                           writes.append(size) if 0x3b000<=addr<0x3c000 or 0x81fa0000<=addr<0x81fa8000 else None)
            for block in range(200):
                writes.clear()
                call(u,META['symbols']['initialize_step'],(model,0x3b000,0x81fa0000,meta))
                self.assertLessEqual(sum(writes),512)
                if u.reg_read(UC_ARM_REG_R0): break
            else: self.fail('initialization did not finish')
            u.hook_del(hook)
            self.assertEqual(bytes(u.mem_read(0x3b000,0x1000)),bytes(s.mem_read(0x2003e000,0x1000)))
            self.assertEqual(bytes(u.mem_read(0x81fa0000,0x8000)),bytes(s.mem_read(0x20200000,0x8000)))

    def test_preset_recall_restores_overrides(self):
        u=make()
        rec=bytearray(98)
        rec[3],rec[4],rec[7]=5,2,0
        rec[67:70]=bytes([0x56,0x58,0x5f])
        u.mem_write(0x2002979c+17*128,bytes(rec))
        call(u,0x4f1e,(17,))
        self.assertEqual(bytes(u.mem_read(EDIT,98)),bytes(rec))

    def test_delay_override_clamps_parameters_like_stock_od(self):
        for model in range(16):
            u=make()
            prepare(u,3,model)
            s=make(False)
            init_stock(s,model)
            expected=audio(s,word(s,0x2000bc48+4*model),model,params=(99,99,99,99))
            actual=audio(u,word(u,0x2000bb78),2,params=(100,127,254,255))
            self.assertEqual(actual,expected,model)

    def test_command_validation_and_transport(self):
        u=make()
        replies=[]
        def reply(uc,addr,size,user):
            n=uc.reg_read(UC_ARM_REG_R1)
            replies.append((bytes(uc.mem_read(uc.reg_read(UC_ARM_REG_R0),n)),uc.reg_read(UC_ARM_REG_R2)))
            uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,reply,begin=0xa2ee,end=0xa2ee)
        def send(msg):
            u.mem_write(PARAM,msg)
            call(u,META['symbols']['command'],(PARAM,len(msg),1))
        send(jme.sysex(0x30,0))
        self.assertEqual(replies.pop(),(jme.sysex(0x30,2,b'FXA\x01\0\0\0'),1))
        for slot,spare,_,_,_ in SLOTS:
            for choice in range(17):
                send(jme.sysex(0x30,1,bytes([slot,choice])))
                self.assertEqual(u.mem_read(EDIT+spare,1)[0],choice+0x4f if choice else 0)
                self.assertEqual(replies.pop()[0][6],3)
        before=bytes(u.mem_read(EDIT,98))
        for payload in [b'',b'\x07',b'\x07\x11',b'\x02\x01',b'\x07\x01\x00']:
            send(jme.sysex(0x30,1,payload))
        self.assertFalse(replies)
        self.assertEqual(bytes(u.mem_read(EDIT,98)),before)

    def test_protected_regions_identical(self):
        a=Firmware.parse((ROOT/'firmware/stock/JME-EN_V1.1.1_modified.bin').read_bytes())
        b=Firmware.parse((ROOT/'build/soran-cfw-0.2.0-fx-on-1.1.1.bin').read_bytes())
        self.assertEqual(b.build(),(ROOT/'build/soran-cfw-0.2.0-fx-on-1.1.1.bin').read_bytes())
        region=layout.region('master')
        self.assertEqual(a.image[:region.start],b.image[:region.start])
        self.assertEqual(a.image[region.start+region.size:],b.image[region.start+region.size:])
        self.assertEqual(STOCK[0x3f000:],PATCHED[0x3f000:])

if __name__=='__main__': unittest.main(verbosity=2)
