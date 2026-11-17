"""Patch engine: applies guarded patches to the flat image.

A patch file is TOML::

    name = "example"
    description = "what it does"

    [[op]]
    kind   = "bytes"          # replace bytes; `expect` must match the stock bytes
    slot   = "master"         # region name from nuxfw.layout
    offset = 0x1234           # slot-relative (== runtime address for code slots)
    expect = "00bf 00bf"      # hex, whitespace ignored
    data   = "70 47"

    [[op]]
    kind   = "word"           # 32-bit little-endian word (pointer tables, literals)
    slot = "master"; offset = 0x40; expect = 0x9dd3; value = 0x38101

    [[op]]
    kind   = "blob"           # place a file (e.g. compiled code) into unused space
    slot = "master"; offset = 0x38100; file = "features/build/feature.bin"

    [[op]]
    kind   = "bl"             # rewrite a Thumb-2 BL/BLX at `offset` to call `target`
    slot = "master"; offset = 0x2000; expect = "00f0 10f8"; target = 0x38101

Rules enforced for every op: offsets must lie inside the slot, ops may not overlap,
protected regions (the DFU bootloader, reserved slot tails) are refused unless the
patch sets ``allow_protected = true``, and `blob` targets must currently be blank (all 0x00).
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import struct
import tomllib
import zlib
from dataclasses import dataclass
from pathlib import Path

from . import layout


class PatchError(Exception):
    pass


def _hex(s: str) -> bytes:
    return bytes.fromhex("".join(s.split()))


def encode_bl(at: int, target: int) -> bytes:
    """Encode Thumb-2 `BL target` placed at address `at` (both runtime addresses)."""
    target &= ~1
    off = target - (at + 4)
    if off % 2 or not -(1 << 24) <= off < (1 << 24):
        raise PatchError(f"BL from {at:#x} to {target:#x} out of range")
    s = (off >> 24) & 1
    i1 = (off >> 23) & 1
    i2 = (off >> 22) & 1
    imm10 = (off >> 12) & 0x3FF
    imm11 = (off >> 1) & 0x7FF
    j1 = (~(i1 ^ s)) & 1
    j2 = (~(i2 ^ s)) & 1
    hw1 = 0xF000 | (s << 10) | imm10
    hw2 = 0xD000 | (j1 << 13) | (j2 << 11) | imm11
    return struct.pack("<HH", hw1, hw2)


@dataclass
class Write:
    patch: str
    slot: str
    offset: int
    data: bytes
    expect: bytes | None   # None = must be blank
    allow_protected: bool

    @property
    def flat(self) -> int:
        return layout.region(self.slot).start + self.offset


def load_patch(path: Path) -> tuple[str, str, list[Write]]:
    spec = tomllib.loads(path.read_text(encoding="utf-8"))
    name = spec.get("name") or path.stem
    allow = bool(spec.get("allow_protected", False))
    writes = []
    for n, op in enumerate(spec.get("op", [])):
        kind = op.get("kind")
        slot = op["slot"]
        off = int(op["offset"])
        where = f"{path.name} op#{n} ({kind} {slot}+{off:#x})"
        if kind == "bytes":
            data, expect = _hex(op["data"]), _hex(op["expect"])
            if len(data) != len(expect):
                raise PatchError(f"{where}: data and expect lengths differ")
        elif kind == "word":
            data = struct.pack("<I", int(op["value"]))
            expect = struct.pack("<I", int(op["expect"]))
        elif kind == "blob":
            data = (path.parent / op["file"]).resolve().read_bytes()
            expect = _hex(op["expect"]) if "expect" in op else None
        elif kind == "bl":
            data = encode_bl(off, int(op["target"]))
            expect = _hex(op["expect"])
            if len(expect) != 4:
                raise PatchError(f"{where}: bl expect must be the 4 original bytes")
        else:
            raise PatchError(f"{where}: unknown kind {kind!r}")
        writes.append(Write(name, slot, off, data, expect, allow))
    return name, spec.get("description", ""), writes


def _check_bounds(w: Write, image_len: int) -> None:
    r = next(x for x in layout.regions_for(image_len) if x.name == w.slot)
    if w.offset < 0 or w.offset + len(w.data) > r.size:
        raise PatchError(f"{w.patch}: write {w.slot}+{w.offset:#x} len {len(w.data)} exceeds slot")
    if w.allow_protected:
        return
    if r.protected:
        raise PatchError(f"{w.patch}: slot {w.slot!r} is protected ({r.desc})")
    for slot, lo, hi, why in layout.RESERVED:
        if slot == w.slot and w.offset < hi and w.offset + len(w.data) > lo:
            raise PatchError(f"{w.patch}: {w.slot}+{w.offset:#x} hits reserved range {lo:#x}-{hi:#x} ({why})")


def apply(image: bytes, writes: list[Write]) -> bytes:
    out = bytearray(image)
    spans = []
    for w in writes:
        _check_bounds(w, len(image))
        a, b = w.flat, w.flat + len(w.data)
        for (pa, pb, pw) in spans:
            if a < pb and b > pa:
                raise PatchError(f"{w.patch} overlaps {pw.patch} at flat {max(a, pa):#x}")
        cur = bytes(out[a:b])
        if w.expect is None:
            if any(cur):
                raise PatchError(f"{w.patch}: blob target {w.slot}+{w.offset:#x} is not blank")
        elif cur != w.expect:
            raise PatchError(
                f"{w.patch}: {w.slot}+{w.offset:#x} expected {w.expect.hex()} found {cur.hex()} "
                "(wrong base firmware?)")
        out[a:b] = w.data
        spans.append((a, b, w))
    return bytes(out)


TAG_MAGIC = b"SCFW"
TAG_SIZE = 0x100


def build_tag(cfw_version: str, base_version: str, base_sha: str, patches: list[str],
              when: _dt.datetime | None = None) -> bytes:
    """Build-info block written into unused flash. Pure data; never executed or read by stock code.

    layout: magic[4] fmt u16 size u16 | cfw_version[16] | base_version[16] | built_utc[24]
            | base_image_sha256[32] | n_patches u32 | patch names (NUL separated) ... | crc32 u32 (last 4)
    """
    when = when or _dt.datetime.now(_dt.timezone.utc)
    blk = bytearray(TAG_SIZE)
    blk[0:4] = TAG_MAGIC
    struct.pack_into("<HH", blk, 4, 1, TAG_SIZE)
    for off, ln, s in ((0x08, 16, cfw_version), (0x18, 16, base_version),
                       (0x28, 24, when.strftime("%Y-%m-%dT%H:%M:%SZ"))):
        enc = s.encode()[:ln - 1]
        blk[off:off + len(enc)] = enc
    blk[0x40:0x60] = bytes.fromhex(base_sha)
    struct.pack_into("<I", blk, 0x60, len(patches))
    names = b"\0".join(p.encode() for p in patches)[:TAG_SIZE - 0x64 - 5]
    blk[0x64:0x64 + len(names)] = names
    struct.pack_into("<I", blk, TAG_SIZE - 4, zlib.crc32(blk[:TAG_SIZE - 4]))
    return bytes(blk)


def read_tag(image: bytes) -> dict | None:
    slot, off = "master", layout.FREE["master"][0]
    a = layout.region(slot).start + off
    blk = image[a:a + TAG_SIZE]
    if blk[:4] != TAG_MAGIC:
        return None
    ok = zlib.crc32(blk[:TAG_SIZE - 4]) == struct.unpack_from("<I", blk, TAG_SIZE - 4)[0]
    cs = lambda b: b.split(b"\0", 1)[0].decode()
    n = struct.unpack_from("<I", blk, 0x60)[0]
    names = [x.decode() for x in blk[0x64:TAG_SIZE - 4].rstrip(b"\0").split(b"\0") if x][:n]
    return {"crc_ok": ok, "cfw_version": cs(blk[8:0x18]), "base_version": cs(blk[0x18:0x28]),
            "built_utc": cs(blk[0x28:0x40]), "base_image_sha256": blk[0x40:0x60].hex(), "patches": names}


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()
