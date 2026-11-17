"""Validate zero latency, all tail partitions, stereo and capture integration."""
import cmath,json, math, random, struct, unittest
from unittest.mock import patch
import test_chain_fir as c
f=c.f;b=f.b
IMAGE=b.master('build/soran-cfw-0.5.2-deadline-on-1.1.1.bin')
META=json.loads((b.ROOT/'patches/fx-partition-fir/symbols.json').read_text())
STATE=0x81fa0000

def setup(coeff=None):
    u=f.g.t.d.setup(IMAGE,META)
    data=coeff or (b.ROOT/'backups/fx01-crash-coefficients.bin').read_bytes()
    u.mem_write(0x60ede000,(b.ROOT/'backups/fx01-crash-metadata.bin').read_bytes())
    u.mem_write(0x60edf000,data)
    for i in range(200):
        b.call(u,META['symbols']['capture_init_step'],(0,STATE,0x3e020))
        stage=b.word(u,0x3e024)
        if stage: break
    assert stage==1,(i,stage)
    return u

class PartitionTests(unittest.TestCase):
    def test_builtins_after_capture_reuse_tcm_safely(self):
        cases=((51,50,50,50),(0,99,30,70),(99,20,80,10))
        for model in range(16):
            stock=b.make(False);b.init_stock(stock,model)
            expected=[b.audio(stock,b.word(stock,0x2000bc48+4*model),model,params=params) for params in cases]
            for slot,spare,carrier,table,base,a,meta in (
                (7,67,0,0x2000bd40,0x81fa0000,0x3b000,0x3e020),
                (3,68,5,0x2000be7c,0x81fa8000,0x3c000,0x3e040)):
                u=f.g.t.d.setup(IMAGE,META)
                u.mem_write(0x60edf000,(b.ROOT/'backups/fx01-crash-coefficients.bin').read_bytes())
                for _ in range(100):
                    b.call(u,META['symbols']['capture_init_step'],(0,base,meta))
                    if b.word(u,meta+4)==1:break
                self.assertNotEqual(bytes(u.mem_read(a+256,3840)),bytes(3840))
                u.mem_write(b.EDIT+slot,bytes([carrier]));u.mem_write(b.EDIT+spare,bytes([0x50+model]))
                u.mem_write(meta,struct.pack('<II',model+1,0));u.mem_write(meta+16,bytes(4))
                for _ in range(200):
                    b.call(u,META['symbols']['initialize_step'],(model,a,base,meta))
                    if u.reg_read(b.UC_ARM_REG_R0):break
                else:self.fail('native initialization did not complete')
                actual=[b.audio(u,b.word(u,table+4*carrier),carrier,params=params) for params in cases]
                self.assertEqual(actual,expected,(slot,model))

    def test_real_fft_dc_nyquist_and_roundtrip(self):
        u=f.g.t.d.setup(IMAGE,META);rng=random.Random(601)
        cases=[[.125]*64,[.125*(-1)**k for k in range(64)],
               [rng.uniform(-.2,.2) for _ in range(64)]]
        for values in cases:
            u.mem_write(b.IN,struct.pack('<128f',*[v for x in values for v in (x,0.)]))
            b.call(u,META['symbols']['fft'],(b.IN,0))
            got=struct.unpack('<128f',u.mem_read(b.IN,512))
            for k in range(33):
                expected=sum(x*cmath.exp(-2j*math.pi*k*n/64) for n,x in enumerate(values))
                self.assertLess(abs(complex(got[2*k],got[2*k+1])-expected),1e-5)
            b.call(u,META['symbols']['fft'],(b.IN,1))
            got=struct.unpack('<128f',u.mem_read(b.IN,512))
            self.assertLess(max(abs(got[2*k]/64-values[k]) for k in range(64)),2e-7)

    def test_assembly_callee_saved_float_registers(self):
        import unicorn.arm_const as regs
        u=f.g.t.d.setup(IMAGE,META)
        saved=[getattr(regs,f'UC_ARM_REG_D{i}') for i in range(8,16)]
        for name in ('partition_head8','partition_cmac'):
            for addr in (0x20060000,0x20061000,0x20062000):
                u.mem_write(addr,struct.pack('<128f',*([.125]*128)))
            for i,reg in enumerate(saved):u.reg_write(reg,0x1234567800000000+i)
            b.call(u,META['symbols'][name],(0x20060000,0x20061000,0x20062000))
            self.assertEqual([u.reg_read(reg) for reg in saved],[0x1234567800000000+i for i in range(8)])

    def test_whole_callback_guard(self):
        u=f.g.t.d.setup(IMAGE,META)
        u.mem_write(0x3e104,struct.pack('<II',1000,100000))
        u.mem_write(0x3e020,struct.pack('<II',17,1))
        u.mem_write(0x3e040,struct.pack('<II',17,1))
        def finish(elapsed):
            u.mem_write(0xe0001004,struct.pack('<I',1000+elapsed))
            b.call(u,META['symbols']['diagnostic_end'],stop=0xde20)
        finish(101000);self.assertEqual(b.word(u,0x3e024),1)
        finish(90000);self.assertEqual(b.word(u,0x3e11c),0)
        finish(101000);self.assertEqual(b.word(u,0x3e024),1)
        finish(101000)
        for meta in (0x3e020,0x3e040):
            self.assertEqual(b.word(u,meta+4),3)
            self.assertEqual(b.word(u,meta+28),3)
            self.assertEqual(b.word(u,meta+24),101000)
        for meta in (0x3e020,0x3e040):u.mem_write(meta+4,struct.pack('<I',1))
        # ISR catch-up intervals are not the nominal 100,000-cycle deadline.
        u.mem_write(0x3e108,struct.pack('<I',66000))
        for _ in range(3):finish(93347)
        self.assertEqual(b.word(u,0x3e024),1)
        self.assertEqual(b.word(u,0x3e044),1)
        # Conversely, a stretched ISR interval must not mask real overruns.
        u.mem_write(0x3e108,struct.pack('<I',150000))
        finish(101000);finish(101000)
        self.assertEqual(b.word(u,0x3e024),3)
        # An initializing second slot cannot disable an otherwise safe first
        # slot merely because a bounded initialization step was expensive.
        u.mem_write(0x3e024,struct.pack('<I',1));u.mem_write(0x3e044,bytes(4))
        for _ in range(3):finish(101000)
        self.assertEqual(b.word(u,0x3e024),1)
        self.assertEqual(b.word(u,0x3e11c),0)
        # Native OD stages 1..7 are initialization cursors, not capture states.
        u.mem_write(0x3e040,struct.pack('<II',3,1))
        finish(101000);finish(101000)
        self.assertEqual(b.word(u,0x3e024),3)
        self.assertEqual(b.word(u,0x3e044),1)

    def test_channel_guard_uses_fixed_deadline(self):
        u=f.g.t.d.setup(IMAGE,META)
        u.mem_write(0x3e104,struct.pack('<II',1000,66000))
        u.mem_write(0x3e114,struct.pack('<I',1))
        u.mem_write(0x3e020,struct.pack('<II',17,1))
        u.mem_write(0xe0001004,struct.pack('<I',81000))
        b.call(u,META['symbols']['capture_budget_guard'],(0x3e020,1))
        self.assertEqual(u.reg_read(b.UC_ARM_REG_R0),0)
        self.assertEqual(b.word(u,0x3e024),1)
        u.mem_write(0x3e108,struct.pack('<I',150000))
        u.mem_write(0xe0001004,struct.pack('<I',99000))
        b.call(u,META['symbols']['capture_budget_guard'],(0x3e020,1))
        self.assertEqual(u.reg_read(b.UC_ARM_REG_R0),1)
        self.assertEqual(b.word(u,0x3e024),3)

    def test_mono_fast_path_and_initialization_deferral(self):
        old=f.g.t.d.setup(c.IMAGE,c.META);new=f.g.t.d.setup(IMAGE,META)
        for u in (old,new):
            u.mem_write(0x60ede000,(b.ROOT/'backups/fx01-crash-metadata.bin').read_bytes())
            u.mem_write(0x60edf000,(b.ROOT/'backups/fx01-crash-coefficients.bin').read_bytes())
            u.mem_write(b.EDIT+7,b'\0');u.mem_write(b.EDIT+67,b'\x60')
        core_calls=[0];instructions=[0]
        def hook(u,pc,*args):
            instructions[0]+=1
            if pc==META['symbols']['capture_core']:core_calls[0]+=1
        new.hook_add(b.UC_HOOK_CODE,hook);new.ctl_remove_cache(0,0x40000)
        rng=random.Random(716);counts=[]
        for block in range(360):
            data=struct.pack('<8f',*([0.]*8 if block<300 else [rng.uniform(-.2,.2) for _ in range(8)]))
            before_stage=b.word(new,0x3e024);core_calls[0]=0;instructions[0]=0
            outputs=[]
            for u in (old,new):
                u.mem_write(b.IN,data);u.mem_write(b.OUT,data)
                u.mem_write(b.PARAM,bytes([0,0,0,40,70,0,0,0]))
                b.call(u,b.word(u,0x2000bd40),(b.IN,b.OUT,b.LEFT,b.RIGHT),(b.PARAM,0))
                outputs.append(struct.unpack('<16f',u.mem_read(b.LEFT,32)+u.mem_read(b.RIGHT,32)))
            if before_stage==0 and b.word(new,0x3e024)==1:self.assertEqual(core_calls[0],0)
            if block>=300:
                self.assertEqual(outputs[1][:8],outputs[1][8:])
                self.assertLess(max(abs(x-y) for x,y in zip(*outputs)),3e-5)
                counts.append(instructions[0])
        self.assertLess(max(counts),19000)
        print('Mono wrapper instruction range:',min(counts),max(counts))

    def test_split_bank_initialization_and_bounds(self):
        u=f.g.t.d.setup(IMAGE,META)
        u.mem_write(STATE-32,b'\xa5'*32)
        u.mem_write(STATE+32768,b'\x5a'*32)
        u.mem_write(0x3b090,b'\xa5'*112)
        u.mem_write(0x3c000,b'\x5a'*32)
        for slot in range(10):
            amp=struct.pack('<2048f',*([.125]*2048))
            value=.25+slot/128
            fx=struct.pack('<2048f',*([value]*2048))
            u.mem_write(0x60ec1000+slot*0x3000,amp)
            u.mem_write(0x60edf000+slot*0x3000,fx)
            u.mem_write(0x3e020,bytes(32))
            for i in range(100):
                b.call(u,META['symbols']['capture_init_step'],(slot,STATE,0x3e020))
                if b.word(u,0x3e024):break
            self.assertEqual(b.word(u,0x3e024),1)
            self.assertEqual(bytes(u.mem_read(STATE+96,512)),struct.pack('<128f',*([value]*128)))
            self.assertEqual(bytes(u.mem_read(0x3b100,256)),struct.pack('<64f',*([value]*64)))
            self.assertEqual(bytes(u.mem_read(0x3b200,3584)),bytes(u.mem_read(STATE+608,3584)))
            self.assertEqual(bytes(u.mem_read(0x3b090,112)),b'\xa5'*112)
            self.assertEqual(bytes(u.mem_read(0x3c000,32)),b'\x5a'*32)
            self.assertEqual(bytes(u.mem_read(0x60ec1000+slot*0x3000,8192)),amp)
            self.assertEqual(bytes(u.mem_read(STATE-32,32)),b'\xa5'*32)
            self.assertEqual(bytes(u.mem_read(STATE+32768,32)),b'\x5a'*32)
        for index in (0,511,512,1023,1024,1535,1536,2047):
            invalid=bytearray(fx);struct.pack_into('<I',invalid,index*4,0x7fc00001)
            u.mem_write(0x60edf000,bytes(invalid));u.mem_write(0x3e020,bytes(32))
            for _ in range(100):
                b.call(u,META['symbols']['capture_init_step'],(0,STATE,0x3e020))
                if b.word(u,0x3e024):break
            self.assertEqual(b.word(u,0x3e024),2,index)

    def test_deadline_display_protocol_and_native_regressions(self):
        with patch.object(f.g,'IMAGE',IMAGE),patch.object(f.g,'META',META):
            f.g.GuardTests().test_deadline_latches_and_skips_remaining_processing()
        with patch.object(f.g.t,'IMAGE',IMAGE),patch.object(f.g.t,'META',META):
            f.g.t.SolidFillTests().test_all_twenty_capture_pages_and_buffer_selectors()
        with patch.object(c,'IMAGE',IMAGE),patch.object(c,'META',META):
            c.ChainFirTests().test_checkpoint_usb_transport_and_read_only()
            c.ChainFirTests().test_amp_and_cab_parent_output_parity()
            c.ChainFirTests().test_cab_384_taps_and_fp_register_preservation()
        with patch.object(f,'IMAGE',IMAGE),patch.object(f,'META',META):
            f.FastTests().test_fir_exact_history_wrap_and_aliasing()
        import test_split_captures as s
        with patch.object(s,'IMAGE',IMAGE),patch.object(s,'META',META):
            for name in ('test_stock_protocol_accepts_twenty_and_rejects_twenty_one',
                'test_storage_count_and_amp_descriptors','test_empty_fx_never_falls_back_to_amp',
                'test_fx_display_names_and_wheel','test_capability_reply',
                'test_cache_timing_usb_and_three_effect_regressions'):
                getattr(s.SplitTests(),name)()

    def test_fir_impulse_tail_and_random(self):
        rng=random.Random(999)
        coeff=[rng.uniform(-.1,.1) for _ in range(512)]
        data=struct.pack('<2048f',*([0.]*512+coeff+[0.]*1024))
        u=setup(data);ref=f.g.t.d.setup(c.IMAGE,c.META)
        ref.mem_write(0x20060000,bytes(2048));ref.mem_write(0x20062000,bytes(4))
        ref.mem_write(0x20061000,struct.pack('<512f',*coeff))
        max_error=0
        for block in range(180):
            values=([1.]+[0.]*7 if block==0 else [0.]*8) if block<80 else [rng.uniform(-1,1) for _ in range(8)]
            inputs=struct.pack('<8f',*values)
            u.mem_write(b.IN,inputs);ref.mem_write(b.IN,inputs)
            b.call(u,META['symbols']['filter8'],(STATE+7776,0x3b100,0x3b200,b.IN),(b.OUT,))
            b.call(ref,0x13f84,(b.IN,b.OUT,0x20061000,0x20060000),(0x20062000,512,512,8))
            a=struct.unpack('<8f',u.mem_read(b.OUT,32));z=struct.unpack('<8f',ref.mem_read(b.OUT,32))
            err=max(abs(x-y) for x,y in zip(a,z));max_error=max(max_error,err)
            self.assertLess(err,1e-5,(block,a,z))
        print('FIR max error:',max_error)

    def test_actual_capture_independent_stereo(self):
        old=f.g.t.d.setup(c.IMAGE,c.META);new=f.g.t.d.setup(IMAGE,META)
        for u in (old,new):
            u.mem_write(0x60ede000,(b.ROOT/'backups/fx01-crash-metadata.bin').read_bytes())
            u.mem_write(0x60edf000,(b.ROOT/'backups/fx01-crash-coefficients.bin').read_bytes())
            u.mem_write(b.EDIT+7,b'\0');u.mem_write(b.EDIT+67,b'\x60')
        funcs=[b.word(u,0x2000bd40) for u in (old,new)]
        rng=random.Random(519);max_error=0;signal_energy=0;error_energy=0
        for block in range(700):
            params=(35 if block<320 else block%100,70,0,0)
            left=[0.]*8 if block<300 else [rng.uniform(-.1,.1) for _ in range(8)]
            right=[0.]*8 if block<300 else [rng.uniform(-.15,.15) for _ in range(8)]
            outputs=[]
            for u,fn in zip((old,new),funcs):
                u.mem_write(b.IN,struct.pack('<8f',*left));u.mem_write(b.OUT,struct.pack('<8f',*right))
                u.mem_write(b.PARAM,bytes([0,0,0,*params,0]))
                b.call(u,fn,(b.IN,b.OUT,b.LEFT,b.RIGHT),(b.PARAM,0))
                outputs.append(struct.unpack('<16f',u.mem_read(b.LEFT,32)+u.mem_read(b.RIGHT,32)))
            if block>=300:
                for x,y in zip(*outputs):
                    self.assertTrue(math.isfinite(y))
                    max_error=max(max_error,abs(x-y));signal_energy+=x*x;error_energy+=(x-y)**2
                    self.assertLess(abs(x-y),3e-5,(block,x,y))
        snr=10*math.log10(signal_energy/max(error_energy,1e-30))
        print('Full stereo max error / SNR dB:',max_error,snr)
        self.assertGreater(snr,90)

    def test_both_slots_simultaneously_and_switch_reset(self):
        old=f.g.t.d.setup(c.IMAGE,c.META);new=f.g.t.d.setup(IMAGE,META)
        for u in (old,new):
            for idx in (0,9):
                u.mem_write(0x60ede000+idx*0x3000,(b.ROOT/'backups/fx01-crash-metadata.bin').read_bytes())
                u.mem_write(0x60edf000+idx*0x3000,(b.ROOT/'backups/fx01-crash-coefficients.bin').read_bytes())
            u.mem_write(b.EDIT+7,b'\0');u.mem_write(b.EDIT+67,b'\x60')
            u.mem_write(b.EDIT+3,b'\x05');u.mem_write(b.EDIT+68,b'\x69')
        rng=random.Random(720)
        for block in range(700):
            if block==350:
                for u in (old,new):
                    u.mem_write(b.EDIT+67,b'\x69');u.mem_write(b.EDIT+68,b'\x60')
            quiet=block<300 or 350<=block<650
            inputs=[0.]*16 if quiet else [rng.uniform(-.2,.2) for _ in range(16)]
            for table,carrier in ((0x2000bd40,0),(0x2000be7c,5)):
                results=[]
                for u in (old,new):
                    u.mem_write(b.IN,struct.pack('<8f',*inputs[:8]));u.mem_write(b.OUT,struct.pack('<8f',*inputs[8:]))
                    u.mem_write(b.PARAM,bytes([0,0,carrier,40,70,0,0,0]))
                    b.call(u,b.word(u,table+carrier*4),(b.IN,b.OUT,b.LEFT,b.RIGHT),(b.PARAM,0))
                    results.append(struct.unpack('<16f',u.mem_read(b.LEFT,32)+u.mem_read(b.RIGHT,32)))
                if not quiet:
                    self.assertLess(max(abs(x-y) for x,y in zip(*results)),3e-5,(block,carrier))

    def test_balanced_instruction_profile(self):
        u=setup();u.mem_write(b.EDIT+7,b'\0');u.mem_write(b.EDIT+67,b'\x60')
        fn=b.word(u,0x2000bd40)
        for _ in range(300):b.audio(u,fn,0)
        count=[0]
        def hook(*args):count[0]+=1
        u.hook_add(b.UC_HOOK_CODE,hook);u.ctl_remove_cache(0,0x40000)
        counts=[]
        for _ in range(8):
            count[0]=0;b.audio(u,fn,0);counts.append(count[0])
        self.assertLess(max(counts),30000)
        self.assertLess(max(counts)-min(counts),1000)
        result={'instructions_by_phase':counts,'hardware_cycles_unverified':True}
        (b.ROOT/'work/partition-profile.json').write_text(json.dumps(result,indent=2))
        print('Partitioned stereo wrapper instructions:',counts)

if __name__=='__main__':unittest.main(verbosity=2)
