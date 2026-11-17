"""Walk the BINA record stream of a NUX DFU image and summarise it."""
import struct, sys, collections

d = open(sys.argv[1], "rb").read()
REC, HDR = 0x21C, 0x1C
bina_size, bina_off = struct.unpack_from("<II", d, 0x234)
end = bina_off + bina_size
print(f"BINA {bina_off:#x}..{end:#x}  ({bina_size} bytes, {bina_size / REC:.3f} records)")

off = bina_off
runs = []  # (hdrkey, first_off, count, first_hdr, last_hdr)
while off + HDR <= end:
    h = d[off:off + HDR]
    key = (h[0], h[1], h[2], h[3])
    if runs and runs[-1][0] == key:
        runs[-1][2] += 1; runs[-1][4] = h
    else:
        runs.append([key, off, 1, h, h])
    off += REC
print(f"stream ends at {off:#x} (BINA end {end:#x}), leftover {end - (off - REC) - REC}")
for key, o, n, h0, h1 in runs:
    print(f"{o:#09x} tag={bytes(key).hex()} n={n:6d}  first={h0[4:].hex()}  last={h1[4:].hex()}")
