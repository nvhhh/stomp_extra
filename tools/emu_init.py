"""Run the master app's IAR data-init routine in Unicorn and dump the initialized RAM.

usage: emu_init.py <master.bin> <outdir>
Writes <outdir>/ram_<base>.bin for every RAM region that received data.
"""
import sys
from pathlib import Path

from unicorn import (UC_ARCH_ARM, UC_HOOK_MEM_UNMAPPED, UC_MODE_MCLASS, UC_MODE_THUMB, Uc,
                     UcError)
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_SP

INIT = 0x30640
REGIONS = {  # base: size
    0x00000000: 0x80000,    # ITCM (app image)
    0x20000000: 0x80000,    # DTCM
    0x20200000: 0x100000,   # OCRAM
    0x80000000: 0x2000000,  # SEMC SDRAM
}
STOP = 0x0007FFF0


def initialize(img):
    """Strict startup emulation: never create memory in response to an invalid access."""
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
    for base, size in REGIONS.items():
        uc.mem_map(base, size)
    uc.mem_write(0, img)
    uc.reg_write(UC_ARM_REG_SP, 0x2003B000)
    uc.reg_write(UC_ARM_REG_LR, STOP | 1)
    uc.emu_start(INIT | 1, STOP, count=50_000_000)
    if uc.reg_read(UC_ARM_REG_PC) != STOP:
        raise RuntimeError('firmware data initialization did not return')
    return uc


def main():
    img = Path(sys.argv[1]).read_bytes()
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
    for base, size in REGIONS.items():
        uc.mem_map(base, size)
    uc.mem_write(0, img)
    uc.mem_write(STOP, b"\x00\xbf\x00\xbf")            # nop; nop (we stop on reaching it)
    touched = []

    def unmapped(uc, access, addr, size, value, _):
        page = addr & ~0xFFF
        touched.append(addr)
        uc.mem_map(page, 0x1000)
        return True
    uc.hook_add(UC_HOOK_MEM_UNMAPPED, unmapped)
    uc.reg_write(UC_ARM_REG_SP, 0x2003B000)
    uc.reg_write(UC_ARM_REG_LR, STOP | 1)
    try:
        uc.emu_start(INIT | 1, STOP, count=50_000_000)
    except UcError as e:
        print("emulation stopped:", e, "pc", hex(uc.reg_read(UC_ARM_REG_PC)))
    print("finished at pc", hex(uc.reg_read(UC_ARM_REG_PC)), "unmapped accesses:", [hex(a) for a in touched[:8]])
    for base, size in REGIONS.items():
        if base == 0:
            continue
        data = bytes(uc.mem_read(base, size))
        used = len(data.rstrip(b"\0"))
        if used:
            (out / f"ram_{base:08x}.bin").write_bytes(data[:used])
            print(f"region {base:#010x}: {used:#x} bytes initialized")


if __name__ == "__main__":
    main()
