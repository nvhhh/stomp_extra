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

def build():
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
                cmp r5, #15
                bhi normal
                ldrb r7, [r6, #{slot}]
                and r7, r7, #0x3f
                cmp r7, #{carrier}
                bne normal
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
        cmp r1, #16
        bhi invalid
        cmp r0, #7
        beq eq_slot
        cmp r0, #3
        beq mod_slot
        cmp r0, #4
        bne invalid
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
        movs r6, #3
        b reply
    read:
        cmp r7, #8
        bne invalid
        movs r6, #2
    reply:
        ldr r0, =0x01415846
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
    boot_source = '''push {r0-r4, lr}
        ldr r0, =0x3b000
        ldr r1, =0x3e080
        movs r2, #0
    clear:
        str r2, [r0], #4
        cmp r0, r1
        blo clear
    '''
    for addr, value in installs:
        boot_source += f'ldr r0, ={addr}\nldr r1, ={value}\nstr r1, [r0]\n'
    boot_source += 'pop {r0-r4, lr}\nb.w 0x76fc\n'
    boot = emit('boot', boot_source)
    assert START + len(blob) < 0x3b000, 'code overlaps state'
    assert not any(master[START:0x3e080]), 'CFW space is occupied'
    ops = ['name = "fx-anywhere"', 'description = "Independent OD/FX in EQ, MOD and DEL"',
           f'[[op]]\nkind="blob"\nslot="master"\noffset={START}\nfile="payload.bin"']
    for old, new, literals in [(0x14300,A_TABLE,A_LITS),(0x14304,B_TABLE,B_LITS)]:
        found = [o for o in range(0,len(master)-3,4) if struct.unpack_from('<I',master,o)[0]==old]
        assert found == literals, 'unexpected state-table references'
        for off in literals:
            ops.append(f'[[op]]\nkind="word"\nslot="master"\noffset={off}\nexpect={old}\nvalue={new}')
    assert master[0x3090e:0x30912].hex() == 'd6f7f5fe'
    ops.append(f'[[op]]\nkind="bl"\nslot="master"\noffset=0x3090e\nexpect="d6f7f5fe"\ntarget={boot}')
    dest = Path(__file__).parent
    (dest/'payload.bin').write_bytes(blob)
    (dest/'generated.S').write_text('\n'.join(sources), encoding='utf-8')
    (dest/'patch.toml').write_text('\n\n'.join(ops)+'\n', encoding='utf-8')
    (dest/'symbols.json').write_text(json.dumps({'symbols':symbols,'installs':installs},indent=2)+'\n')
    print(f'FX Anywhere: {len(blob)} bytes code/data; 31 guarded literals; boot {boot:#x}')

if __name__ == '__main__':
    build()
