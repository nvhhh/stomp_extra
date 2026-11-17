"""Read-only audio timing and fault breadcrumbs; no automatic fault recovery.

Storage is in the existing free ITCM area, outside DSP state and code.
Fault records require a debugger if the CPU faults and USB stops responding.
"""
BASE = 0x3e100
FAULT = 0x3e180

def install(emit, installs, master, ram, whole_guard=False):
    command = 0x20010cbc + 0x485 + 0x31*9
    assert ram[command-0x20000000:command-0x20000000+9] == bytes(9)
    assert master[BASE:FAULT+64] == bytes(FAULT+64-BASE)
    begin = emit('diagnostic_begin', f'''
        push {{r0-r4,lr}}
        ldr r4, ={BASE}
        ldr r0, =0xe0001004
        ldr r0, [r0]
        ldr r1, [r4, #4]
        ldr r2, [r4]
        cbz r2, first
        subs r1, r0, r1
        str r1, [r4, #8]
    first:
        str r0, [r4, #4]
        adds r2, #1
        str r2, [r4]
        ldr r0, [r4, #20]
        cbz r0, not_busy
        ldr r1, [r4, #24]
        adds r1, #1
        str r1, [r4, #24]
    not_busy:
        movs r0, #1
        str r0, [r4, #20]
        pop {{r0-r4,lr}}
        b.w 0xde12
    ''')
    # V1.1.1's measured nominal audio interval is 100,000 DWT cycles. Actual
    # ISR entry deltas include short catch-up gaps and stretched overruns;
    # neither is a valid substitute for the processing deadline.
    whole_check = '''
        ldr r1, =100000
        cmp r0, r1
        blo reset_overruns
        ldr r3, =0x3e020
        movs r2, #2
    check_preparing:
        ldr r1, [r3]
        cmp r1, #17
        blo next_preparing
        ldr r1, [r3, #4]
        cmp r1, #0
        beq reset_overruns
    next_preparing:
        add r3, #32
        subs r2, #1
        bne check_preparing
        ldr r1, [r4, #28]
        adds r1, #1
        str r1, [r4, #28]
        cmp r1, #2
        blo guard_done
        ldr r3, =0x3e020
        movs r2, #2
    latch_capture:
        ldr r1, [r3]
        cmp r1, #17
        blo next_capture
        ldr r1, [r3, #4]
        cmp r1, #1
        bne next_capture
        movs r1, #3
        str r1, [r3, #4]
        str r1, [r3, #28]
        str r0, [r3, #24]
    next_capture:
        add r3, #32
        subs r2, #1
        bne latch_capture
        b guard_done
    reset_overruns:
        movs r1, #0
        str r1, [r4, #28]
    guard_done:
    ''' if whole_guard else ''
    end = emit('diagnostic_end', f'''
        push {{r0-r4,lr}}
        ldr r4, ={BASE}
        ldr r0, =0xe0001004
        ldr r0, [r0]
        ldr r1, [r4, #4]
        subs r0, r0, r1
        str r0, [r4, #12]
        ldr r1, [r4, #16]
        cmp r0, r1
        it hi
        strhi r0, [r4, #16]
        {whole_check}
        movs r0, #0
        str r0, [r4, #20]
        pop {{r0-r4,lr}}
        b.w 0xde20
    ''')
    fault = emit('diagnostic_fault', f'''
        .cpu cortex-m7
        ldr r0, ={FAULT}
        mov r1, lr
        str r1, [r0, #4]
        mrs r2, ipsr
        str r2, [r0, #8]
        mrs r2, msp
        str r2, [r0, #12]
        mrs r3, psp
        str r3, [r0, #16]
        ldr r1, =0xe000ed28
        ldr r2, [r1]
        str r2, [r0, #20]
        ldr r2, [r1, #4]
        str r2, [r0, #24]
        ldr r2, [r1, #12]
        str r2, [r0, #28]
        ldr r2, [r1, #16]
        str r2, [r0, #32]
        ldr r2, =0x314c5446
        str r2, [r0]
        dsb
    halted:
        b halted
    ''')
    # No stack dereference in the fault handler: stacking itself may have failed.
    # A debugger can inspect MSP/PSP and EXC_RETURN to decode the exception frame.
    handler = emit('diagnostic_read', f'''
        mov r12, r2
        cmp r1, #8
        bne invalid
        ldrb r2, [r0, #6]
        cmp r2, #0
        bne invalid
        ldrb r2, [r0, #7]
        cmp r2, #0xf7
        bne invalid
        push {{r4-r7,lr}}
        sub sp, #92
        str r12, [sp]
        ldr r0, =0x31544744
        str r0, [sp, #4]
        add r4, sp, #8
        ldr r5, ={BASE}
        movs r6, #7
    metric:
        ldr r0, [r5], #4
        bl pack
        subs r6, #1
        bne metric
        ldr r5, =0x3e020
        movs r6, #3
    state:
        ldr r0, [r5]
        bl pack
        ldr r0, [r5, #4]
        bl pack
        add r5, #32
        subs r6, #1
        bne state
        ldr r0, =0x2001f894
        ldr r0, [r0]
        bl pack
        ldr r0, =0xe0001000
        ldr r0, [r0]
        bl pack
        ldr r0, ={BASE}
        ldr r0, [r0]
        bl pack
        movs r0, #0x31
        movs r1, #2
        add r2, sp, #4
        movs r3, #84
        bl 0x5248
        add sp, #92
        pop {{r4-r7,pc}}
    invalid:
        bx lr
    pack:
        movs r7, #5
    digit:
        and r1, r0, #127
        strb r1, [r4], #1
        lsrs r0, #7
        subs r7, #1
        bne digit
        bx lr
    ''')
    installs.extend([(command, handler), (command+4, handler)])
    ops = []
    for address, target in [(0x1228c, begin), (0x125ea, end)]:
        ops.append(f'[[op]]\nkind="bl"\nslot="master"\noffset={address}\nexpect="{master[address:address+4].hex()}"\ntarget={target}')
    for address in (12,16,20,24):
        old = int.from_bytes(master[address:address+4], 'little')
        ops.append(f'[[op]]\nkind="word"\nslot="master"\noffset={address}\nexpect={old}\nvalue={fault}')
    boot = f'''
        ldr r0, ={BASE}
        ldr r1, ={FAULT+64}
        movs r2, #0
    diagnostic_clear:
        str r2, [r0], #4
        cmp r0, r1
        blo diagnostic_clear
        ldr r0, =0xe000edfc
        ldr r1, [r0]
        orr r1, r1, #0x1000000
        str r1, [r0]
        ldr r0, =0xe0001000
        ldr r1, [r0]
        orr r1, r1, #1
        str r1, [r0]
        dsb
        isb
    '''
    return boot, ops
