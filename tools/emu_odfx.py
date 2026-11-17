"""Emulate the 16 OD/FX model functions and measure the state memory they touch.

usage: emu_odfx.py <master.bin> <ram_20000000.bin>
Runs table[k](in, out, obj+0x78, obj+0x98, obj+4, 0) for a few blocks with varying params and
reports the address extents used inside the A (0x2003E000) and B (0x20200000) state regions.
"""
import struct
import sys
from pathlib import Path

from unicorn import (UC_ARCH_ARM, UC_HOOK_MEM_READ, UC_HOOK_MEM_UNMAPPED, UC_HOOK_MEM_WRITE,
                     UC_MODE_MCLASS, UC_MODE_THUMB, Uc, UcError)
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
                               UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP)

OBJ = 0x2000BC10           # OD/FX module object
TABLE = OBJ + 0x38
A, B = 0x2003E000, 0x20200000
STOP = 0x0007FFF0
NAMES = ["Red Comp", "RS Comp", "Yellow Dist", "Boost RC", "Boost AC", "DS1", "TS9", "BD2",
         "Klone", "Ratt2", "Red Drive", "Cruncher", "Muff", "Boost", "Face Fuzz", "ST Drive"]


def make(img, ram):
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
    for base, size in ((0, 0x80000), (0x20000000, 0x80000), (0x20200000, 0x100000), (0x80000000, 0x2000000)):
        uc.mem_map(base, size)
    uc.mem_write(0, img)
    uc.mem_write(0x20000000, ram)
    uc.mem_write(STOP, b"\x00\xbf\x00\xbf")

    def unmapped(uc, access, addr, size, value, _):
        uc.mem_map(addr & ~0xFFF, 0x1000)
        return True
    uc.hook_add(UC_HOOK_MEM_UNMAPPED, unmapped)
    return uc


def main():
    img = Path(sys.argv[1]).read_bytes()
    ram = Path(sys.argv[2]).read_bytes()
    table = struct.unpack_from("<16I", ram, TABLE - 0x20000000)
    IN, OUT, STK = 0x20070000, 0x20071000, 0x2007F000
    worst = {"A": 0, "B": 0}
    for k, fn in enumerate(table):
        uc = make(img, ram)
        touched = {"A": [None, None], "B": [None, None]}

        def hook(uc, access, addr, size, value, _):
            for nm, base, lim in (("A", A, 0x1000), ("B", B, 0x8000)):
                if base <= addr < base + lim:
                    t = touched[nm]
                    t[0] = addr if t[0] is None else min(t[0], addr)
                    t[1] = addr + size if t[1] is None else max(t[1], addr + size)
        uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, hook, begin=A, end=A + 0x1000)
        uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, hook, begin=B, end=B + 0x8000)
        sig = [0.3 * ((i * 37 % 17) - 8) / 8 for i in range(64)]
        uc.mem_write(IN, struct.pack("<64f", *sig))
        err = None
        for blk in range(24):
            # obj+4.. : flag, ?, model, params...
            p = [(blk * 13 + j * 29) % 101 for j in range(4)]
            uc.mem_write(OBJ + 4, bytes([blk & 0xFF, 0, k] + p))
            uc.mem_write(OBJ, bytes([k, k]))
            sp = STK - 0x40
            uc.mem_write(sp, struct.pack("<II", OBJ + 4, 0))
            for reg, v in ((UC_ARM_REG_R0, IN), (UC_ARM_REG_R1, OUT), (UC_ARM_REG_R2, OBJ + 0x78),
                           (UC_ARM_REG_R3, OBJ + 0x98), (UC_ARM_REG_SP, sp), (UC_ARM_REG_LR, STOP | 1)):
                uc.reg_write(reg, v)
            try:
                uc.emu_start(fn | 1, STOP, count=3_000_000)
            except UcError as e:
                err = f"{e} @ {uc.reg_read(UC_ARM_REG_PC):#x}"
                break
        a, b = touched["A"], touched["B"]
        ua = (a[1] - A) if a[1] else 0
        ub = (b[1] - B) if b[1] else 0
        worst["A"], worst["B"] = max(worst["A"], ua), max(worst["B"], ub)
        print(f"{k:2d} {NAMES[k]:12s} fn={fn:#07x}  A used up to +{ua:#06x}   B used up to +{ub:#06x}"
              + (f"   ERROR {err}" if err else ""))
    print(f"worst case: A {worst['A']:#x} bytes, B {worst['B']:#x} bytes")


if __name__ == "__main__":
    main()
