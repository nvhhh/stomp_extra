"""Thumb hooks for the on-pedal selector (stock preset encoding is retained)."""

def install(emit):
    selection = emit('selection', '''
        cmp r0, #7
        beq eq_slot
        cmp r0, #3
        bne invalid
        movs r1, #68
        movs r2, #5
        b check
    eq_slot:
        movs r1, #67
        movs r2, #0
    check:
        ldr r3, =0x200101f4
        ldr r3, [r3]
        ldrb r12, [r3, r0]
        and r12, #63
        cmp r12, r2
        bne invalid
        ldrb r0, [r3, r1]
        subs r0, #0x50
        cmp r0, #25
        bls done
    invalid:
        mov r0, #-1
    done:
        bx lr
    ''')
    # 0x4ae0's displaced push + PC-relative load. All other slots use stock code.
    native = emit('wheel_native', '''
        push {r4,r6,r7,lr}
        ldr r6, =0x200101f4
        b.w 0x4ae4
    ''')
    wheel = emit('wheel', f'''
        cmp r0, #7
        beq extended
        cmp r0, #3
        beq extended
        b.w {native & ~1}
    extended:
        push {{r4-r8,lr}}
        sub sp, #8
        mov r4, r0
        ldr r5, =0x200101f4
        ldr r5, [r5]
        cmp r4, #7
        ite eq
        moveq r6, #67
        movne r6, #68
        ite eq
        moveq r7, #2
        movne r7, #13
        ite eq
        moveq r8, #0
        movne r8, #5
        ldrb r0, [r5, r4]
        and r0, #63
        cmp r0, r8
        bne selected
        ldrb r1, [r5, r6]
        subs r1, #0x50
        cmp r1, #25
        it ls
        addls r0, r7, r1
    selected:
        str r0, [sp, #4]
        strb r0, [sp]
        movs r0, #0
        mov r1, sp
        movs r2, #0
        add r3, r7, #25
        bl 0x8e8a
        ldrb r0, [sp]
        ldr r1, [sp, #4]
        cmp r0, r1
        beq done
        cmp r0, r7
        blo normal
        sub r0, r7
        add r1, r0, #0x50
        strb r1, [r5, r6]
        mov r0, r8
        b store
    normal:
        movs r1, #0
        strb r1, [r5, r6]
    store:
        ldrb r1, [r5, r4]
        and r1, #0x40
        orr r0, r1
        strb r0, [r5, r4]
        mov r0, r4
        bl 0x9a28
        ldrb r0, [r5, r6]
        cmp r0, #0x50
        blo done
        cmp r4, #7
        ite eq
        addeq r1, r5, #37
        addne r1, r5, #50
        ldr r2, =0x32323232
        cmp r0, #0x60
        bhs defaults
        sub r0, #0x50
        movs r2, #7
        mul r0, r0, r2
        ldr r2, =0x2907a
        add r2, r0
        movs r3, #4
    copy_defaults:
        ldrb r0, [r2], #1
        strb r0, [r1], #1
        subs r3, #1
        bne copy_defaults
        b done
    defaults:
        movs r0, #50
        strb r0, [r1]
        strb r0, [r1, #1]
        strb r0, [r1, #2]
        strb r0, [r1, #3]
    done:
        add sp, #8
        pop {{r4-r8,pc}}
    ''')
    count = emit('parameter_count', f'''
        push {{r0,lr}}
        bl {selection & ~1}
        cmp r0, #25
        bhi normal
        cmp r0, #16
        bhs capture
        movs r1, #7
        mul r0, r0, r1
        ldr r1, =0x28ca5
        ldrb r0, [r1, r0]
        add sp, #4
        pop {{pc}}
    capture:
        movs r0, #2
        add sp, #4
        pop {{pc}}
    normal:
        pop {{r0,lr}}
        ldr r1, =0x2001683c
        add r2, r0, r0, lsl #1
        b.w 0x4c04
    ''')
    parameter = emit('parameter_edit', f'''
        push {{r0,lr}}
        bl {selection & ~1}
        cmp r0, #25
        bhi normal
        mov r3, r0
        pop {{r0,lr}}
        push {{r4-r6,lr}}
        sub sp, #8
        ldr r1, =0x200101f4
        ldr r2, [r1, #4]
        ldr r5, [r1]
        ldrb r4, [r2, #0x6e]
        and r4, #127
        subs r4, #3
        cmp r4, #1
        blo done
        cmp r4, #4
        bhi done
        cmp r0, #7
        ite eq
        addeq r5, #36
        addne r5, #49
        add r5, r4
        cmp r3, #16
        bhs capture
        movs r1, #7
        mul r3, r3, r1
        ldr r1, =0x28ca5
        add r1, r3
        ldrb r6, [r1, r4]
        b edit
    capture:
        cmp r4, #2
        bhi done
        movs r6, #99
    edit:
        ldrb r0, [r5]
        strb r0, [sp]
        movs r0, #0
        mov r1, sp
        movs r2, #0
        mov r3, r6
        bl 0x8e8a
        ldrb r0, [sp]
        strb r0, [r5]
        ldr r1, =0x2001f764
        strb r4, [r1]
        strb r6, [r1, #1]
        strb r0, [r1, #2]
    done:
        add sp, #8
        pop {{r4-r6,pc}}
    normal:
        pop {{r0,lr}}
        ldr r2, =0x200101f4
        push {{r4-r7,lr}}
        b.w 0x4ce4
    ''')
    return [(0x4ae0,4,wheel),(0x4bfe,6,count),(0x4ce0,4,parameter)], selection
