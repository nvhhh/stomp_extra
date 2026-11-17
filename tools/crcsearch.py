"""Brute-force common CRC/checksum variants against the two unknown NUX DFU check values."""
import struct, sys, zlib

def make_crc(width, poly, init, refin, refout, xorout):
    mask = (1 << width) - 1
    table = []
    for i in range(256):
        if refin:
            rpoly = int(f"{poly:0{width}b}"[::-1], 2)
            c = i
            for _ in range(8):
                c = (c >> 1) ^ rpoly if c & 1 else c >> 1
        else:
            c = i << (width - 8)
            for _ in range(8):
                c = ((c << 1) ^ poly) & mask if c & (1 << (width - 1)) else (c << 1) & mask
        table.append(c)

    def run(data):
        c = int(f"{init:0{width}b}"[::-1], 2) if refin else init
        if refin:
            for b in data:
                c = (c >> 8) ^ table[(c ^ b) & 0xFF]
        else:
            sh = width - 8
            for b in data:
                c = ((c << 8) & mask) ^ table[((c >> sh) ^ b) & 0xFF]
        if refin != refout:
            c = int(f"{c:0{width}b}"[::-1], 2)
        return c ^ xorout
    return run

CRC16 = {
    "ARC": (0x8005, 0, True, True, 0), "MODBUS": (0x8005, 0xFFFF, True, True, 0),
    "USB": (0x8005, 0xFFFF, True, True, 0xFFFF), "BUYPASS": (0x8005, 0, False, False, 0),
    "CCITT-FALSE": (0x1021, 0xFFFF, False, False, 0), "XMODEM": (0x1021, 0, False, False, 0),
    "KERMIT": (0x1021, 0, True, True, 0), "X25": (0x1021, 0xFFFF, True, True, 0xFFFF),
    "MCRF4XX": (0x1021, 0xFFFF, True, True, 0), "GENIBUS": (0x1021, 0xFFFF, False, False, 0xFFFF),
}
CRC32 = {
    "ISO-HDLC": (0x04C11DB7, 0xFFFFFFFF, True, True, 0xFFFFFFFF),
    "BZIP2": (0x04C11DB7, 0xFFFFFFFF, False, False, 0xFFFFFFFF),
    "MPEG-2": (0x04C11DB7, 0xFFFFFFFF, False, False, 0),
    "POSIX": (0x04C11DB7, 0, False, False, 0xFFFFFFFF),
    "JAMCRC": (0x04C11DB7, 0xFFFFFFFF, True, True, 0),
    "C(Castagnoli)": (0x1EDC6F41, 0xFFFFFFFF, True, True, 0xFFFFFFFF),
}

d = open(sys.argv[1], "rb").read()
REC = 0x21C
first_data, end_rec = 0x5D8, 0xF6ADFC
flat = b"".join(d[o + 0x1C:o + REC] for o in range(first_data, end_rec, REC))
hdr_val = struct.unpack_from("<I", d, 0x10)[0]
end_val_be = struct.unpack_from(">H", d, end_rec + 0x1C + 510)[0]
targets16 = {end_val_be, ((end_val_be & 0xFF) << 8) | (end_val_be >> 8)}
print(f"targets: hdr32={hdr_val:#010x}  end16={[hex(t) for t in targets16]}")

ranges = {
    "flat": flat,
    "flat+endpayload(510)": flat + d[end_rec + 0x1C:end_rec + 0x1C + 510],
    "bina-all": d[0x3BC:0xF6B018],
    "bina-data-recs": d[first_data:end_rec],
    "bina-before-end": d[0x3BC:end_rec],
    "file[0x14:]": d[0x14:],
    "file[0x14:bina_end]": d[0x14:0xF6B018],
    "file[0x200:]": d[0x200:],
    "file[0x3bc:]": d[0x3BC:],
}
zero = bytearray(d); zero[0x10:0x14] = b"\0\0\0\0"; ranges["file-crc-zeroed"] = bytes(zero)
ffed = bytearray(d); ffed[0x10:0x14] = b"\xff" * 4; ranges["file-crc-ff"] = bytes(ffed)

for name, data in ranges.items():
    s = sum(data)
    for t in targets16:
        if s & 0xFFFF == t: print(f"MATCH sum16 over {name} = {t:#x}")
    if s & 0xFFFFFFFF == hdr_val: print(f"MATCH sum32 over {name}")
    if (-s) & 0xFFFF in targets16: print(f"MATCH neg-sum16 over {name}")

for name in ("flat", "flat+endpayload(510)", "bina-data-recs", "bina-before-end"):
    for cname, p in CRC16.items():
        v = make_crc(16, *p)(ranges[name])
        if v in targets16: print(f"MATCH CRC16/{cname} over {name} = {v:#06x}")
    print("  crc16 done", name, flush=True)

for name, data in ranges.items():
    for cname, p in CRC32.items():
        v = zlib.crc32(data) if cname == "ISO-HDLC" else make_crc(32, *p)(data)
        if v == hdr_val: print(f"MATCH CRC32/{cname} over {name}")
    print("  crc32 done", name, flush=True)
