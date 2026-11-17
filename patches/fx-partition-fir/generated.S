/* initialize_step @ 0x38120 */

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
    

/* selection @ 0x381bc */

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
    

/* wheel_native @ 0x381f0 */

        push {r4,r6,r7,lr}
        ldr r6, =0x200101f4
        b.w 0x4ae4
    

/* wheel @ 0x381fc */

        cmp r0, #7
        beq extended
        cmp r0, #3
        beq extended
        b.w 229872
    extended:
        push {r4-r8,lr}
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
        pop {r4-r8,pc}
    

/* parameter_count @ 0x382d8 */

        push {r0,lr}
        bl 229820
        cmp r0, #25
        bhi normal
        cmp r0, #16
        bhs capture
        movs r1, #7
        mul r0, r0, r1
        ldr r1, =0x28ca5
        ldrb r0, [r1, r0]
        add sp, #4
        pop {pc}
    capture:
        movs r0, #2
        add sp, #4
        pop {pc}
    normal:
        pop {r0,lr}
        ldr r1, =0x2001683c
        add r2, r0, r0, lsl #1
        b.w 0x4c04
    

/* parameter_edit @ 0x38310 */

        push {r0,lr}
        bl 229820
        cmp r0, #25
        bhi normal
        mov r3, r0
        pop {r0,lr}
        push {r4-r6,lr}
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
        pop {r4-r6,pc}
    normal:
        pop {r0,lr}
        ldr r2, =0x200101f4
        push {r4-r7,lr}
        b.w 0x4ce4
    

/* fx_bank_names @ 0x383a0 */
.byte 70,88,32,48,49,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,70,88,32,48,50,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,70,88,32,48,51,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,70,88,32,48,52,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,70,88,32,48,53,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,70,88,32,48,54,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,70,88,32,48,55,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,70,88,32,48,56,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,70,88,32,48,57,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,70,88,32,49,48,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

/* capture_parameter_layout @ 0x384e0 */
.short 15,104,0,170,104,0

/* display_route @ 0x384ec */

        push {r0-r3,r12,lr}
        mov r0, r8
        bl 229820
        cmp r0, #25
        bhi normal
        mov r5, r0
        pop {r0-r3,r12,lr}
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
        
            movs r1, #3
            strh r1, [r6, #4]
            movs r1, #240
            strh r1, [r6, #8]
            movw r1, #320
            strh r1, [r6, #10]
            sub r1, r5, #16
            addw r1, r1, #0x396
            strh r1, [r6, #0xc6]
        
        mov r3, #0
        ldr r10, =230624
        movs r1, #2
        b.w 0x1f840
    normal:
        pop {r0-r3,r12,lr}
        cmp r8, #7
        b.w 0x1f6bc
    

/* capture_labels @ 0x38588 */

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
    

/* display_capture_name @ 0x385e8 */

        push {r0-r3,r12,lr}
        ldrb r0, [r11, #10]
        bl 229820
        cmp r0, #16
        blo normal
        cmp r0, #25
        bhi normal
        mov r5, r0
        pop {r0-r3,r12,lr}
        bl 230792
        sub r5, #16
        ldr r1, =230304
        mov r0, #32
        mla r1, r5, r0, r1
        ldrb r9, [r11, #0x6e]
        b.w 0x1f992
    normal:
        pop {r0-r3,r12,lr}
        ldrb r0, [r11, #10]
        b.w 0x1f954
    

/* capture_fir8 @ 0x3862c */

        ldr r12, [sp, #4]
        cmp r12, #512
        bne fallback
        ldr r12, [sp, #8]
        cmp r12, #384
        beq supported
        cmp r12, #512
        bne fallback
    supported:
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
    
        vldr s0, [r9]
        ldr r12, [r0], #4
        str r12, [r9], #4
        cmp r9, r8
        it eq
        moveq r9, r7
        
        vldr s1, [r9]
        ldr r12, [r0], #4
        str r12, [r9], #4
        cmp r9, r8
        it eq
        moveq r9, r7
        
        vldr s2, [r9]
        ldr r12, [r0], #4
        str r12, [r9], #4
        cmp r9, r8
        it eq
        moveq r9, r7
        
        vldr s3, [r9]
        ldr r12, [r0], #4
        str r12, [r9], #4
        cmp r9, r8
        it eq
        moveq r9, r7
        
        vldr s4, [r9]
        ldr r12, [r0], #4
        str r12, [r9], #4
        cmp r9, r8
        it eq
        moveq r9, r7
        
        vldr s5, [r9]
        ldr r12, [r0], #4
        str r12, [r9], #4
        cmp r9, r8
        it eq
        moveq r9, r7
        
        vldr s6, [r9]
        ldr r12, [r0], #4
        str r12, [r9], #4
        cmp r9, r8
        it eq
        moveq r9, r7
        
        vldr s7, [r9]
        ldr r12, [r0], #4
        str r12, [r9], #4
        cmp r9, r8
        it eq
        moveq r9, r7
        movs r12, #0
vmov s8, r12
vmov s9, r12
vmov s10, r12
vmov s11, r12
vmov s12, r12
vmov s13, r12
vmov s14, r12
vmov s15, r12
ldr r10, [sp, #56]
lsr r10, #3
loop:
vldmia r4!, {s16}
vmla.f32 s8, s0, s16
vmla.f32 s9, s1, s16
vmla.f32 s10, s2, s16
vmla.f32 s11, s3, s16
vmla.f32 s12, s4, s16
vmla.f32 s13, s5, s16
vmla.f32 s14, s6, s16
vmla.f32 s15, s7, s16

        vldmia r9!, {s0}
        cmp r9, r8
        it eq
        moveq r9, r7
        vldmia r4!, {s16}
vmla.f32 s8, s1, s16
vmla.f32 s9, s2, s16
vmla.f32 s10, s3, s16
vmla.f32 s11, s4, s16
vmla.f32 s12, s5, s16
vmla.f32 s13, s6, s16
vmla.f32 s14, s7, s16
vmla.f32 s15, s0, s16

        vldmia r9!, {s1}
        cmp r9, r8
        it eq
        moveq r9, r7
        vldmia r4!, {s16}
vmla.f32 s8, s2, s16
vmla.f32 s9, s3, s16
vmla.f32 s10, s4, s16
vmla.f32 s11, s5, s16
vmla.f32 s12, s6, s16
vmla.f32 s13, s7, s16
vmla.f32 s14, s0, s16
vmla.f32 s15, s1, s16

        vldmia r9!, {s2}
        cmp r9, r8
        it eq
        moveq r9, r7
        vldmia r4!, {s16}
vmla.f32 s8, s3, s16
vmla.f32 s9, s4, s16
vmla.f32 s10, s5, s16
vmla.f32 s11, s6, s16
vmla.f32 s12, s7, s16
vmla.f32 s13, s0, s16
vmla.f32 s14, s1, s16
vmla.f32 s15, s2, s16

        vldmia r9!, {s3}
        cmp r9, r8
        it eq
        moveq r9, r7
        vldmia r4!, {s16}
vmla.f32 s8, s4, s16
vmla.f32 s9, s5, s16
vmla.f32 s10, s6, s16
vmla.f32 s11, s7, s16
vmla.f32 s12, s0, s16
vmla.f32 s13, s1, s16
vmla.f32 s14, s2, s16
vmla.f32 s15, s3, s16

        vldmia r9!, {s4}
        cmp r9, r8
        it eq
        moveq r9, r7
        vldmia r4!, {s16}
vmla.f32 s8, s5, s16
vmla.f32 s9, s6, s16
vmla.f32 s10, s7, s16
vmla.f32 s11, s0, s16
vmla.f32 s12, s1, s16
vmla.f32 s13, s2, s16
vmla.f32 s14, s3, s16
vmla.f32 s15, s4, s16

        vldmia r9!, {s5}
        cmp r9, r8
        it eq
        moveq r9, r7
        vldmia r4!, {s16}
vmla.f32 s8, s6, s16
vmla.f32 s9, s7, s16
vmla.f32 s10, s0, s16
vmla.f32 s11, s1, s16
vmla.f32 s12, s2, s16
vmla.f32 s13, s3, s16
vmla.f32 s14, s4, s16
vmla.f32 s15, s5, s16

        vldmia r9!, {s6}
        cmp r9, r8
        it eq
        moveq r9, r7
        vldmia r4!, {s16}
vmla.f32 s8, s7, s16
vmla.f32 s9, s0, s16
vmla.f32 s10, s1, s16
vmla.f32 s11, s2, s16
vmla.f32 s12, s3, s16
vmla.f32 s13, s4, s16
vmla.f32 s14, s5, s16
vmla.f32 s15, s6, s16

        vldmia r9!, {s7}
        cmp r9, r8
        it eq
        moveq r9, r7
        
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
    

/* capture_core @ 0x388c8 */
/* Vendor capture core with explicit drive and independent scratch arguments. */
push     {r4, r5, r6, r7, lr}
mov      r4, r1
mov r1, r2
sub      sp, #0x14
ldr r6, =0x1e5a4
nop
mov      r5, r3
nop
ldr r7, [sp, #40]
nop
uxtb     r2, r1
cmp      r2, #0x65
ldr r12, =1065185444
vmov s0, r12
add.w    r2, r5, #0x28
it       ge
movge    r1, #0x64
uxtb     r1, r1
movs     r3, #8
ldr.w    r1, [r6, r1, lsl #2]
str      r1, [r5, #0x2c]
add.w    r1, r7, #0xc
bl       #0x8674
movs     r3, #8
movw     r0, #0x2034
str      r3, [sp, #0xc]
add      r0, r5
movw     r1, #0x203c
mov.w    ip, #0x200
str      r0, [sp]
adds     r3, r5, r1
str.w    ip, [sp, #8]
addw     r2, r5, #0x834
str.w    ip, [sp, #4]
add.w    r1, r7, #0x4c
add.w    r0, r7, #0xc
bl 230956
movs     r0, #8
mov.w    r1, #0x258
str      r0, [sp, #4]
mov      r3, r7
str      r1, [sp]
add.w    r2, r6, #0x194
add.w    r1, r7, #0x2c
add.w    r0, r7, #0x4c
bl       #0x1b2c8
movw     r3, #0x2038
mov.w    r1, #0x200
movs     r0, #8
add      r3, r5
str      r0, [sp, #0xc]
movw     r6, #0x283c
str      r1, [sp, #8]
movw     ip, #0x1834
str      r1, [sp, #4]
add.w    r2, r5, ip
str      r3, [sp]
adds     r3, r5, r6
add.w    r1, r7, #0x6c
add.w    r0, r7, #0x2c
bl 230956
mov      r1, r4
add.w    r0, r7, #0x6c
add      sp, #0x14
movs     r2, #8
vmov.f32 s0, #1.000000e+00
pop.w    {r4, r5, r6, r7, lr}
b.w      #0x8560


/* capture_init_step @ 0x38998 */

        push {r4-r8,lr}
        mov r4, r1
        mov r5, r2
        mov r6, r0
        ldr r7, [r5, #16]
        mov r8, #128
        ldr r1, =1626206208
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
    

/* capture_budget_guard @ 0x38a10 */

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
            ldr r2, =100000
            movw r12, #10000
            cmp r2, r12
            blo safe
            movw r12, #5000
            sub r2, r2, r12
            cmp r3, r2
            blo safe
            str r1, [r0, #28]
            movs r2, #3
            str r2, [r0, #4]
            movs r0, #1
            bx lr
        safe:
            movs r0, #0
            bx lr
        

/* slot7_model0 @ 0x38a5c */

                push {r4-r7, lr}
                sub sp, #28
                str r0, [sp, #8]
                str r1, [sp, #12]
                str r2, [sp, #16]
                str r3, [sp, #20]
                ldr r4, [sp, #48]
                
                ldr r6, =536937120
                ldrb r5, [r6, #67]
                subs r5, #0x50
                cmp r5, #25
                bhi normal
                ldrb r7, [r6, #7]
                and r7, r7, #0x3f
                cmp r7, #0
                bne normal
                cmp r5, #16
                bhs capture
            
                ldr r6, =253984
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
                ldr r1, =241664
                ldr r2, =2180644864
                mov r3, r6
                bl 229664
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
                movs r0, #1
                str r0, [sp, #4]
                ldr r7, =0x2000bc48
                ldr r7, [r7, r5, lsl #2]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                blx r7
                add sp, #28
                pop {r4-r7, pc}
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
                pop {r4-r7, pc}
            normal:
                ldr r6, =253984
                movs r5, #0
                str r5, [r6]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                add sp, #28
                pop {r4-r7, lr}
                ldr r12, =177537
                bx r12
                
    capture:
        sub r0, r5, #16
        mov r1, #0x3000
        ldr r2, =1626202112
        mla r0, r0, r1, r2
        ldrb r0, [r0, #33]
        cmp r0, #1
        bne preparing
        ldr r6, =253984
        ldr r7, [r6]
        add r0, r5, #1
        cmp r0, r7
        beq capture_ready
        str r0, [r6]
        movs r0, #0
        str r0, [r6, #4]
        str r0, [r6, #16]
    capture_ready:
        ldr r0, [r6, #4]
        cmp r0, #3; beq preparing
        cmp r0, #2
        beq preparing
        cmp r0, #0
        bne capture_run
        sub r0, r5, #16
        ldr r1, =2180644864
        mov r2, r6
        bl 224528
        cmp r0, #0
        beq preparing
    capture_run:
        ldr r0, [sp, #8]; ldr r1, [sp, #12]; ldr r2, =2180644864; bl 225648
        ldr r0, =253984
        movs r1, #0
        bl 231952
        cmp r0, #0
        bne preparing
        
        ldr r7, =241664
        ldr r0, =0x20000000
        ldr r1, [r0]
        ldr r2, [r0, #4]
        str r1, [r7]
        str r2, [r7, #4]
        str r7, [sp]
        ldr r0, [sp, #8]
        ldr r1, [sp, #16]
        ldrb r2, [r4, #3]
        ldr r3, =2180644864
        bl 225752
        ldr r0, =253984
        movs r1, #1
        bl 231952
        cmp r0, #0
        bne preparing
        
        str r7, [sp]
        ldr r0, [sp, #12]
        ldr r1, [sp, #20]
        ldrb r2, [r4, #3]
        ldr r3, =2180644912
        bl 225752
        ldr r0, =253984
        movs r1, #2
        bl 231952
        cmp r0, #0
        bne preparing
        
        ldrb r0, [r4, #4]
        cmp r0, #99
        it hi
        movhi r0, #99
        vmov s0, r0
        vcvt.f32.u32 s0, s0
        ldr r0, =0x3ca3d70a
        vmov s1, r0
        vmul.f32 s0, s0, s1
        ldr r2, =2180644864
        vstr s0, [r2, #4]
        ldr r2, =2180644912
        vstr s0, [r2, #4]
        ldr r0, [sp, #16]
        mov r1, r0
        ldr r2, =2180644864
        movs r3, #8
        ldr r12, =0x3f7d70a4
        vmov s0, r12
        bl 0x8674
        ldr r0, [sp, #20]
        mov r1, r0
        ldr r2, =2180644912
        movs r3, #8
        ldr r12, =0x3f7d70a4
        vmov s0, r12
        bl 0x8674
        add sp, #28
        pop {r4-r7,pc}
    
            

/* slot7_model1 @ 0x38c78 */

                push {r4-r7, lr}
                sub sp, #28
                str r0, [sp, #8]
                str r1, [sp, #12]
                str r2, [sp, #16]
                str r3, [sp, #20]
                ldr r4, [sp, #48]
                b normal
                ldr r6, =253984
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
                ldr r1, =241664
                ldr r2, =2180644864
                mov r3, r6
                bl 229664
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
                movs r0, #1
                str r0, [sp, #4]
                ldr r7, =0x2000bc48
                ldr r7, [r7, r5, lsl #2]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                blx r7
                add sp, #28
                pop {r4-r7, pc}
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
                pop {r4-r7, pc}
            normal:
                ldr r6, =253984
                movs r5, #0
                str r5, [r6]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                add sp, #28
                pop {r4-r7, lr}
                ldr r12, =121161
                bx r12
                
            

/* slot3_model0 @ 0x38d40 */

                push {r4-r7, lr}
                sub sp, #28
                str r0, [sp, #8]
                str r1, [sp, #12]
                str r2, [sp, #16]
                str r3, [sp, #20]
                ldr r4, [sp, #48]
                b normal
                ldr r6, =254016
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
                ldr r1, =245760
                ldr r2, =2180677632
                mov r3, r6
                bl 229664
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
                movs r0, #2
                str r0, [sp, #4]
                ldr r7, =0x2000bc48
                ldr r7, [r7, r5, lsl #2]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                blx r7
                add sp, #28
                pop {r4-r7, pc}
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
                pop {r4-r7, pc}
            normal:
                ldr r6, =254016
                movs r5, #0
                str r5, [r6]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                add sp, #28
                pop {r4-r7, lr}
                ldr r12, =178653
                bx r12
                
            

/* slot3_model1 @ 0x38e08 */

                push {r4-r7, lr}
                sub sp, #28
                str r0, [sp, #8]
                str r1, [sp, #12]
                str r2, [sp, #16]
                str r3, [sp, #20]
                ldr r4, [sp, #48]
                b normal
                ldr r6, =254016
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
                ldr r1, =245760
                ldr r2, =2180677632
                mov r3, r6
                bl 229664
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
                movs r0, #2
                str r0, [sp, #4]
                ldr r7, =0x2000bc48
                ldr r7, [r7, r5, lsl #2]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                blx r7
                add sp, #28
                pop {r4-r7, pc}
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
                pop {r4-r7, pc}
            normal:
                ldr r6, =254016
                movs r5, #0
                str r5, [r6]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                add sp, #28
                pop {r4-r7, lr}
                ldr r12, =180673
                bx r12
                
            

/* slot3_model2 @ 0x38ed0 */

                push {r4-r7, lr}
                sub sp, #28
                str r0, [sp, #8]
                str r1, [sp, #12]
                str r2, [sp, #16]
                str r3, [sp, #20]
                ldr r4, [sp, #48]
                b normal
                ldr r6, =254016
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
                ldr r1, =245760
                ldr r2, =2180677632
                mov r3, r6
                bl 229664
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
                movs r0, #2
                str r0, [sp, #4]
                ldr r7, =0x2000bc48
                ldr r7, [r7, r5, lsl #2]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                blx r7
                add sp, #28
                pop {r4-r7, pc}
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
                pop {r4-r7, pc}
            normal:
                ldr r6, =254016
                movs r5, #0
                str r5, [r6]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                add sp, #28
                pop {r4-r7, lr}
                ldr r12, =183109
                bx r12
                
            

/* slot3_model3 @ 0x38f98 */

                push {r4-r7, lr}
                sub sp, #28
                str r0, [sp, #8]
                str r1, [sp, #12]
                str r2, [sp, #16]
                str r3, [sp, #20]
                ldr r4, [sp, #48]
                b normal
                ldr r6, =254016
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
                ldr r1, =245760
                ldr r2, =2180677632
                mov r3, r6
                bl 229664
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
                movs r0, #2
                str r0, [sp, #4]
                ldr r7, =0x2000bc48
                ldr r7, [r7, r5, lsl #2]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                blx r7
                add sp, #28
                pop {r4-r7, pc}
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
                pop {r4-r7, pc}
            normal:
                ldr r6, =254016
                movs r5, #0
                str r5, [r6]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                add sp, #28
                pop {r4-r7, lr}
                ldr r12, =189705
                bx r12
                
            

/* slot3_model4 @ 0x39060 */

                push {r4-r7, lr}
                sub sp, #28
                str r0, [sp, #8]
                str r1, [sp, #12]
                str r2, [sp, #16]
                str r3, [sp, #20]
                ldr r4, [sp, #48]
                b normal
                ldr r6, =254016
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
                ldr r1, =245760
                ldr r2, =2180677632
                mov r3, r6
                bl 229664
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
                movs r0, #2
                str r0, [sp, #4]
                ldr r7, =0x2000bc48
                ldr r7, [r7, r5, lsl #2]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                blx r7
                add sp, #28
                pop {r4-r7, pc}
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
                pop {r4-r7, pc}
            normal:
                ldr r6, =254016
                movs r5, #0
                str r5, [r6]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                add sp, #28
                pop {r4-r7, lr}
                ldr r12, =170885
                bx r12
                
            

/* slot3_model5 @ 0x39128 */

                push {r4-r7, lr}
                sub sp, #28
                str r0, [sp, #8]
                str r1, [sp, #12]
                str r2, [sp, #16]
                str r3, [sp, #20]
                ldr r4, [sp, #48]
                
                ldr r6, =536937120
                ldrb r5, [r6, #68]
                subs r5, #0x50
                cmp r5, #25
                bhi normal
                ldrb r7, [r6, #3]
                and r7, r7, #0x3f
                cmp r7, #5
                bne normal
                cmp r5, #16
                bhs capture
            
                ldr r6, =254016
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
                ldr r1, =245760
                ldr r2, =2180677632
                mov r3, r6
                bl 229664
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
                movs r0, #2
                str r0, [sp, #4]
                ldr r7, =0x2000bc48
                ldr r7, [r7, r5, lsl #2]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                blx r7
                add sp, #28
                pop {r4-r7, pc}
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
                pop {r4-r7, pc}
            normal:
                ldr r6, =254016
                movs r5, #0
                str r5, [r6]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                add sp, #28
                pop {r4-r7, lr}
                ldr r12, =178137
                bx r12
                
    capture:
        sub r0, r5, #16
        mov r1, #0x3000
        ldr r2, =1626202112
        mla r0, r0, r1, r2
        ldrb r0, [r0, #33]
        cmp r0, #1
        bne preparing
        ldr r6, =254016
        ldr r7, [r6]
        add r0, r5, #1
        cmp r0, r7
        beq capture_ready
        str r0, [r6]
        movs r0, #0
        str r0, [r6, #4]
        str r0, [r6, #16]
    capture_ready:
        ldr r0, [r6, #4]
        cmp r0, #3; beq preparing
        cmp r0, #2
        beq preparing
        cmp r0, #0
        bne capture_run
        sub r0, r5, #16
        ldr r1, =2180677632
        mov r2, r6
        bl 224528
        cmp r0, #0
        beq preparing
    capture_run:
        ldr r0, [sp, #8]; ldr r1, [sp, #12]; ldr r2, =2180677632; bl 225648
        ldr r0, =254016
        movs r1, #0
        bl 231952
        cmp r0, #0
        bne preparing
        
        ldr r7, =245760
        ldr r0, =0x20000000
        ldr r1, [r0]
        ldr r2, [r0, #4]
        str r1, [r7]
        str r2, [r7, #4]
        str r7, [sp]
        ldr r0, [sp, #8]
        ldr r1, [sp, #16]
        ldrb r2, [r4, #3]
        ldr r3, =2180677632
        bl 225752
        ldr r0, =254016
        movs r1, #1
        bl 231952
        cmp r0, #0
        bne preparing
        
        str r7, [sp]
        ldr r0, [sp, #12]
        ldr r1, [sp, #20]
        ldrb r2, [r4, #3]
        ldr r3, =2180677680
        bl 225752
        ldr r0, =254016
        movs r1, #2
        bl 231952
        cmp r0, #0
        bne preparing
        
        ldrb r0, [r4, #4]
        cmp r0, #99
        it hi
        movhi r0, #99
        vmov s0, r0
        vcvt.f32.u32 s0, s0
        ldr r0, =0x3ca3d70a
        vmov s1, r0
        vmul.f32 s0, s0, s1
        ldr r2, =2180677632
        vstr s0, [r2, #4]
        ldr r2, =2180677680
        vstr s0, [r2, #4]
        ldr r0, [sp, #16]
        mov r1, r0
        ldr r2, =2180677632
        movs r3, #8
        ldr r12, =0x3f7d70a4
        vmov s0, r12
        bl 0x8674
        ldr r0, [sp, #20]
        mov r1, r0
        ldr r2, =2180677680
        movs r3, #8
        ldr r12, =0x3f7d70a4
        vmov s0, r12
        bl 0x8674
        add sp, #28
        pop {r4-r7,pc}
    
            

/* slot3_model6 @ 0x39344 */

                push {r4-r7, lr}
                sub sp, #28
                str r0, [sp, #8]
                str r1, [sp, #12]
                str r2, [sp, #16]
                str r3, [sp, #20]
                ldr r4, [sp, #48]
                b normal
                ldr r6, =254016
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
                ldr r1, =245760
                ldr r2, =2180677632
                mov r3, r6
                bl 229664
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
                movs r0, #2
                str r0, [sp, #4]
                ldr r7, =0x2000bc48
                ldr r7, [r7, r5, lsl #2]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                blx r7
                add sp, #28
                pop {r4-r7, pc}
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
                pop {r4-r7, pc}
            normal:
                ldr r6, =254016
                movs r5, #0
                str r5, [r6]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                add sp, #28
                pop {r4-r7, lr}
                ldr r12, =191065
                bx r12
                
            

/* slot3_model7 @ 0x3940c */

                push {r4-r7, lr}
                sub sp, #28
                str r0, [sp, #8]
                str r1, [sp, #12]
                str r2, [sp, #16]
                str r3, [sp, #20]
                ldr r4, [sp, #48]
                b normal
                ldr r6, =254016
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
                ldr r1, =245760
                ldr r2, =2180677632
                mov r3, r6
                bl 229664
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
                movs r0, #2
                str r0, [sp, #4]
                ldr r7, =0x2000bc48
                ldr r7, [r7, r5, lsl #2]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                blx r7
                add sp, #28
                pop {r4-r7, pc}
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
                pop {r4-r7, pc}
            normal:
                ldr r6, =254016
                movs r5, #0
                str r5, [r6]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                add sp, #28
                pop {r4-r7, lr}
                ldr r12, =190417
                bx r12
                
            

/* slot3_model8 @ 0x394d4 */

                push {r4-r7, lr}
                sub sp, #28
                str r0, [sp, #8]
                str r1, [sp, #12]
                str r2, [sp, #16]
                str r3, [sp, #20]
                ldr r4, [sp, #48]
                b normal
                ldr r6, =254016
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
                ldr r1, =245760
                ldr r2, =2180677632
                mov r3, r6
                bl 229664
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
                movs r0, #2
                str r0, [sp, #4]
                ldr r7, =0x2000bc48
                ldr r7, [r7, r5, lsl #2]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                blx r7
                add sp, #28
                pop {r4-r7, pc}
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
                pop {r4-r7, pc}
            normal:
                ldr r6, =254016
                movs r5, #0
                str r5, [r6]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                add sp, #28
                pop {r4-r7, lr}
                ldr r12, =156397
                bx r12
                
            

/* slot3_model9 @ 0x3959c */

                push {r4-r7, lr}
                sub sp, #28
                str r0, [sp, #8]
                str r1, [sp, #12]
                str r2, [sp, #16]
                str r3, [sp, #20]
                ldr r4, [sp, #48]
                b normal
                ldr r6, =254016
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
                ldr r1, =245760
                ldr r2, =2180677632
                mov r3, r6
                bl 229664
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
                movs r0, #2
                str r0, [sp, #4]
                ldr r7, =0x2000bc48
                ldr r7, [r7, r5, lsl #2]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                blx r7
                add sp, #28
                pop {r4-r7, pc}
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
                pop {r4-r7, pc}
            normal:
                ldr r6, =254016
                movs r5, #0
                str r5, [r6]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                add sp, #28
                pop {r4-r7, lr}
                ldr r12, =172593
                bx r12
                
            

/* slot3_model10 @ 0x39664 */

                push {r4-r7, lr}
                sub sp, #28
                str r0, [sp, #8]
                str r1, [sp, #12]
                str r2, [sp, #16]
                str r3, [sp, #20]
                ldr r4, [sp, #48]
                b normal
                ldr r6, =254016
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
                ldr r1, =245760
                ldr r2, =2180677632
                mov r3, r6
                bl 229664
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
                movs r0, #2
                str r0, [sp, #4]
                ldr r7, =0x2000bc48
                ldr r7, [r7, r5, lsl #2]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                blx r7
                add sp, #28
                pop {r4-r7, pc}
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
                pop {r4-r7, pc}
            normal:
                ldr r6, =254016
                movs r5, #0
                str r5, [r6]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                add sp, #28
                pop {r4-r7, lr}
                ldr r12, =174873
                bx r12
                
            

/* slot3_model11 @ 0x3972c */

                push {r4-r7, lr}
                sub sp, #28
                str r0, [sp, #8]
                str r1, [sp, #12]
                str r2, [sp, #16]
                str r3, [sp, #20]
                ldr r4, [sp, #48]
                b normal
                ldr r6, =254016
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
                ldr r1, =245760
                ldr r2, =2180677632
                mov r3, r6
                bl 229664
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
                movs r0, #2
                str r0, [sp, #4]
                ldr r7, =0x2000bc48
                ldr r7, [r7, r5, lsl #2]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                blx r7
                add sp, #28
                pop {r4-r7, pc}
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
                pop {r4-r7, pc}
            normal:
                ldr r6, =254016
                movs r5, #0
                str r5, [r6]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                add sp, #28
                pop {r4-r7, lr}
                ldr r12, =185333
                bx r12
                
            

/* slot3_model12 @ 0x397f4 */

                push {r4-r7, lr}
                sub sp, #28
                str r0, [sp, #8]
                str r1, [sp, #12]
                str r2, [sp, #16]
                str r3, [sp, #20]
                ldr r4, [sp, #48]
                b normal
                ldr r6, =254016
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
                ldr r1, =245760
                ldr r2, =2180677632
                mov r3, r6
                bl 229664
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
                movs r0, #2
                str r0, [sp, #4]
                ldr r7, =0x2000bc48
                ldr r7, [r7, r5, lsl #2]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                blx r7
                add sp, #28
                pop {r4-r7, pc}
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
                pop {r4-r7, pc}
            normal:
                ldr r6, =254016
                movs r5, #0
                str r5, [r6]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                add sp, #28
                pop {r4-r7, lr}
                ldr r12, =142669
                bx r12
                
            

/* slot4_model0 @ 0x398bc */

                push {r4-r7, lr}
                sub sp, #28
                str r0, [sp, #8]
                str r1, [sp, #12]
                str r2, [sp, #16]
                str r3, [sp, #20]
                ldr r4, [sp, #48]
                b normal
                ldr r6, =254048
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
                ldr r1, =249856
                ldr r2, =2180710400
                mov r3, r6
                bl 229664
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
                movs r0, #3
                str r0, [sp, #4]
                ldr r7, =0x2000bc48
                ldr r7, [r7, r5, lsl #2]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                blx r7
                add sp, #28
                pop {r4-r7, pc}
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
                pop {r4-r7, pc}
            normal:
                ldr r6, =254048
                movs r5, #0
                str r5, [r6]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                add sp, #28
                pop {r4-r7, lr}
                ldr r12, =155117
                bx r12
                
            

/* slot4_model1 @ 0x39984 */

                push {r4-r7, lr}
                sub sp, #28
                str r0, [sp, #8]
                str r1, [sp, #12]
                str r2, [sp, #16]
                str r3, [sp, #20]
                ldr r4, [sp, #48]
                b normal
                ldr r6, =254048
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
                ldr r1, =249856
                ldr r2, =2180710400
                mov r3, r6
                bl 229664
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
                movs r0, #3
                str r0, [sp, #4]
                ldr r7, =0x2000bc48
                ldr r7, [r7, r5, lsl #2]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                blx r7
                add sp, #28
                pop {r4-r7, pc}
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
                pop {r4-r7, pc}
            normal:
                ldr r6, =254048
                movs r5, #0
                str r5, [r6]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                add sp, #28
                pop {r4-r7, lr}
                ldr r12, =164797
                bx r12
                
            

/* slot4_model2 @ 0x39a4c */

                push {r4-r7, lr}
                sub sp, #28
                str r0, [sp, #8]
                str r1, [sp, #12]
                str r2, [sp, #16]
                str r3, [sp, #20]
                ldr r4, [sp, #48]
                
                ldr r6, =536937120
                ldrb r5, [r6, #69]
                subs r5, #0x50
                cmp r5, #15
                bhi normal
                ldrb r7, [r6, #4]
                and r7, r7, #0x3f
                cmp r7, #2
                bne normal
                cmp r5, #16
                bhs capture
            
                ldr r6, =254048
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
                ldr r1, =249856
                ldr r2, =2180710400
                mov r3, r6
                bl 229664
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
                movs r0, #3
                str r0, [sp, #4]
                ldr r7, =0x2000bc48
                ldr r7, [r7, r5, lsl #2]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                blx r7
                add sp, #28
                pop {r4-r7, pc}
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
                pop {r4-r7, pc}
            normal:
                ldr r6, =254048
                movs r5, #0
                str r5, [r6]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                add sp, #28
                pop {r4-r7, lr}
                ldr r12, =162485
                bx r12
                
    capture:
        sub r0, r5, #16
        mov r1, #0x3000
        ldr r2, =1626202112
        mla r0, r0, r1, r2
        ldrb r0, [r0, #33]
        cmp r0, #1
        bne preparing
        ldr r6, =254048
        ldr r7, [r6]
        add r0, r5, #1
        cmp r0, r7
        beq capture_ready
        str r0, [r6]
        movs r0, #0
        str r0, [r6, #4]
        str r0, [r6, #16]
    capture_ready:
        ldr r0, [r6, #4]
        cmp r0, #3; beq preparing
        cmp r0, #2
        beq preparing
        cmp r0, #0
        bne capture_run
        sub r0, r5, #16
        ldr r1, =2180710400
        mov r2, r6
        bl 224528
        cmp r0, #0
        beq preparing
    capture_run:
        ldr r0, [sp, #8]; ldr r1, [sp, #12]; ldr r2, =2180710400; bl 225648
        ldr r0, =254048
        movs r1, #0
        bl 231952
        cmp r0, #0
        bne preparing
        
        ldr r7, =249856
        ldr r0, =0x20000000
        ldr r1, [r0]
        ldr r2, [r0, #4]
        str r1, [r7]
        str r2, [r7, #4]
        str r7, [sp]
        ldr r0, [sp, #8]
        ldr r1, [sp, #16]
        ldrb r2, [r4, #3]
        ldr r3, =2180710400
        bl 225752
        ldr r0, =254048
        movs r1, #1
        bl 231952
        cmp r0, #0
        bne preparing
        
        str r7, [sp]
        ldr r0, [sp, #12]
        ldr r1, [sp, #20]
        ldrb r2, [r4, #3]
        ldr r3, =2180710448
        bl 225752
        ldr r0, =254048
        movs r1, #2
        bl 231952
        cmp r0, #0
        bne preparing
        
        ldrb r0, [r4, #4]
        cmp r0, #99
        it hi
        movhi r0, #99
        vmov s0, r0
        vcvt.f32.u32 s0, s0
        ldr r0, =0x3ca3d70a
        vmov s1, r0
        vmul.f32 s0, s0, s1
        ldr r2, =2180710400
        vstr s0, [r2, #4]
        ldr r2, =2180710448
        vstr s0, [r2, #4]
        ldr r0, [sp, #16]
        mov r1, r0
        ldr r2, =2180710400
        movs r3, #8
        ldr r12, =0x3f7d70a4
        vmov s0, r12
        bl 0x8674
        ldr r0, [sp, #20]
        mov r1, r0
        ldr r2, =2180710448
        movs r3, #8
        ldr r12, =0x3f7d70a4
        vmov s0, r12
        bl 0x8674
        add sp, #28
        pop {r4-r7,pc}
    
            

/* slot4_model3 @ 0x39c68 */

                push {r4-r7, lr}
                sub sp, #28
                str r0, [sp, #8]
                str r1, [sp, #12]
                str r2, [sp, #16]
                str r3, [sp, #20]
                ldr r4, [sp, #48]
                b normal
                ldr r6, =254048
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
                ldr r1, =249856
                ldr r2, =2180710400
                mov r3, r6
                bl 229664
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
                movs r0, #3
                str r0, [sp, #4]
                ldr r7, =0x2000bc48
                ldr r7, [r7, r5, lsl #2]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                blx r7
                add sp, #28
                pop {r4-r7, pc}
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
                pop {r4-r7, pc}
            normal:
                ldr r6, =254048
                movs r5, #0
                str r5, [r6]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                add sp, #28
                pop {r4-r7, lr}
                ldr r12, =132053
                bx r12
                
            

/* slot4_model4 @ 0x39d30 */

                push {r4-r7, lr}
                sub sp, #28
                str r0, [sp, #8]
                str r1, [sp, #12]
                str r2, [sp, #16]
                str r3, [sp, #20]
                ldr r4, [sp, #48]
                b normal
                ldr r6, =254048
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
                ldr r1, =249856
                ldr r2, =2180710400
                mov r3, r6
                bl 229664
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
                movs r0, #3
                str r0, [sp, #4]
                ldr r7, =0x2000bc48
                ldr r7, [r7, r5, lsl #2]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                blx r7
                add sp, #28
                pop {r4-r7, pc}
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
                pop {r4-r7, pc}
            normal:
                ldr r6, =254048
                movs r5, #0
                str r5, [r6]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                add sp, #28
                pop {r4-r7, lr}
                ldr r12, =169953
                bx r12
                
            

/* slot4_model5 @ 0x39df8 */

                push {r4-r7, lr}
                sub sp, #28
                str r0, [sp, #8]
                str r1, [sp, #12]
                str r2, [sp, #16]
                str r3, [sp, #20]
                ldr r4, [sp, #48]
                b normal
                ldr r6, =254048
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
                ldr r1, =249856
                ldr r2, =2180710400
                mov r3, r6
                bl 229664
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
                movs r0, #3
                str r0, [sp, #4]
                ldr r7, =0x2000bc48
                ldr r7, [r7, r5, lsl #2]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                blx r7
                add sp, #28
                pop {r4-r7, pc}
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
                pop {r4-r7, pc}
            normal:
                ldr r6, =254048
                movs r5, #0
                str r5, [r6]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                add sp, #28
                pop {r4-r7, lr}
                ldr r12, =161321
                bx r12
                
            

/* slot4_model6 @ 0x39ec0 */

                push {r4-r7, lr}
                sub sp, #28
                str r0, [sp, #8]
                str r1, [sp, #12]
                str r2, [sp, #16]
                str r3, [sp, #20]
                ldr r4, [sp, #48]
                b normal
                ldr r6, =254048
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
                ldr r1, =249856
                ldr r2, =2180710400
                mov r3, r6
                bl 229664
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
                movs r0, #3
                str r0, [sp, #4]
                ldr r7, =0x2000bc48
                ldr r7, [r7, r5, lsl #2]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                blx r7
                add sp, #28
                pop {r4-r7, pc}
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
                pop {r4-r7, pc}
            normal:
                ldr r6, =254048
                movs r5, #0
                str r5, [r6]
                ldr r0, [sp, #8]
                ldr r1, [sp, #12]
                ldr r2, [sp, #16]
                ldr r3, [sp, #20]
                add sp, #28
                pop {r4-r7, lr}
                ldr r12, =141005
                bx r12
                
            

/* command @ 0x39f88 */

        push {r4-r7, lr}
        sub sp, #20
        str r2, [sp]
        mov r4, r0
        mov r7, r1
        ldr r5, =536937120
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
        ldr r0, =54614086
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
        pop {r4-r7, pc}
    

/* diagnostic_begin @ 0x3a02c */

        push {r0-r4,lr}
        ldr r4, =254208
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
        pop {r0-r4,lr}
        b.w 0xde12
    

/* diagnostic_end @ 0x3a064 */

        push {r0-r4,lr}
        ldr r4, =254208
        ldr r0, =0xe0001004
        ldr r0, [r0]
        ldr r1, [r4, #4]
        subs r0, r0, r1
        str r0, [r4, #12]
        ldr r1, [r4, #16]
        cmp r0, r1
        it hi
        strhi r0, [r4, #16]
        
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
    
        movs r0, #0
        str r0, [r4, #20]
        pop {r0-r4,lr}
        b.w 0xde20
    

/* diagnostic_fault @ 0x3a0e8 */

        .cpu cortex-m7
        ldr r0, =254336
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
    

/* diagnostic_read @ 0x3a128 */

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
        sub sp, #92
        str r12, [sp]
        ldr r0, =0x31544744
        str r0, [sp, #4]
        add r4, sp, #8
        ldr r5, =254208
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
        ldr r0, =254208
        ldr r0, [r0]
        bl pack
        movs r0, #0x31
        movs r1, #2
        add r2, sp, #4
        movs r3, #84
        bl 0x5248
        add sp, #92
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
    

/* capture_metrics_read @ 0x3a1c4 */

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
    

/* cache_extra_state @ 0x3a23c */

            push {r0-r3}
            ldr r0, =0xe000ed90
            ldr r1, [r0]
            ubfx r1, r1, #8, #8
            cmp r1, #11
            blo unchanged
            ldr r1, =0x81fa001a
            str r1, [r0, #12]
            ldr r1, =0x1303c021
            str r1, [r0, #16]
        unchanged:
            pop {r0-r3}
            dsb
            b.w 0xc3da
        

/* boot @ 0x3a268 */
push {r0-r4, lr}
        ldr r0, =0x3b000
        ldr r1, =0x3e080
        movs r2, #0
    clear:
        str r2, [r0], #4
        cmp r0, r1
        blo clear
    
        ldr r0, =254208
        ldr r1, =254400
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
    ldr r0, =0x20010ba5
movs r1, #20
strb r1, [r0]
ldr r0, =536919360
ldr r1, =232029
str r1, [r0]
ldr r0, =536919364
ldr r1, =232569
str r1, [r0]
ldr r0, =536919676
ldr r1, =232769
str r1, [r0]
ldr r0, =536919680
ldr r1, =232969
str r1, [r0]
ldr r0, =536919684
ldr r1, =233169
str r1, [r0]
ldr r0, =536919688
ldr r1, =233369
str r1, [r0]
ldr r0, =536919692
ldr r1, =233569
str r1, [r0]
ldr r0, =536919696
ldr r1, =233769
str r1, [r0]
ldr r0, =536919700
ldr r1, =234309
str r1, [r0]
ldr r0, =536919704
ldr r1, =234509
str r1, [r0]
ldr r0, =536919708
ldr r1, =234709
str r1, [r0]
ldr r0, =536919712
ldr r1, =234909
str r1, [r0]
ldr r0, =536919716
ldr r1, =235109
str r1, [r0]
ldr r0, =536919720
ldr r1, =235309
str r1, [r0]
ldr r0, =536919724
ldr r1, =235509
str r1, [r0]
ldr r0, =536918896
ldr r1, =235709
str r1, [r0]
ldr r0, =536918900
ldr r1, =235909
str r1, [r0]
ldr r0, =536918904
ldr r1, =236109
str r1, [r0]
ldr r0, =536918908
ldr r1, =236649
str r1, [r0]
ldr r0, =536918912
ldr r1, =236849
str r1, [r0]
ldr r0, =536918916
ldr r1, =237049
str r1, [r0]
ldr r0, =536918920
ldr r1, =237249
str r1, [r0]
ldr r0, =536941297
ldr r1, =237449
str r1, [r0]
ldr r0, =536941301
ldr r1, =237449
str r1, [r0]
ldr r0, =536941306
ldr r1, =237865
str r1, [r0]
ldr r0, =536941310
ldr r1, =237865
str r1, [r0]
ldr r0, =536941315
ldr r1, =238021
str r1, [r0]
ldr r0, =536941319
ldr r1, =238021
str r1, [r0]
pop {r0-r4, lr}
b.w 0x76fc

