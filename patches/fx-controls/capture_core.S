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
bl       #0x13f84
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
bl       #0x13f84
mov      r1, r4
add.w    r0, r7, #0x6c
add      sp, #0x14
movs     r2, #8
vmov.f32 s0, #1.000000e+00
pop.w    {r4, r5, r6, r7, lr}
b.w      #0x8560
