"""Linear-sweep Thumb-2 disassembly of a raw Cortex-M image with literal-pool annotation.

usage: disasm.py <image> <base> <start> <end> [out]
Annotates `ldr rX, [pc, #n]` with the loaded constant and, if it points into the image,
the ASCII string there.
"""
import re, struct, sys
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS

img = open(sys.argv[1], "rb").read()
base, start, end = (int(x, 0) for x in sys.argv[2:5])
out = open(sys.argv[5], "w") if len(sys.argv) > 5 else sys.stdout
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
md.detail = False

def cstr(addr):
    o = addr - base
    if 0 <= o < len(img):
        m = re.match(rb"[\x20-\x7e]{4,}", img[o:o + 80])
        if m:
            return m.group().decode()
    return None

off = start
while off < end:
    progressed = False
    for ins in md.disasm(img[off:end], base + off):
        note = ""
        m = re.match(r"(\w+), \[pc, #(-?0x[0-9a-f]+|-?\d+)\]", ins.op_str)
        if ins.mnemonic.startswith("ldr") and m:
            lit = ((ins.address + 4) & ~3) + int(m.group(2), 0)
            lo = lit - base
            if 0 <= lo + 4 <= len(img):
                v = struct.unpack_from("<I", img, lo)[0]
                s = cstr(v)
                note = f"  ; ={v:#010x}" + (f' "{s}"' if s else "")
        out.write(f"{ins.address:08x}: {ins.bytes.hex():<10} {ins.mnemonic:<8} {ins.op_str}{note}\n")
        off = ins.address - base + ins.size
        progressed = True
    if not progressed or off < end:
        out.write(f"{base + off:08x}: {img[off:off + 2].hex():<10} .short\n")
        off += 2
