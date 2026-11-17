"""Read-only checkpoint telemetry, independent of the stable DGT1 packet."""
def install(emit,installs,ram):
    command=0x20010cbc+0x485+0x32*9
    assert ram[command-0x20000000:command-0x20000000+9]==bytes(9)
    fn=emit('capture_metrics_read','''
        mov r12, r2
        cmp r1, #8
        bne invalid
        ldrb r2, [r0, #6]
        cmp r2, #0
        bne invalid
        ldrb r2, [r0, #7]
        cmp r2, #0xf7
        bne invalid
        push {r4-r7,lr}
        sub sp, #60
        str r12, [sp]
        ldr r0, =0x31434743
        str r0, [sp, #4]
        add r4, sp, #8
        ldr r5, =0x3e020
        movs r6, #2
    slot:
        ldr r0, [r5]
        bl pack
        ldr r0, [r5, #4]
        bl pack
        ldr r0, [r5, #20]
        bl pack
        ldr r0, [r5, #24]
        bl pack
        ldr r0, [r5, #28]
        bl pack
        add r5, #32
        subs r6, #1
        bne slot
        movs r0, #0x32
        movs r1, #2
        add r2, sp, #4
        movs r3, #54
        bl 0x5248
        add sp, #60
        pop {r4-r7,pc}
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
    installs.extend([(command,fn),(command+4,fn)])
