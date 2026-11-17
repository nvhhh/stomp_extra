"""Eight-output FIR specialization; preserve stock tap order and VMLA rounding."""

def install(emit, scheduled=False, allow_cab=False, ring=512, name='capture_fir8'):
    """ring != 512: variant for exactly `ring` taps on a `ring`-sample history (long cab IRs)."""
    long_ring = ring != 512
    assert not long_ring or (ring in (1024, 2048) and not scheduled)
    source = '''
        ldr r12, [sp, #4]
        cmp r12, #512
        bne fallback
        ldr r12, [sp, #8]
        cmp r12, #512
        bne fallback
        ldr r12, [sp, #12]
        cmp r12, #8
        bne fallback
        push {r4-r11,lr}
        sub sp, #4
        vpush {d8}
        mov r4, r2
        mov r5, r1
        mov r7, r3
        add r8, r7, #2048
        ldr r6, [sp, #48]
        ldr r11, [r6]
        add r9, r7, r11, lsl #2
    '''
    if long_ring:
        source = source.replace('ldr r12, [sp, #4]\n        cmp r12, #512',
                                f'ldr r12, [sp, #4]\n        cmp r12, #{ring}')
        source = source.replace('ldr r12, [sp, #8]\n        cmp r12, #512',
                                f'ldr r12, [sp, #8]\n        cmp r12, #{ring}')
        source = source.replace('add r8, r7, #2048', f'add r8, r7, #{ring * 4}')
    elif scheduled or allow_cab:
        source=source.replace('ldr r12, [sp, #8]\n        cmp r12, #512\n        bne fallback',
            'ldr r12, [sp, #8]\n        cmp r12, #384\n        beq supported\n        cmp r12, #512\n        bne fallback\n    supported:')
    if scheduled:
        source=source.replace('vpush {d8}', 'vpush {d8-d12}').replace('[sp, #48]', '[sp, #80]')
    # Preserve eight old history values before inserting the new eight samples.
    for i in range(8):
        source += f'''
        vldr s{i}, [r9]
        ldr r12, [r0], #4
        str r12, [r9], #4
        cmp r9, r8
        it eq
        moveq r9, r7
        '''
    source += 'movs r12, #0\n'
    for i in range(8,16): source += f'vmov s{i}, r12\n'
    source += (f'ldr r10, [sp, #{88 if scheduled else 56}]\nlsr r10, #3\nloop:\n'
               if scheduled or allow_cab or long_ring else 'mov r10, #64\nloop:\n')
    for k in range(8):
        source += 'vldmia r4!, {s16}\n'
        if scheduled:
            for j in range(8): source += f'vmul.f32 s{17+j}, s{(j+k)%8}, s16\n'
            for j in range(8): source += f'vadd.f32 s{8+j}, s{8+j}, s{17+j}\n'
        else:
            for j in range(8): source += f'vmla.f32 s{8+j}, s{(j+k)%8}, s16\n'
        source += f'''
        vldmia r9!, {{s{k}}}
        cmp r9, r8
        it eq
        moveq r9, r7
        '''
    source += '''
        subs r10, #1
        bne loop
        vstmia r5!, {s8-s15}
        add r11, #8
        ubfx r11, r11, #0, #9
        str r11, [r6]
        vpop {d8}
        add sp, #4
        pop {r4-r11,pc}
    fallback:
        b.w 0x13f84
    '''
    if scheduled: source=source.replace('vpop {d8}', 'vpop {d8-d12}')
    if long_ring:
        source = source.replace('ubfx r11, r11, #0, #9', f'ubfx r11, r11, #0, #{ring.bit_length() - 1}')
    return emit(name, source)
