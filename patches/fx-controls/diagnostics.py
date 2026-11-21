"""Read-only audio timing and fault breadcrumbs; no automatic fault recovery.

Storage is in the existing free ITCM area, outside DSP state and code.
Fault records require a debugger if the CPU faults and USB stops responding.
"""
BASE = 0x3e100
FAULT = 0x3e180

GRACE_CALLBACKS = 3000      # ~0.5 s of audio callbacks after a capture starts processing
GRACE_HARD = 115000         # during grace, a callback at or above this still counts as normal
GRACE_STREAK = 16           # during grace, this many consecutive overruns still latch

# Stall profiler (0.6.3-diag). The main loop's spin at 0x7778 bumps a heartbeat; the audio
# callback counts callbacks without a heartbeat change. From PROF_THRESHOLD on, every
# PROF_INTERVAL callbacks it records the interrupted main-loop context (stacked PC, LR,
# EXC_RETURN, longest audio-start gap since the previous sample). The longest stall is kept.
PROF = 0x3e200
PROF_THRESHOLD = 120        # callbacks (~20 ms) without a main-loop spin
PROF_INTERVAL = 24          # callbacks (~4 ms) between samples
PROF_SAMPLES = 96           # per stall record: covers ~0.4 s after the threshold
PROF_CUR = PROF + 128
PROF_BEST = PROF_CUR + PROF_SAMPLES * 16
PROF_END = PROF_BEST + PROF_SAMPLES * 16
PROF_PAGES = (PROF_END - PROF) // 64
# Header words: 0 heartbeat, 1 heartbeat seen, 2 current stall length, 3 current samples,
# 4 longest stall length, 5 its samples, 6 stalls finished (>= threshold), 7 gap max since sample,
# (7 is reset whenever the main loop runs) 8 longest stall's start pass, 9 current stall's start pass, 10 last finished stall length,
# 11 longest audio-start gap since boot. Preset settle (0.6.3): 12 hold callbacks left (0 = off),
# 13 quiet callbacks, 14 redraw seen, 15 recalls, 16 debt, 17 max debt, 18 debt latches,
# 19 settles ended by quiet, 20 settles ended by the hold limit.
SETTLE = PROF + 48
SETTLE_MAX = 3000           # callbacks (0.5 s): longest hold after a preset recall
SETTLE_BUSY = 120           # a main-loop stall this long (20 ms) is the preset redraw
SETTLE_QUIET = 12           # main loop counts as running when it stalled less than this (2 ms)
SETTLE_IDLE = 60            # callbacks (10 ms) of running main loop after the redraw end the hold
DEBT = PROF + 64
DEBT_LIMIT = 400000         # cycles (4 blocks) behind real time: latch processing captures dry
# Frame: SAI1 IRQ 56 -> veneer -> 0xdb88 (pops its frame) -> b.w 0x12278 (48-byte frame,
# EXC_RETURN at frame-4) -> bl diagnostic_begin (push 24). Exception frame = sp + 72.


def profile_sample():
    return f'''
        .cpu cortex-m7
        ldr r4, ={PROF}
        ldr r0, ={BASE}
        ldr r0, [r0, #8]
        ldr r1, [r4, #28]
        cmp r0, r1
        it hi
        strhi r0, [r4, #28]
        ldr r1, [r4, #44]
        cmp r0, r1
        it hi
        strhi r0, [r4, #44]
        ldr r0, [r4]
        ldr r1, [r4, #4]
        cmp r0, r1
        beq prof_stalled
        str r0, [r4, #4]
        ldr r1, [r4, #8]
        cmp r1, #{PROF_THRESHOLD}
        blo prof_reset
        ldr r2, [r4, #24]
        adds r2, #1
        str r2, [r4, #24]
        str r1, [r4, #40]
        ldr r2, [r4, #16]
        cmp r1, r2
        bls prof_reset
        str r1, [r4, #16]
        ldr r2, [r4, #12]
        str r2, [r4, #20]
        ldr r2, [r4, #36]
        str r2, [r4, #32]
        ldr r0, ={PROF_CUR}
        ldr r1, ={PROF_BEST}
        mov r2, #{PROF_SAMPLES * 4}
    prof_copy:
        ldr r3, [r0], #4
        str r3, [r1], #4
        subs r2, #1
        bne prof_copy
    prof_reset:
        movs r1, #0
        str r1, [r4, #8]
        str r1, [r4, #28]
        b prof_done
    prof_stalled:
        ldr r1, [r4, #8]
        adds r1, #1
        str r1, [r4, #8]
        cmp r1, #{PROF_THRESHOLD}
        blo prof_done
        bne prof_due
        movs r2, #0
        str r2, [r4, #12]
        ldr r2, ={BASE}
        ldr r2, [r2]
        str r2, [r4, #36]
    prof_due:
        subs r2, r1, #{PROF_THRESHOLD}
        movs r3, #{PROF_INTERVAL}
        udiv r12, r2, r3
        mls r12, r12, r3, r2
        cmp r12, #0
        bne prof_done
        ldr r2, [r4, #12]
        cmp r2, #{PROF_SAMPLES}
        bhs prof_done
        ldr r0, [sp, #68]
        add r3, sp, #72
        tst r0, #4
        beq prof_msp
        mrs r3, psp
    prof_msp:
        ldr r1, ={PROF_CUR}
        add r1, r1, r2, lsl #4
        ldr r12, [r3, #24]
        str r12, [r1]
        ldr r12, [r3, #20]
        str r12, [r1, #4]
        str r0, [r1, #8]
        ldr r12, [r4, #28]
        str r12, [r1, #12]
        movs r12, #0
        str r12, [r4, #28]
        adds r2, #1
        str r2, [r4, #12]
    prof_done:
    '''


def grace_tick():
    """Per callback, before the overrun test: load each capture's grace counter (meta +8) while
    it initializes (stage 0), count it down while it processes (stage 1), and set the shared
    in-grace flag at BASE+32 when any processing capture is still inside its window."""
    return f'''
        ldr r3, =0x3e020
        movs r2, #0
        str r2, [r4, #32]
        movs r2, #2
    grace_loop:
        ldr r1, [r3]
        cmp r1, #17
        blo grace_next
        ldr r1, [r3, #4]
        cbnz r1, grace_active
        ldr r1, ={GRACE_CALLBACKS}
        str r1, [r3, #8]
        b grace_next
    grace_active:
        cmp r1, #1
        bne grace_next
        ldr r1, [r3, #8]
        cbz r1, grace_next
        subs r1, #1
        str r1, [r3, #8]
        movs r1, #1
        str r1, [r4, #32]
    grace_next:
        add r3, #32
        subs r2, #1
        bne grace_loop
    '''


def install(emit, installs, master, ram, whole_guard=False, grace=False, profiler=False, settle=False, hooks=None):
    command = 0x20010cbc + 0x485 + 0x31*9
    assert ram[command-0x20000000:command-0x20000000+9] == bytes(9)
    assert master[BASE:FAULT+64] == bytes(FAULT+64-BASE)
    assert not settle or (profiler and grace and hooks is not None)
    if profiler:
        assert FAULT + 64 <= PROF and PROF_END <= 0x3f000
        assert master[PROF:PROF_END] == bytes(PROF_END - PROF)
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
        str r0, [r4, #20]{profile_sample().rstrip() if profiler else ''}{settle_tick().rstrip() if settle else ''}
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
    if grace:
        # Start-up grace: a capture's first callbacks after initialization can exceed the
        # 100,000-cycle block briefly (cold state). For GRACE_CALLBACKS after it starts
        # processing, overruns below GRACE_HARD latch only after GRACE_STREAK in a row.
        assert whole_guard
        old_limit = '''
        cmp r1, #2
        blo guard_done
        ldr r3, =0x3e020'''
        assert whole_check.count(old_limit) == 1
        whole_check = (debt_check() if settle else '') + grace_tick() + whole_check.replace(old_limit, f'''
        ldr r2, [r4, #32]
        cbz r2, normal_limit
        ldr r2, ={GRACE_HARD}
        cmp r0, r2
        bhs normal_limit
        cmp r1, #{GRACE_STREAK}
        blo guard_done
        b latch_start
    normal_limit:
        cmp r1, #2
        blo guard_done
    latch_start:
        ldr r3, =0x3e020''')
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
    if profiler:
        boot += profiler_install(emit, installs, ram, ops, master)
    if settle:
        hooks.append(settle_install(emit, master))
    return boot, ops


def profiler_install(emit, installs, ram, ops, master):
    """Main-loop heartbeat at the loop head (0x7778 `bl 0x2750`) and read-only command 0x33:
    request [F0 00 21 7A 70 33 00 page F7], reply 'PRF1' + 16 words (5 x 7 bits) from
    PROF + 64*page. Returns boot code that clears the profiler area."""
    assert master[0x7778:0x777c].hex() == 'faf7eaff'           # bl 0x2750, main-loop spin
    heartbeat = emit('profile_heartbeat', f'''
        push {{r0, r1}}
        ldr r0, ={PROF}
        ldr r1, [r0]
        adds r1, #1
        str r1, [r0]
        pop {{r0, r1}}
        b.w 0x2750
    ''')
    ops.append(f'[[op]]\nkind="bl"\nslot="master"\noffset={0x7778}\nexpect="faf7eaff"\ntarget={heartbeat}')
    command = 0x20010cbc + 0x485 + 0x33*9
    assert ram[command-0x20000000:command-0x20000000+9] == bytes(9)
    read = emit('profile_read', f'''
        mov r12, r2
        cmp r1, #9
        bne invalid
        ldrb r2, [r0, #6]
        cmp r2, #0
        bne invalid
        ldrb r2, [r0, #8]
        cmp r2, #0xf7
        bne invalid
        ldrb r2, [r0, #7]
        cmp r2, #{PROF_PAGES}
        bhs invalid
        push {{r4-r7,lr}}
        sub sp, #92
        str r12, [sp]
        ldr r0, =0x31465250
        str r0, [sp, #4]
        add r4, sp, #8
        ldr r5, ={PROF}
        add r5, r5, r2, lsl #6
        movs r6, #16
    word:
        ldr r0, [r5], #4
        bl pack
        subs r6, #1
        bne word
        movs r0, #0x33
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
    installs.extend([(command, read), (command+4, read)])
    return f'''
        ldr r0, ={PROF}
        ldr r1, ={PROF_END}
        movs r2, #0
    profile_clear:
        str r2, [r0], #4
        cmp r0, r1
        blo profile_clear
    '''


def settle_tick():
    """Per callback (r4 = PROF after profile_sample): count down the preset-settle hold. It ends once
    a main-loop stall of SETTLE_BUSY was seen (the redraw) and the loop then ran for SETTLE_IDLE
    callbacks, or after SETTLE_MAX callbacks."""
    return f'''
        ldr r0, [r4, #48]
        cmp r0, #0
        beq settle_done
        subs r0, #1
        beq settle_limit
        ldr r1, [r4, #8]
        cmp r1, #{SETTLE_BUSY}
        blo settle_not_busy
        movs r2, #1
        str r2, [r4, #56]
    settle_not_busy:
        cmp r1, #{SETTLE_QUIET}
        bhs settle_busy
        ldr r2, [r4, #56]
        cmp r2, #0
        beq settle_store
        ldr r1, [r4, #52]
        adds r1, #1
        str r1, [r4, #52]
        cmp r1, #{SETTLE_IDLE}
        blo settle_store
        movs r0, #0
        ldr r1, [r4, #76]
        adds r1, #1
        str r1, [r4, #76]
        b settle_store
    settle_limit:
        ldr r1, [r4, #80]
        adds r1, #1
        str r1, [r4, #80]
        b settle_store
    settle_busy:
        movs r2, #0
        str r2, [r4, #52]
    settle_store:
        str r0, [r4, #48]
    settle_done:
    '''


def debt_check():
    """End of callback (r0 = elapsed, r4 = BASE): debt = max(0, debt + elapsed - 100000). Above
    DEBT_LIMIT the audio is falling behind however the overruns alternate: latch processing
    captures dry (0.6.0 latch, same checkpoint 3)."""
    return f'''
        ldr r3, ={PROF}
        ldr r1, [r3, #64]
        add r1, r0
        ldr r2, =100000
        subs r1, r1, r2
        it mi
        movmi r1, #0
        str r1, [r3, #64]
        ldr r2, [r3, #68]
        cmp r1, r2
        it hi
        strhi r1, [r3, #68]
        ldr r2, ={DEBT_LIMIT}
        cmp r1, r2
        blo debt_ok
        movs r1, #0
        str r1, [r3, #64]
        ldr r1, [r3, #72]
        adds r1, #1
        str r1, [r3, #72]
        b latch_start
    debt_ok:'''


def settle_install(emit, master):
    """Preset recall 0x4f1e(index) copies preset index into the edit buffer (every load path:
    program change, footswitches, editor, boot). Start the settle hold, then run the stock code."""
    assert master[0x4f1e:0x4f22].hex() == '632806da'          # cmp r0, #99; bge 0x4f30
    target = emit('settle_recall', f'''
        cmp r0, #99
        bge skip
        push {{r0, r1}}
        ldr r0, ={PROF}
        ldr r1, ={SETTLE_MAX}
        str r1, [r0, #48]
        movs r1, #0
        str r1, [r0, #52]
        str r1, [r0, #56]
        ldr r1, [r0, #60]
        adds r1, #1
        str r1, [r0, #60]
        pop {{r0, r1}}
        b.w 0x4f22
    skip:
        bx lr
    ''')
    return (0x4f1e, 4, target)
