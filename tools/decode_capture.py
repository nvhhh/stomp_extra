"""Turn a smcapture JSONL log into a MIDI timeline.

usage: decode_capture.py <capture.jsonl> [out.jsonl]

Unwraps Flutter StandardMessageCodec (universal_ble pigeon writeValue / onValueChanged),
reassembles BLE-MIDI packets into complete MIDI messages (SysEx and short messages), and also
includes WinMM-driver records. Output lines: {"t", "dir": "host"|"dev", "hex"}.
"""
import json
import struct
import sys


class Codec:
    """Minimal Flutter StandardMessageCodec reader (enough for pigeon BLE messages)."""

    def __init__(self, b: bytes):
        self.b, self.i = b, 0

    def size(self):
        n = self.b[self.i]; self.i += 1
        if n < 254:
            return n
        if n == 254:
            v = struct.unpack_from("<H", self.b, self.i)[0]; self.i += 2
            return v
        v = struct.unpack_from("<I", self.b, self.i)[0]; self.i += 4
        return v

    def align(self, n):
        self.i += (-self.i) % n

    def value(self):
        t = self.b[self.i]; self.i += 1
        if t == 0: return None
        if t in (1, 2): return t == 1
        if t == 3:
            v = struct.unpack_from("<i", self.b, self.i)[0]; self.i += 4; return v
        if t == 4:
            v = struct.unpack_from("<q", self.b, self.i)[0]; self.i += 8; return v
        if t == 6:
            self.align(8); v = struct.unpack_from("<d", self.b, self.i)[0]; self.i += 8; return v
        if t in (5, 7):
            n = self.size(); v = self.b[self.i:self.i + n].decode("utf-8", "replace"); self.i += n; return v
        if t == 8:
            n = self.size(); v = bytes(self.b[self.i:self.i + n]); self.i += n; return v
        if t in (9, 14):
            n = self.size(); self.align(4); self.i += 4 * n; return None
        if t in (10, 11):
            n = self.size(); self.align(8); self.i += 8 * n; return None
        if t == 12:
            return [self.value() for _ in range(self.size())]
        if t == 13:
            return {self.value(): self.value() for _ in range(self.size())}
        if t >= 128:  # pigeon custom class: encoded as a list
            return self.value()
        raise ValueError(f"codec type {t}")


def first_bytes(v):
    if isinstance(v, (bytes, bytearray)):
        return v
    if isinstance(v, list):
        for x in v:
            r = first_bytes(x)
            if r is not None:
                return r
    if isinstance(v, dict):
        for x in v.values():
            r = first_bytes(x)
            if r is not None:
                return r
    return None


class BleMidi:
    """BLE-MIDI packet -> MIDI messages, keeping SysEx state across packets."""

    def __init__(self):
        self.sysex = None
        self.running = None

    def feed(self, pkt: bytes):
        out = []
        if len(pkt) < 2 or not pkt[0] & 0x80:
            return out
        i = 1
        while i < len(pkt):
            b = pkt[i]
            if self.sysex is not None:
                if b & 0x80:
                    # timestamp byte; next byte F7 ends sysex, or a real-time/other status
                    if i + 1 < len(pkt) and pkt[i + 1] == 0xF7:
                        self.sysex.append(0xF7); out.append(bytes(self.sysex)); self.sysex = None; i += 2
                        continue
                    i += 1
                    continue
                self.sysex.append(b); i += 1
                continue
            if b & 0x80:  # timestamp
                i += 1
                if i >= len(pkt):
                    break
                st = pkt[i]
                if st == 0xF0:
                    self.sysex = bytearray([0xF0]); i += 1
                    continue
                if st & 0x80:
                    self.running = st; i += 1
            # data bytes for running status
            st = self.running
            if st is None:
                i += 1; continue
            n = 1 if 0xC0 <= st < 0xE0 else 2
            data = pkt[i:i + n]
            out.append(bytes([st]) + data)
            i += n
        return out


def main():
    recs = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8")]
    host, dev = BleMidi(), BleMidi()
    out = []
    for r in recs:
        ch = r.get("ch", "")
        raw = bytes.fromhex(r.get("hex", "")) if r.get("hex") else b""
        if ch == "drv" and raw:
            out.append({"t": r["t"], "dir": "host" if r["dir"] == "out" else "dev", "hex": raw.hex()})
        elif ch.endswith("writeValue") and r["dir"] == "d2n" and raw:
            pkt = first_bytes(Codec(raw).value())
            for m in host.feed(pkt or b""):
                out.append({"t": r["t"], "dir": "host", "hex": m.hex()})
        elif ch.endswith("onValueChanged") and raw:
            pkt = first_bytes(Codec(raw).value())
            for m in dev.feed(pkt or b""):
                out.append({"t": r["t"], "dir": "dev", "hex": m.hex()})
    dst = open(sys.argv[2], "w") if len(sys.argv) > 2 else sys.stdout
    for o in out:
        dst.write(json.dumps(o) + "\n")
    if len(sys.argv) > 2:
        print(f"{len(out)} MIDI messages -> {sys.argv[2]}")


if __name__ == "__main__":
    main()
