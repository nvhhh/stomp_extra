"""Quick structural survey of a NUX DFU firmware image."""
import math, re, struct, sys, zlib, collections

data = open(sys.argv[1], "rb").read()
print(f"size {len(data)} (0x{len(data):x})")
magic, size, cnt, crc = struct.unpack_from("<8sIII", data, 0)
print("magic", magic, "hdr size", hex(size), "field@0c", cnt, "field@10", hex(crc))

# Try CRC32 over plausible ranges
for start in (0, 0x14, 0x20, 0x100, 0x200, 0x400, 0x1000):
    for end in (len(data),):
        c = zlib.crc32(data[start:end]) & 0xFFFFFFFF
        if c == crc:
            print(f"  CRC32 matches range [{start:#x}:{end:#x}]")
    # crc with the crc field zeroed
z = bytearray(data); z[0x10:0x14] = b"\0\0\0\0"
if zlib.crc32(z) & 0xFFFFFFFF == crc:
    print("  CRC32 matches whole file with crc field zeroed")

# Non-zero spans in the first 64KiB (header / section table)
print("\nnon-zero dwords in first 0x2000 bytes:")
for off in range(0, 0x2000, 4):
    v = struct.unpack_from("<I", data, off)[0]
    if v and not (0x14 <= off < 0x24) and not (0x114 <= off < 0x11c):
        print(f"  {off:#06x}: {v:#010x}  {data[off:off+4]!r}")

def entropy(b):
    if not b: return 0
    c = collections.Counter(b); n = len(b)
    return -sum(v / n * math.log2(v / n) for v in c.values())

print("\nentropy map (64 KiB blocks), F=ff-fill 0=zero-fill:")
row = []
for i in range(0, len(data), 0x10000):
    blk = data[i:i + 0x10000]
    if blk.count(0xFF) == len(blk): row.append("F")
    elif blk.count(0) == len(blk): row.append("0")
    else: row.append(str(min(9, int(entropy(blk)))))
for i in range(0, len(row), 64):
    print(f"  {i * 0x10000:#09x}: {''.join(row[i:i + 64])}")

# ASCII strings
strs = [(m.start(), m.group().decode()) for m in re.finditer(rb"[\x20-\x7e]{8,}", data)]
print(f"\n{len(strs)} strings >= 8 chars; first 80:")
for off, s in strs[:80]:
    print(f"  {off:#09x} {s[:100]}")
