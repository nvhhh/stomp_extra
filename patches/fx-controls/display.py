"""Use existing model artwork and native text rendering for extended selections."""


def install(emit, selection, split_bank=False, display_fix=False, solid_fill=False):
    names = emit('fx_bank_names', '.byte ' + ','.join(str(b) for i in range(1,11)
                 for b in f'FX {i:02d}'.encode().ljust(32,b'\0'))) & ~1 if split_bank else None
    layout = emit('capture_parameter_layout', '.short 15,104,0,170,104,0') & ~1
    clean_background = '''
        movs r1, #5
        strh r1, [r6, #4]
        movs r1, #0
        strh r1, [r6, #8]
        strh r1, [r6, #10]
        sub r1, r5, #16
        addw r1, r1, #0x396
        strh r1, [r6, #0xc6]
    ''' if display_fix else ''
    if solid_fill:
        # Type 3 is RGB565 rectangle fill. Type 5 copies a raw bitmap pointer.
        # Renderer passes +8 as height and +10 as width to the rotated buffer.
        clean_background = '''
            movs r1, #3
            strh r1, [r6, #4]
            movs r1, #240
            strh r1, [r6, #8]
            movw r1, #320
            strh r1, [r6, #10]
            sub r1, r5, #16
            addw r1, r1, #0x396
            strh r1, [r6, #0xc6]
        '''
    route = emit('display_route', f'''
        push {{r0-r3,r12,lr}}
        mov r0, r8
        bl {selection & ~1}
        cmp r0, #25
        bhi normal
        mov r5, r0
        pop {{r0-r3,r12,lr}}
        cmp r8, #7
        ite eq
        addeq r9, lr, #37
        addne r9, lr, #50
        add r1, r5, #0x398
        strh r1, [r6, #0xc6]
        cmp r5, #16
        bhs capture
        ldr r1, =0x20012c34
        add r1, r1, r5, lsl #3
        cmp r0, #0
        ite ne
        ldrhne r3, [r1, #2]
        ldrheq r3, [r1]
        movs r1, #78
        mul r1, r5, r1
        ldr r10, =0x2001310e
        add r10, r1
        movs r1, #7
        mul r1, r5, r1
        ldr r0, =0x28ca5
        ldrb r1, [r0, r1]
        b.w 0x1f840
    capture:
        {clean_background}
        mov r3, #{0 if solid_fill else 0xffff}
        ldr r10, ={layout}
        movs r1, #2
        b.w 0x1f840
    normal:
        pop {{r0-r3,r12,lr}}
        cmp r8, #7
        b.w 0x1f6bc
    ''')
    labels = emit('capture_labels', '''
        push {r4,lr}
        sub sp, #48
        mov r4, sp
        movs r0, #0
        movs r1, #12
    clear:
        str r0, [r4], #4
        subs r1, #1
        bne clear
        mov r4, sp
        movs r0, #15
        strh r0, [r4]
        movs r0, #80
        strh r0, [r4, #2]
        mov r0, #300
        strh r0, [r4, #4]
        movs r0, #95
        strh r0, [r4, #8]
        movs r0, #2
        strh r0, [r4, #10]
        movs r0, #5
        strh r0, [r4, #12]
        movs r0, #100
        strh r0, [r4, #14]
        ldr r0, =0x4e494147
        str r0, [r4, #16]
        mov r0, r4
        movs r1, #50
        bl 0x1f138
        movs r0, #170
        strh r0, [r4]
        ldr r0, =0x4556454c
        str r0, [r4, #16]
        movs r0, #76
        str r0, [r4, #20]
        mov r0, r4
        movs r1, #56
        bl 0x1f138
        add sp, #48
        pop {r4,pc}
    ''')
    name = emit('display_capture_name', f'''
        push {{r0-r3,r12,lr}}
        ldrb r0, [r11, #10]
        bl {selection & ~1}
        cmp r0, #16
        blo normal
        cmp r0, #25
        bhi normal
        mov r5, r0
        pop {{r0-r3,r12,lr}}
        bl {labels & ~1}
        sub r5, #16
        ldr r1, ={names if split_bank else 0x60ec0000}
        mov r0, #{32 if split_bank else 0x3000}
        mla r1, r5, r0, r1
        ldrb r9, [r11, #0x6e]
        b.w 0x1f992
    normal:
        pop {{r0-r3,r12,lr}}
        ldrb r0, [r11, #10]
        b.w 0x1f954
    ''')
    return [(0x1f6b8,4,route),(0x1f950,4,name)]
