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
    

/* slot7_model0 @ 0x381bc */

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
                cmp r5, #15
                bhi normal
                ldrb r7, [r6, #7]
                and r7, r7, #0x3f
                cmp r7, #0
                bne normal
            
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
            

/* slot7_model1 @ 0x3829c */

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
            

/* slot3_model0 @ 0x38364 */

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
            

/* slot3_model1 @ 0x3842c */

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
            

/* slot3_model2 @ 0x384f4 */

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
            

/* slot3_model3 @ 0x385bc */

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
            

/* slot3_model4 @ 0x38684 */

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
            

/* slot3_model5 @ 0x3874c */

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
                cmp r5, #15
                bhi normal
                ldrb r7, [r6, #3]
                and r7, r7, #0x3f
                cmp r7, #5
                bne normal
            
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
            

/* slot3_model6 @ 0x3882c */

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
            

/* slot3_model7 @ 0x388f4 */

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
            

/* slot3_model8 @ 0x389bc */

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
            

/* slot3_model9 @ 0x38a84 */

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
            

/* slot3_model10 @ 0x38b4c */

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
            

/* slot3_model11 @ 0x38c14 */

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
            

/* slot3_model12 @ 0x38cdc */

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
            

/* slot4_model0 @ 0x38da4 */

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
            

/* slot4_model1 @ 0x38e6c */

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
            

/* slot4_model2 @ 0x38f34 */

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
            

/* slot4_model3 @ 0x39014 */

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
            

/* slot4_model4 @ 0x390dc */

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
            

/* slot4_model5 @ 0x391a4 */

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
            

/* slot4_model6 @ 0x3926c */

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
            

/* command @ 0x39334 */

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
        pop {r4-r7, pc}
    

/* boot @ 0x393b8 */
push {r0-r4, lr}
        ldr r0, =0x3b000
        ldr r1, =0x3e080
        movs r2, #0
    clear:
        str r2, [r0], #4
        cmp r0, r1
        blo clear
    ldr r0, =536919360
ldr r1, =229821
str r1, [r0]
ldr r0, =536919364
ldr r1, =230045
str r1, [r0]
ldr r0, =536919676
ldr r1, =230245
str r1, [r0]
ldr r0, =536919680
ldr r1, =230445
str r1, [r0]
ldr r0, =536919684
ldr r1, =230645
str r1, [r0]
ldr r0, =536919688
ldr r1, =230845
str r1, [r0]
ldr r0, =536919692
ldr r1, =231045
str r1, [r0]
ldr r0, =536919696
ldr r1, =231245
str r1, [r0]
ldr r0, =536919700
ldr r1, =231469
str r1, [r0]
ldr r0, =536919704
ldr r1, =231669
str r1, [r0]
ldr r0, =536919708
ldr r1, =231869
str r1, [r0]
ldr r0, =536919712
ldr r1, =232069
str r1, [r0]
ldr r0, =536919716
ldr r1, =232269
str r1, [r0]
ldr r0, =536919720
ldr r1, =232469
str r1, [r0]
ldr r0, =536919724
ldr r1, =232669
str r1, [r0]
ldr r0, =536918896
ldr r1, =232869
str r1, [r0]
ldr r0, =536918900
ldr r1, =233069
str r1, [r0]
ldr r0, =536918904
ldr r1, =233269
str r1, [r0]
ldr r0, =536918908
ldr r1, =233493
str r1, [r0]
ldr r0, =536918912
ldr r1, =233693
str r1, [r0]
ldr r0, =536918916
ldr r1, =233893
str r1, [r0]
ldr r0, =536918920
ldr r1, =234093
str r1, [r0]
ldr r0, =536941297
ldr r1, =234293
str r1, [r0]
ldr r0, =536941301
ldr r1, =234293
str r1, [r0]
pop {r0-r4, lr}
b.w 0x76fc

