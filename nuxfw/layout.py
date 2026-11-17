"""Main-flash layout of the JME (Soran Dual Stomp family) firmware image.

All offsets are into the flat image that DFU command 4 writes at FLASH_BASE.
Code slots are linked at address 0 and copied into ITCM by the stage-1 loader,
so for code slots *slot offset == runtime address*.
"""
from __future__ import annotations

from dataclasses import dataclass

FLASH_BASE = 0x60040000  # where the bootloader writes the flat image (FlexSPI NOR, XIP alias)


@dataclass(frozen=True)
class Region:
    name: str
    start: int
    size: int
    kind: str
    desc: str
    protected: bool = False

    @property
    def end(self) -> int:
        return self.start + self.size


REGIONS = [
    Region("master", 0x000000, 0x40000, "code",
           "Main app for Dual Stomp / Dual Stomp Lite (JME=1/2). Cortex-M7, IAR, linked @0x0 (ITCM)."),
    Region("jme3", 0x040000, 0x40000, "code",
           "App for Tiny Stomp (JME=3). Not executed on a Dual Stomp Lite."),
    Region("tables", 0x080000, 0x40000, "data", "float32 DSP tables"),
    Region("presets", 0x100000, 0x40000, "data", "Factory preset bank (names + parameters)"),
    Region("m_dfu", 0x140000, 0x10000, "code",
           "DFU bootloader image (USB HID 9527:c157). Never modified: it is the recovery path.",
           protected=True),
    Region("assets", 0x150000, 0, "data", "IR / NAM / drum / coefficient data up to end of image"),
]

# Space inside code slots that is unused by the stock app and reserved for CFW code/data.
# master stock code+data ends at 0x36D08; keep a margin and leave the top 4 KiB of the slot alone.
FREE = {
    "master": (0x38000, 0x3F000),
}
# Never written by the patcher unless a patch explicitly sets allow_protected.
RESERVED = [
    ("master", 0x3F000, 0x40000, "top 4 KiB of ITCM slot left untouched"),
    ("jme3", 0x3F000, 0x40000, "top 4 KiB of ITCM slot left untouched"),
]


def region(name: str) -> Region:
    for r in REGIONS:
        if r.name == name:
            return r
    raise KeyError(f"unknown region {name!r}; known: {', '.join(r.name for r in REGIONS)}")


def regions_for(image_len: int) -> list[Region]:
    """Concrete regions for an image of the given length (assets runs to the end)."""
    out = []
    for r in REGIONS:
        if r.size == 0:
            r = Region(r.name, r.start, image_len - r.start, r.kind, r.desc, r.protected)
        out.append(r)
    return out


def locate(flat_off: int) -> tuple[str, int]:
    for r in REGIONS:
        if r.start <= flat_off and (r.size == 0 or flat_off < r.end):
            return r.name, flat_off - r.start
    return "?", flat_off
