"""Build the guarded V1.1.1 FX Anywhere patch. Run from any directory."""
from pathlib import Path
import hashlib
import json
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
from nuxfw.container import Firmware
from nuxfw import layout
from tools.emu_init import initialize
import controls
import capture
import display

BASE_SHA = 'fda9d54bd168554bf69b2a7b5a02830dc69b0ac4993e7daababc5d7dfbdcd31a'
START = 0x38100
A_TABLE, B_TABLE = START, START + 16
EDIT = 0x200102A0
CMD_TABLE = 0x20010CBC + 0x485 + 0x30 * 9
# slot, spare record byte, carrier model, model table, number of native models
SLOTS = [(7, 67, 0, 0x2000BD40, 2), (3, 68, 5, 0x2000BE7C, 13),
         (4, 69, 2, 0x2000BB70, 7)]
A_LITS = [0x239d0,0x245f0,0x26c54,0x27108,0x2b56c,0x2bfbc,0x2c1ac,0x2c954,
          0x2cedc,0x2d240,0x2d3e0,0x2d714,0x2dd68,0x2e07c,0x2e204,0x2ecb4]
B_LITS = [0x239d4,0x245f4,0x26c58,0x2710c,0x2b574,0x2bfc0,0x2c1b4,0x2c964,
          0x2cee0,0x2d244,0x2d3e4,0x2d724,0x2dd70,0x2e08c,0x2e214]

CAB_OBJECT = 0x20004998        # stock CAB processor state (coefficients +0x128..+0x2128)


def build(diagnostics=False, cache_state=False, split_bank=False, display_fix=False, solid_fill=False, capture_guard=False, fast_fir=False, chain_fir=False, partition_fir=False, long_ir=False, guard_grace=False, stall_profiler=False, preset_settle=False):
    assert not guard_grace or (partition_fir and capture_guard)
    assert not stall_profiler or guard_grace
    assert not preset_settle or stall_profiler
    assert not long_ir or (chain_fir and cache_state)
    assert not partition_fir or chain_fir
    assert not chain_fir or fast_fir
    assert not fast_fir or capture_guard
    assert not capture_guard or (diagnostics and solid_fill)
    assert not solid_fill or display_fix
    assert not display_fix or split_bank
    assert not split_bank or (diagnostics and cache_state)
    raw = (ROOT / 'firmware/stock/JME-EN_V1.1.1_modified.bin').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == BASE_SHA, 'wrong stock firmware'
    image = Firmware.parse(raw).image
    master = image[layout.region('master').start:layout.region('master').start + 0x40000]
    ram = bytes(initialize(master).mem_read(0x20000000, 0x40000))
    # Validate every stock initialization descriptor before reusing it for extra instances.
    for model in range(16):
        for part in range(7):
            off, src, size = struct.unpack_from('<III', master, 0x24b90 + model*84 + part*12)
            if size == 0:
                break
            assert not (off % 4 or src % 4 or size % 4), 'unaligned DSP initialization'
            assert off + size <= (0x1000 if part == 0 else 0x8000), 'DSP state too large'
            assert (0x20000000 <= src and src+size <= 0x20040000 or
                    layout.FLASH_BASE <= src and src+size <= layout.FLASH_BASE+len(image)), 'unknown coefficient source'
    ks = Ks(KS_ARCH_ARM, KS_MODE_THUMB)
    blob = bytearray(struct.pack('<8I', 0x2003e000,0x3b000,0x3c000,0x3d000,
                                0x20200000,0x81fa0000,0x81fa8000,0x81fb0000))
    symbols, sources, installs = {}, [], []
    def emit(name, source):
        while len(blob) % 4: blob.append(0)
        addr = START + len(blob)
        code, _ = ks.asm(source, addr)
        assert code, name
        blob.extend(code)
        symbols[name] = addr
        sources.append(f'/* {name} @ {addr:#x} */\n{source}\n')
        return addr | 1
    initializer = emit('initialize_step', '''
        push {r4-r11, lr}
        mov r5, r1
        mov r6, r2
        mov r7, r3
        movs r1, #84
        mul r0, r0, r1
        ldr r4, =0x24b90
        add r4, r0
        ldr r8, [r7, #4]
        ldr r9, [r7, #16]
        mov r10, #128
    next:
        cmp r8, #8
        bhs complete
        cmp r8, #0
        bne descriptor
        mov r11, #0x8000
        mov r0, r6
        movs r2, #0
        b copy
    descriptor:
        sub r0, r8, #1
        movs r1, #12
        mla r0, r0, r1, r4
        ldr r11, [r0, #8]
        cmp r11, #0
        beq complete
        ldr r12, [r0, #4]
        ldr r0, [r0]
        cmp r8, #1
        ite eq
        addeq r0, r5
        addne r0, r6
    copy:
        cmp r9, r11
        bhs advance
        cmp r8, #0
        it ne
        ldrne r2, [r12, r9]
        str r2, [r0, r9]
        add r9, #4
        subs r10, #1
        bne copy
        str r8, [r7, #4]
        str r9, [r7, #16]
        movs r0, #0
        pop {r4-r11, pc}
    advance:
        add r8, #1
        mov r9, #0
        b next
    complete:
        movs r0, #8
        str r0, [r7, #4]
        movs r0, #1
        pop {r4-r11, pc}
    ''')
    hooks, selection = controls.install(emit)
    hooks += display.install(emit, selection, split_bank, display_fix, solid_fill)
    capture_core, capture_init = capture.install(emit, master, ROOT, 10 if split_bank else 0,
        fast_fir, chain_fir and not partition_fir, chain_fir)
    partition_ops = []
    if partition_fir:
        import partition_build
        partition_blob, partition_symbols = partition_build.build(
            ROOT, 'cab_partitioned.c' if long_ir else 'capture_partitioned.c')
        assert not any(master[0x36d10:0x36d10+len(partition_blob)]), 'partition code space occupied'
        capture_core = partition_symbols['partition_core'] | 1
        capture_init = partition_symbols['partition_init'] | 1
        symbols.update(partition_symbols)
        symbols['capture_core'] = capture_core & ~1
        symbols['capture_init_step'] = capture_init & ~1
        partition_ops.append('[[op]]\nkind="blob"\nslot="master"\noffset=0x36d10\nfile="partition.bin"')
    budget_guard = 0
    import diagnostics as diag
    # --guard-grace: during a capture's start-up grace (meta +8, counted by the whole-callback
    # guard), the per-channel check only latches at or above diag.GRACE_HARD.
    grace_check = f'''
            ldr r2, [r0, #8]
            cbz r2, latch
            ldr r2, ={diag.GRACE_HARD}
            cmp r3, r2
            blo safe
        latch:''' if guard_grace else ''
    if capture_guard:
        # Partitioned builds use the fixed stock-clock deadline, not the last
        # (potentially shortened or stretched) interval between ISR entries.
        budget_guard = emit('capture_budget_guard', f'''
            ldr r2, =0x3e100
            ldr r3, [r2, #20]
            cmp r3, #1
            bne safe
            ldr r3, =0xe0001004
            ldr r3, [r3]
            ldr r12, [r2, #4]
            sub r3, r3, r12
            cmp r1, #0
            ite eq
            streq r3, [r0, #20]
            strne r3, [r0, #24]
            {'ldr r2, =100000' if partition_fir else 'ldr r2, [r2, #8]'}
            movw r12, #10000
            cmp r2, r12
            blo safe
            movw r12, #5000
            sub r2, r2, r12
            cmp r3, r2
            blo safe{grace_check}
            str r1, [r0, #28]
            movs r2, #3
            str r2, [r0, #4]
            movs r0, #1
            bx lr
        safe:
            movs r0, #0
            bx lr
        ''')
    for instance, (slot, spare, carrier, table, count) in enumerate(SLOTS, 1):
        a = 0x3a000 + instance * 0x1000
        b = 0x81f98000 + instance * 0x8000
        # Metadata is outside the stock algorithms' 4 KiB state allocation.
        meta = 0x3e000 + instance * 32
        for model in range(count):
            original = struct.unpack_from('<I', ram, table - 0x20000000 + 4*model)[0]
            guard = 'b normal' if model != carrier else f'''
                ldr r6, ={EDIT}
                ldrb r5, [r6, #{spare}]
                subs r5, #0x50
                cmp r5, #{25 if slot in (7,3) else 15}
                bhi normal
                ldrb r7, [r6, #{slot}]
                and r7, r7, #0x3f
                cmp r7, #{carrier}
                bne normal
                cmp r5, #16
                bhs capture
            '''
            fn = emit(f'slot{slot}_model{model}', f'''
                push {{r4-r7, lr}}
                sub sp, #28
                str r0, [sp, #8]
                str r1, [sp, #12]
                str r2, [sp, #16]
                str r3, [sp, #20]
                ldr r4, [sp, #48]
                {guard}
                ldr r6, ={meta}
                ldr r7, [r6]
                adds r5, #1
                cmp r5, r7
                beq ready
                str r5, [r6]
                movs r0, #0
                str r0, [r6, #4]
                str r0, [r6, #16]
            ready:
                subs r5, #1
                mov r0, r5
                ldr r1, ={a}
                ldr r2, ={b}
                mov r3, r6
                bl {initializer & ~1}
                cmp r0, #0
                beq preparing
                ldr r0, [r4]
                ldr r1, [r4, #4]
                str r0, [r6, #8]
                str r1, [r6, #12]
                strb r5, [r6, #10]
                add r0, r6, #11
                movs r1, #4
            clamp:
                ldrb r2, [r0]
                cmp r2, #99
                it hi
                movhi r2, #99
                strb r2, [r0], #1
                subs r1, #1
                bne clamp
                add r4, r6, #8
                str r4, [sp]
                movs r0, #{instance}
                str r0, [sp, #4]
                ldr r7, =0x2000bc48
                ldr r7, [r7, r5, lsl #2]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                blx r7
                add sp, #28
                pop {{r4-r7, pc}}
            preparing:
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                movs r4, #8
            dry:
                ldr r5, [r0], #4
                str r5, [r2], #4
                ldr r5, [r1], #4
                str r5, [r3], #4
                subs r4, #1
                bne dry
                add sp, #28
                pop {{r4-r7, pc}}
            normal:
                ldr r6, ={meta}
                movs r5, #0
                str r5, [r6]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                add sp, #28
                pop {{r4-r7, lr}}
                ldr r12, ={original}
                bx r12
                {capture.wrapper(capture_core, capture_init, a, b, meta, 10 if split_bank else 0, budget_guard, partition_fir, symbols.get('partition_pair_prepare',0), diag.SETTLE if preset_settle else 0) if model == carrier else ''}
            ''')
            installs.append((table + 4*model, fn))
    # ABI: r0=complete SysEx, r1=length, r2=reply transport. No persistent writes.
    handler = emit('command', f'''
        push {{r4-r7, lr}}
        sub sp, #20
        str r2, [sp]
        mov r4, r0
        mov r7, r1
        ldr r5, ={EDIT}
        ldrb r6, [r4, #6]
        cmp r6, #0
        beq read
        cmp r6, #1
        bne invalid
        cmp r7, #10
        bne invalid
        ldrb r0, [r4, #9]
        cmp r0, #0xf7
        bne invalid
        ldrb r0, [r4, #7]
        ldrb r1, [r4, #8]
        cmp r1, #26
        bhi invalid
        cmp r0, #7
        beq eq_slot
        cmp r0, #3
        beq mod_slot
        cmp r0, #4
        bne invalid
        cmp r1, #16
        bhi invalid
        movs r2, #69
        b write
    eq_slot:
        movs r2, #67
        b write
    mod_slot:
        movs r2, #68
    write:
        cmp r1, #0
        beq store
        adds r1, #0x4f
    store:
        strb r1, [r5, r2]
        cmp r0, #7
        beq reset_eq
        cmp r0, #3
        bne stored
        ldr r0, =0x3e040
        b reset
    reset_eq:
        ldr r0, =0x3e020
    reset:
        movs r1, #0
        str r1, [r0]
    stored:
        movs r6, #3
        b reply
    read:
        cmp r7, #8
        bne invalid
        movs r6, #2
    reply:
        ldr r0, ={0x03415846 if split_bank else 0x02415846}
        str r0, [sp, #8]
        ldrb r0, [r5, #67]
        strb r0, [sp, #12]
        ldrb r0, [r5, #68]
        strb r0, [sp, #13]
        ldrb r0, [r5, #69]
        strb r0, [sp, #14]
        movs r0, #0x30
        mov r1, r6
        add r2, sp, #8
        movs r3, #7
        bl 0x5248
    invalid:
        add sp, #20
        pop {{r4-r7, pc}}
    ''')
    installs.extend([(CMD_TABLE, handler), (CMD_TABLE+4, handler)])
    diagnostic_boot = ''
    extra_ops = []
    if diagnostics:
        diagnostic_boot, extra_ops = diag.install(emit, installs, master, ram, whole_guard=partition_fir, grace=guard_grace, profiler=stall_profiler, settle=preset_settle, hooks=hooks)
    if chain_fir:
        cab_target = symbols["capture_fir8"] | 1
        if long_ir:
            # The CAB object holds all 2048 uploaded IR floats (reversed) at +0x128..+0x2128;
            # stock plays the last 384 (+0x1b28). For user IR slots (active index 240..249) the
            # FIR calls go to cab_process (cab_partitioned.c): 1024 taps, partitioned FFT,
            # spectra prepared in the main loop by cab_load. It returns 0 when it does not
            # handle the call (built-in cab, or spectra not ready) -> unchanged 0.5.2 kernel.
            assert partition_fir, '--long-ir needs the partition kernel build'
            loader_call, _ = ks.asm('bl 0x14fac', 0x15020)
            assert master[0x15020:0x15024] == bytes(loader_call)   # only caller of the IR loader
            cab_target = emit('cab_long_fir', f'''
                push {{r0-r3, r4, lr}}
                ldr r2, ={CAB_OBJECT}
                ldrh r2, [r2, #2]
                bl {symbols["cab_process"]}
                cmp r0, #0
                pop {{r0-r3, r4, lr}}
                bne handled
                b.w {symbols["capture_fir8"]}
            handled:
                bx lr
            ''')
            load_hook = emit('cab_load_hook', f'''
                push {{r4, lr}}
                mov r4, r0
                bl 0x14fac
                mov r0, r4
                bl {symbols["cab_load"]}
                pop {{r4, pc}}
            ''')
            extra_ops.append(f'[[op]]\nkind="bl"\nslot="master"\noffset={0x15020}\nexpect="{bytes(loader_call).hex()}"\ntarget={load_hook}')
        for address in (0x14d22,0x14e5e,0x17c3a,0x17c84):
            expected,_=ks.asm('bl 0x13f84',address)
            assert master[address:address+4]==bytes(expected)
            target = cab_target if address in (0x14d22, 0x14e5e) else symbols["capture_fir8"] | 1
            extra_ops.append(f'[[op]]\nkind="bl"\nslot="master"\noffset={address}\nexpect="{bytes(expected).hex()}"\ntarget={target}')
        import capture_metrics
        capture_metrics.install(emit,installs,ram)
    if cache_state:
        # Install the extra region while the stock startup has MPU and caches
        # disabled, before its existing barriers / full cache invalidation.
        # Region 10: 128 KiB at 0x81fa0000, cacheable. SRD 0xc0 disables subregions 6-7 (the
        # last 32 KiB); long_ir enables both (0x81fb8000..0x81fbffff) for the cab FFT state.
        rasr = 0x13030021 if long_ir else 0x1303c021
        cached = emit('cache_extra_state', f'''
            push {{r0-r3}}
            ldr r0, =0xe000ed90
            ldr r1, [r0]
            ubfx r1, r1, #8, #8
            cmp r1, #11
            blo unchanged
            ldr r1, =0x81fa001a
            str r1, [r0, #12]
            ldr r1, ={rasr:#x}
            str r1, [r0, #16]
        unchanged:
            pop {{r0-r3}}
            dsb
            b.w 0xc3da
        ''')
        assert master[0xc3d6:0xc3da].hex() == 'bff34f8f'
        hooks.append((0xc3d6,4,cached))
    boot_source = '''push {r0-r4, lr}
        ldr r0, =0x3b000
        ldr r1, =0x3e080
        movs r2, #0
    clear:
        str r2, [r0], #4
        cmp r0, r1
        blo clear
    '''
    boot_source += diagnostic_boot
    if split_bank:
        # Expand only the storage protocol. AMP's ten descriptors and wheel
        # limits are deliberately unchanged; FX uses physical slots 10..19.
        assert ram[0x10ba5] == 10
        boot_source += 'ldr r0, =0x20010ba5\nmovs r1, #20\nstrb r1, [r0]\n'
    for addr, value in installs:
        boot_source += f'ldr r0, ={addr}\nldr r1, ={value}\nstr r1, [r0]\n'
    boot_source += 'pop {r0-r4, lr}\nb.w 0x76fc\n'
    boot = emit('boot', boot_source)
    assert START + len(blob) < 0x3b000, 'code overlaps state'
    assert not any(master[START:0x3e080]), 'CFW space is occupied'
    ops = ['name = "fx-controls"', 'description = "Experimental wheel and capture extensions"',
           f'[[op]]\nkind="blob"\nslot="master"\noffset={START}\nfile="payload.bin"']
    for address, size, target in hooks:
        branch, _ = ks.asm(f'b.w {target & ~1}' + ('\nnop' if size==6 else ''), address)
        assert len(branch) == size
        ops.append(f'[[op]]\nkind="bytes"\nslot="master"\noffset={address}\nexpect="{master[address:address+size].hex()}"\ndata="{bytes(branch).hex()}"')
    for old, new, literals in [(0x14300,A_TABLE,A_LITS),(0x14304,B_TABLE,B_LITS)]:
        found = [o for o in range(0,len(master)-3,4) if struct.unpack_from('<I',master,o)[0]==old]
        assert found == literals, 'unexpected state-table references'
        for off in literals:
            ops.append(f'[[op]]\nkind="word"\nslot="master"\noffset={off}\nexpect={old}\nvalue={new}')
    ops.extend(extra_ops)
    ops.extend(partition_ops)
    assert master[0x3090e:0x30912].hex() == 'd6f7f5fe'
    ops.append(f'[[op]]\nkind="bl"\nslot="master"\noffset=0x3090e\nexpect="d6f7f5fe"\ntarget={boot}')
    dest = (Path(__file__).parent.parent / 'fx-settle' if preset_settle else
            Path(__file__).parent.parent / 'fx-stall-diag' if stall_profiler else
            Path(__file__).parent.parent / 'fx-guard-grace' if guard_grace else
            Path(__file__).parent.parent / 'fx-long-ir' if long_ir else
            Path(__file__).parent.parent / 'fx-partition-fir' if partition_fir else
            Path(__file__).parent.parent / 'fx-chain-fir' if chain_fir else
            Path(__file__).parent.parent / 'fx-capture-fast' if fast_fir else
            Path(__file__).parent.parent / 'fx-capture-guard' if capture_guard else
            Path(__file__).parent.parent / 'fx-split-solid-fill' if solid_fill else
            Path(__file__).parent.parent / 'fx-split-display-fix' if display_fix else
            Path(__file__).parent.parent / 'fx-split-captures' if split_bank else
            Path(__file__).parent.parent / 'fx-cache-diagnostics' if cache_state else
            Path(__file__).parent if not diagnostics else Path(__file__).parent.parent / 'fx-diagnostics')
    dest.mkdir(exist_ok=True)
    if partition_fir:
        (dest/'partition.bin').write_bytes(partition_blob)
    (dest/'payload.bin').write_bytes(blob)
    (dest/'generated.S').write_text('\n'.join(sources), encoding='utf-8')
    (dest/'patch.toml').write_text('\n\n'.join(ops)+'\n', encoding='utf-8')
    (dest/'symbols.json').write_text(json.dumps({'symbols':symbols,'installs':installs},indent=2)+'\n')
    print(f'FX Anywhere: {len(blob)} bytes code/data; 31 guarded literals; boot {boot:#x}')

if __name__ == '__main__':
    build(diagnostics='--diagnostic' in sys.argv, cache_state='--cache-state' in sys.argv,
          split_bank='--split-bank' in sys.argv, display_fix='--display-fix' in sys.argv,
          solid_fill='--solid-fill' in sys.argv, capture_guard='--capture-guard' in sys.argv,
          fast_fir='--fast-fir' in sys.argv, chain_fir='--chain-fir' in sys.argv,
          partition_fir='--partition-fir' in sys.argv, long_ir='--long-ir' in sys.argv,
          guard_grace='--guard-grace' in sys.argv, stall_profiler='--stall-profiler' in sys.argv,
          preset_settle='--preset-settle' in sys.argv)
