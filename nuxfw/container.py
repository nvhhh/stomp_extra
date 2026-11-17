"""NUX DFU firmware container (Soran Dual Stomp / Dual Stomp Lite / Tiny Stomp).

File layout (all little-endian unless noted)::

    0x000  8s   magic  "NUX DFU\\x02"
    0x008  u32  total file size
    0x00C  u32  format field (2 on all known files) -- preserved verbatim
    0x010  u16  DFU-mode USB VID (0x9527)   u16 DFU-mode USB PID (0xC157)
    0x014  str  device name  "JME STOMPBOX DFU"   (shown by the updater)
    0x114  str  vendor       "SORAN"
    0x214  str  version      "V1.1.0.x"
    0x224  section table, 12-byte entries {tag[4], size u32, offset u32}:
             TEXT  release notes (UTF-8, [en]..[/en] markup)
             BINA  the DFU record stream that is sent verbatim to the bootloader
             EXTR  256 reserved bytes
    0x3BC  BINA data (by convention)

BINA is a sequence of 0x21C-byte records = 0x1C header + 0x200 payload.
Record header::

    +0x00 u8      progress percent shown on the pedal (1..100)
    +0x02 u16 BE  command: 1 = session info, 2 = config sector @0x60010000,
                  4 = main flash @0x60040000
    +0x0C u32 BE  block index (0..N-1), 0xFFFFFFFF = final block

Info record payload (command 1)::

    +0x00  ~"AE-100X"   bitwise-inverted device id the bootloader requires
    +0x08  ~version     12 bytes, bitwise-inverted
    +0x14  u32 BE  (bootloader reads it, 0 in stock)
    +0x18  u32 BE  total payload bytes incl. the final block
    +0x1C  u32 BE  (bootloader reads it, 0 in stock)
"""
from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field

MAGIC = b"NUX DFU\x02"
REC_SIZE = 0x21C
REC_HDR = 0x1C
BLOCK = 0x200
END_INDEX = 0xFFFFFFFF
DEVICE_ID = b"AE-100X"

CMD_INFO = 1
CMD_CONFIG = 2
CMD_MAIN = 4

SECTION_TABLE = 0x224
SECTION_SLOTS = (SECTION_TABLE + 0x00, SECTION_TABLE + 0x0C, SECTION_TABLE + 0x18)
BINA_OFFSET = 0x3BC


class FormatError(ValueError):
    pass


def _inv(b: bytes) -> bytes:
    return bytes(x ^ 0xFF if x else 0 for x in b)


def _cstr(b: bytes) -> str:
    return b.split(b"\0", 1)[0].decode("latin-1")


def progress_byte(i: int, total: int) -> int:
    """Progress percentage NUX tools put in byte 0 of the i-th main-flash record.

    Reproduces the stock files exactly: data records count 1..99, the final record is 100.
    """
    return -(-99 * (i + 1) // total)  # ceil(99 * (i + 1) / total)


@dataclass
class Record:
    cmd: int
    index: int
    payload: bytes
    progress: int = 0

    def encode(self) -> bytes:
        hdr = bytearray(REC_HDR)
        hdr[0] = self.progress
        struct.pack_into(">H", hdr, 2, self.cmd)
        struct.pack_into(">I", hdr, 0x0C, self.index)
        if len(self.payload) != BLOCK:
            raise FormatError("record payload must be 512 bytes")
        return bytes(hdr) + self.payload

    @classmethod
    def decode(cls, raw: bytes) -> "Record":
        if len(raw) != REC_SIZE:
            raise FormatError("short record")
        hdr = raw[:REC_HDR]
        known = {0, 2, 3, 0x0C, 0x0D, 0x0E, 0x0F}
        if any(hdr[i] for i in range(REC_HDR) if i not in known):
            raise FormatError(f"unexpected bytes in record header: {hdr.hex()}")
        return cls(
            cmd=struct.unpack_from(">H", hdr, 2)[0],
            index=struct.unpack_from(">I", hdr, 0x0C)[0],
            payload=raw[REC_HDR:],
            progress=hdr[0],
        )


@dataclass
class Firmware:
    header: bytes                # bytes 0x000..0x224 (magic, ids, strings) kept verbatim
    notes: bytes                 # TEXT section
    extra: bytes                 # EXTR section
    info: bytes                  # info record payload (512 bytes)
    image: bytes                 # flat main-flash image, written at 0x60040000
    final: bytes                 # payload of the 0xFFFFFFFF block (512 bytes)
    info_progress: int = 1
    progress: list[int] = field(default_factory=list)  # per main record, preserved if unchanged

    # ---- convenience accessors -------------------------------------------------
    @property
    def dfu_vid_pid(self) -> tuple[int, int]:
        return struct.unpack_from("<HH", self.header, 0x10)

    @property
    def device_name(self) -> str:
        return _cstr(self.header[0x14:0x114])

    @property
    def vendor(self) -> str:
        return _cstr(self.header[0x114:0x214])

    @property
    def version(self) -> str:
        return _cstr(self.header[0x214:0x224])

    @property
    def device_id(self) -> str:
        return _cstr(_inv(self.info[0:8]))

    @property
    def info_version(self) -> str:
        return _cstr(_inv(self.info[8:0x14]))

    @property
    def notes_text(self) -> str:
        return self.notes.decode("utf-8", "replace")

    # ---- parse -----------------------------------------------------------------
    @classmethod
    def parse(cls, data: bytes) -> "Firmware":
        if data[:8] != MAGIC:
            raise FormatError("not a NUX DFU file (bad magic)")
        size = struct.unpack_from("<I", data, 8)[0]
        if size != len(data):
            raise FormatError(f"size field {size:#x} != file size {len(data):#x}")

        sections = {}
        for off in SECTION_SLOTS:
            tag = data[off:off + 4]
            if tag == b"\0\0\0\0":
                continue
            sz, so = struct.unpack_from("<II", data, off + 4)
            if so + sz > len(data):
                raise FormatError(f"section {tag!r} out of bounds")
            sections[tag] = data[so:so + sz]
        for need in (b"TEXT", b"BINA", b"EXTR"):
            if need not in sections:
                raise FormatError(f"missing section {need!r}")

        bina = sections[b"BINA"]
        if len(bina) % REC_SIZE:
            raise FormatError("BINA is not a whole number of records")
        recs = [Record.decode(bina[i:i + REC_SIZE]) for i in range(0, len(bina), REC_SIZE)]

        if not recs or recs[0].cmd != CMD_INFO:
            raise FormatError("BINA must start with an info record")
        info = recs[0]
        if _inv(info.payload[:len(DEVICE_ID)]) != DEVICE_ID:
            raise FormatError(f"info record device id is {_inv(info.payload[:8])!r}, expected {DEVICE_ID!r}")

        body = recs[1:]
        if not body or body[-1].index != END_INDEX:
            raise FormatError("stream must end with a 0xFFFFFFFF block")
        for n, r in enumerate(body[:-1]):
            if r.cmd != CMD_MAIN:
                raise FormatError(f"record {n + 1}: command {r.cmd} not supported (only main-flash images)")
            if r.index != n:
                raise FormatError(f"record {n + 1}: index {r.index} != {n}")
        if body[-1].cmd != CMD_MAIN:
            raise FormatError("final record is not a main-flash record")

        declared = struct.unpack_from(">I", info.payload, 0x18)[0]
        if declared != len(body) * BLOCK:
            raise FormatError(f"info size {declared:#x} != streamed {len(body) * BLOCK:#x}")

        return cls(
            header=data[:SECTION_TABLE],
            notes=sections[b"TEXT"],
            extra=sections[b"EXTR"],
            info=info.payload,
            image=b"".join(r.payload for r in body[:-1]),
            final=body[-1].payload,
            info_progress=info.progress,
            progress=[r.progress for r in body],
        )

    # ---- build -----------------------------------------------------------------
    def records(self) -> list[Record]:
        if len(self.image) % BLOCK:
            raise FormatError("image length must be a multiple of 512")
        nblocks = len(self.image) // BLOCK
        total = nblocks + 1
        info = bytearray(self.info)
        struct.pack_into(">I", info, 0x18, total * BLOCK)
        keep = len(self.progress) == total
        out = [Record(CMD_INFO, 0, bytes(info), self.info_progress)]
        for i in range(nblocks):
            p = self.progress[i] if keep else progress_byte(i, total)
            out.append(Record(CMD_MAIN, i, self.image[i * BLOCK:(i + 1) * BLOCK], p))
        out.append(Record(CMD_MAIN, END_INDEX, self.final, self.progress[-1] if keep else 100))
        return out

    def build(self) -> bytes:
        bina = b"".join(r.encode() for r in self.records())
        hdr = bytearray(self.header)
        out = bytearray(hdr) + bytes(BINA_OFFSET - SECTION_TABLE)
        text_off = BINA_OFFSET + len(bina)
        extr_off = text_off + len(self.notes)
        table = (b"TEXT", len(self.notes), text_off), (b"BINA", len(bina), BINA_OFFSET), (b"EXTR", len(self.extra), extr_off)
        for slot, (tag, sz, so) in zip(SECTION_SLOTS, table):
            out[slot:slot + 12] = tag + struct.pack("<II", sz, so)
        out += bina + self.notes + self.extra
        struct.pack_into("<I", out, 8, len(out))
        return bytes(out)

    def with_image(self, image: bytes) -> "Firmware":
        f = Firmware(**{**self.__dict__})
        f.image = image
        if len(image) != len(self.image):
            f.progress = []
        return f

    def summary(self) -> dict:
        vid, pid = self.dfu_vid_pid
        return {
            "device_name": self.device_name,
            "vendor": self.vendor,
            "header_version": self.version,
            "device_id": self.device_id,
            "info_version": self.info_version,
            "dfu_usb_id": f"{vid:04x}:{pid:04x}",
            "image_bytes": len(self.image),
            "image_sha256": hashlib.sha256(self.image).hexdigest(),
            "records": len(self.records()),
        }
