"""Compile the freestanding DSP kernel into verified empty ITCM space."""
from pathlib import Path
import json, math, subprocess

def build(root):
    source=Path(__file__).with_name('capture_partitioned.c')
    out=root/'work/partition-kernel';out.mkdir(exist_ok=True)
    llvm=Path('C:/Program Files/LLVM/bin')
    vals=[v for k in range(32) for v in (math.cos(2*math.pi*k/64),-math.sin(2*math.pi*k/64))]
    (out/'capture_twiddle.h').write_text('static const float twiddle[64]={'+','.join(f'{v:.17e}f' for v in vals)+'};\n')
    asm='''.syntax unified
.thumb
.text
.global partition_head8
.type partition_head8,%function
.thumb_func
partition_head8:
push {r4,lr}
vpush {d8}
add r3,r0,#252
add r0,r0,#256
vldmia r0,{s0-s7}
movs r0,#0
'''
    for i in range(8,16): asm+=f'vmov s{i},r0\n'
    asm+='movs r4,#8\n1:\n'
    for k in range(8):
        asm+='vldmia r1!,{s16}\n'
        for j in range(8):asm+=f'vmla.f32 s{8+j},s{(j-k)%8},s16\n'
        asm+=f'vldr s{(7-k)%8},[r3]\nsub r3,r3,#4\n'
    asm+='subs r4,r4,#1\nbne 1b\nvstmia r2,{s8-s15}\nvpop {d8}\npop {r4,pc}\n'
    asm+='''.global partition_cmac
.type partition_cmac,%function
.thumb_func
partition_cmac:
vldmia r0,{s0-s1}
vldmia r1!,{s2-s3}
vldmia r2!,{s4-s5}
vmla.f32 s0,s2,s4
vmla.f32 s1,s2,s5
vmls.f32 s0,s3,s5
vmla.f32 s1,s3,s4
vstmia r0!,{s0-s1}
movs r3,#15
2:
vldmia r0,{s0-s3}
vldmia r1!,{s4-s7}
vldmia r2!,{s8-s11}
vmla.f32 s0,s4,s8
vmla.f32 s1,s4,s9
vmla.f32 s2,s6,s10
vmla.f32 s3,s6,s11
vmls.f32 s0,s5,s9
vmla.f32 s1,s5,s8
vmls.f32 s2,s7,s11
vmla.f32 s3,s7,s10
vstmia r0!,{s0-s3}
subs r3,r3,#1
bne 2b
bx lr
'''
    (out/'head.S').write_text(asm)
    script=out/'kernel.ld'
    script.write_text('ENTRY(partition_init)\nSECTIONS { . = 0x36d10; .text : { *(.text*) *(.rodata*) } /DISCARD/ : { *(.ARM.exidx*) *(.comment*) *(.ARM.attributes*) } }')
    subprocess.run([str(llvm/'clang.exe'),'--target=arm-none-eabi','-mcpu=cortex-m7','-mthumb',
        '-mfpu=fpv4-sp-d16','-mfloat-abi=hard','-O2','-fno-unroll-loops','-ffreestanding','-fno-builtin',
        '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-ffp-contract=off',
        '-I',str(out),'-c',str(source),'-o',str(out/'kernel.o')],check=True)
    subprocess.run([str(llvm/'clang.exe'),'--target=arm-none-eabi','-mcpu=cortex-m7','-mthumb',
        '-c',str(out/'head.S'),'-o',str(out/'head.o')],check=True)
    subprocess.run([str(llvm/'ld.lld.exe'),'-T',str(script),str(out/'kernel.o'),str(out/'head.o'),'-o',str(out/'kernel.elf')],check=True)
    subprocess.run([str(llvm/'llvm-objcopy.exe'),'-O','binary',str(out/'kernel.elf'),str(out/'kernel.bin')],check=True)
    nm=subprocess.check_output([str(llvm/'llvm-nm.exe'),'--defined-only',str(out/'kernel.elf')],text=True)
    symbols={line.split()[2]:int(line.split()[0],16) for line in nm.splitlines() if len(line.split())==3}
    data=(out/'kernel.bin').read_bytes()
    assert len(data)<=0x38000-0x36d10, f'partition kernel too large: {len(data)}'
    assert 'partition_core' in symbols and 'partition_init' in symbols
    (out/'symbols.json').write_text(json.dumps(symbols,indent=2))
    return data,symbols
