"""Independent instances of the vendor's converted-capture processing core.

This is not a general NAM neural-network runtime. The vendor converter produces
the coefficient format consumed here. Tone-stack processing belongs to AMP and
is deliberately not included in the capture effect.
"""
from pathlib import Path


def install(emit, master, root, bank_offset=0, fast_fir=False, scheduled=False, allow_cab=False):
    # Stock 0x17bd4..0x17c9e, with PC-relative literals made explicit.
    # The complete stock hash is guarded by the builder; emulation checks parity.
    source = Path(__file__).with_name('capture_core.S').read_text()
    if fast_fir:
        import capture_fir
        fir = capture_fir.install(emit, scheduled, allow_cab)
        source = source.replace('bl       #0x13f84', f'bl {fir & ~1}')
    core = emit('capture_core', source)
    init = emit('capture_init_step', '''
        push {r4-r8,lr}
        mov r4, r1
        mov r5, r2
        mov r6, r0
        ldr r7, [r5, #16]
        mov r8, #128
        ldr r1, =0x60ec1000
        mov r2, #0x3000
        mla r6, r6, r2, r1
    loop:
        cmp r7, #0x6200
        bhs copy
        movs r0, #0
        str r0, [r4, r7]
        b advance
    copy:
        sub r1, r7, #0x6200
        cmp r1, #0x4000
        bhs complete
        cmp r1, #0x2000
        ite lo
        movlo r2, r4
        addhs r2, r4, #0x3100
        bic r1, #0x2000
        ldr r0, [r6, r1]
        ubfx r3, r0, #23, #8
        cmp r3, #255
        beq invalid
        add r2, #0x34
        str r0, [r2, r1]
    advance:
        adds r7, #4
        subs r8, #1
        bne loop
        str r7, [r5, #16]
        movs r0, #0
        pop {r4-r8,pc}
    complete:
        movs r0, #1
        str r0, [r5, #4]
        pop {r4-r8,pc}
    invalid:
        movs r0, #2
        str r0, [r5, #4]
        movs r0, #0
        pop {r4-r8,pc}
    '''.replace('=0x60ec1000', f'={0x60ec1000 + bank_offset * 0x3000}'))
    return core, init


def wrapper(core, init, a, b, meta, bank_offset=0, budget_guard=0, partition_fir=False, pair_prepare=0, settle=0):
    right = b + (0x30 if partition_fir else 0x3100)
    def check(channel):
        return f'''ldr r0, ={meta}
        movs r1, #{channel}
        bl {budget_guard & ~1}
        cmp r0, #0
        bne preparing
        ''' if budget_guard else ''
    # Preset settle (0.6.3): dry, without initializing or processing, while the hold word is set.
    settle_check = f'''
        ldr r0, ={settle}
        ldr r0, [r0]
        cmp r0, #0
        bne preparing''' if settle else ''
    # Enter with the same saved arguments/48-byte frame as the OD wrapper.
    return f'''
    capture:
        sub r0, r5, #16
        mov r1, #0x3000
        ldr r2, ={0x60ec0000 + bank_offset * 0x3000}
        mla r0, r0, r1, r2
        ldrb r0, [r0, #33]
        cmp r0, #1
        bne preparing
        ldr r6, ={meta}
        ldr r7, [r6]
        add r0, r5, #1
        cmp r0, r7
        beq capture_ready
        str r0, [r6]
        movs r0, #0
        str r0, [r6, #4]
        str r0, [r6, #16]
    capture_ready:{settle_check}
        ldr r0, [r6, #4]
        {'cmp r0, #3; beq preparing' if budget_guard else ''}
        cmp r0, #2
        beq preparing
        cmp r0, #0
        bne capture_run
        sub r0, r5, #16
        ldr r1, ={b}
        mov r2, r6
        bl {init & ~1}
        cmp r0, #0
        beq preparing
    capture_run:
        {f'ldr r0, [sp, #8]; ldr r1, [sp, #12]; ldr r2, ={b}; bl {pair_prepare & ~1}' if pair_prepare else ''}
        {check(0)}
        ldr r7, ={a}
        ldr r0, =0x20000000
        ldr r1, [r0]
        ldr r2, [r0, #4]
        str r1, [r7]
        str r2, [r7, #4]
        str r7, [sp]
        ldr r0, [sp, #8]
        ldr r1, [sp, #16]
        ldrb r2, [r4, #3]
        ldr r3, ={b}
        bl {core & ~1}
        {check(1)}
        str r7, [sp]
        ldr r0, [sp, #12]
        ldr r1, [sp, #20]
        ldrb r2, [r4, #3]
        ldr r3, ={right}
        bl {core & ~1}
        {check(2)}
        ldrb r0, [r4, #4]
        cmp r0, #99
        it hi
        movhi r0, #99
        vmov s0, r0
        vcvt.f32.u32 s0, s0
        ldr r0, =0x3ca3d70a
        vmov s1, r0
        vmul.f32 s0, s0, s1
        ldr r2, ={b}
        vstr s0, [r2, #4]
        ldr r2, ={right}
        vstr s0, [r2, #4]
        ldr r0, [sp, #16]
        mov r1, r0
        ldr r2, ={b}
        movs r3, #8
        ldr r12, =0x3f7d70a4
        vmov s0, r12
        bl 0x8674
        ldr r0, [sp, #20]
        mov r1, r0
        ldr r2, ={right}
        movs r3, #8
        ldr r12, =0x3f7d70a4
        vmov s0, r12
        bl 0x8674
        add sp, #28
        pop {{r4-r7,pc}}
    '''
