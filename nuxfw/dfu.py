"""USB-HID DFU transport for the JME/Soran bootloader (m_dfu), reverse engineered from the
bootloader binary (see docs/FORMAT.md).

Wire format, host -> device, 64-byte HID OUT reports (no report ID):
    [0] = 0x01  record fragment
    [1] = fragment number 0..8
    [2..3] unused (0)
    [4..63] 60 bytes of the current 540-byte record
After fragment 8 the bootloader processes the record synchronously in the USB callback and only
re-arms the OUT endpoint when done, so the host is paced by NAKs. Only fragment 0 of the next record
can stall (e.g. during a 64 KiB erase); fragments 0..7 are idempotent and safe to resend.

    [0] = 0x56 ('V')  -> device answers with one 64-byte IN report holding its version string.
There are no per-record acknowledgements.
"""
from __future__ import annotations

import time
from typing import Callable, Iterable, Protocol

from .container import BLOCK, CMD_INFO, CMD_MAIN, DEVICE_ID, END_INDEX, REC_HDR, REC_SIZE, Firmware

DFU_VID, DFU_PID = 0x9527, 0xC157
APP_VID, APP_PID = 0x3962, 0x2000
FRAG = 60
NFRAG = REC_SIZE // FRAG  # 9
assert NFRAG * FRAG == REC_SIZE


class DfuError(Exception):
    pass


class Transport(Protocol):
    def write(self, report: bytes) -> int: ...
    def read(self, n: int, timeout_ms: int) -> bytes: ...
    def close(self) -> None: ...


def fragments(record: bytes) -> list[bytes]:
    if len(record) != REC_SIZE:
        raise DfuError("record must be 540 bytes")
    return [bytes([0x01, i, 0, 0]) + record[i * FRAG:(i + 1) * FRAG] for i in range(NFRAG)]


class HidTransport:
    def __init__(self, path: bytes | None = None):
        import hid
        self._dev = hid.device()
        if path:
            self._dev.open_path(path)
        else:
            self._dev.open(DFU_VID, DFU_PID)
        self.product = self._dev.get_product_string()

    def write(self, report: bytes) -> int:
        if len(report) != 64:
            raise DfuError("reports are 64 bytes")
        return self._dev.write(b"\x00" + report)  # leading 0 = no report ID

    def read(self, n: int, timeout_ms: int) -> bytes:
        return bytes(self._dev.read(n, timeout_ms))

    def close(self) -> None:
        self._dev.close()


def list_devices() -> dict:
    import hid
    dfu = hid.enumerate(DFU_VID, DFU_PID)
    return {"dfu": dfu, "app_hid": hid.enumerate(APP_VID, APP_PID)}


def query_version(t: Transport) -> bytes:
    t.write(b"V" + bytes(63))
    return t.read(64, 1000)


def send_records(t: Transport, records: Iterable[bytes], total: int,
                 progress: Callable[[int, int], None] | None = None,
                 retries: int = 20, retry_sleep: float = 0.05) -> None:
    for n, rec in enumerate(records):
        for i, rep in enumerate(fragments(rec)):
            for attempt in range(retries + 1):
                if t.write(rep) >= 64:
                    break
                if i == NFRAG - 1:
                    # The final fragment triggers the flash write; a blind resend could apply the
                    # record twice. Abort instead: the device stays in DFU mode, just rerun.
                    raise DfuError(f"write of record {n} final fragment failed; re-run the update")
                time.sleep(retry_sleep)
            else:
                raise DfuError(f"record {n} fragment {i}: device not accepting data")
        if progress:
            progress(n + 1, total)


def flash(t: Transport, fw: Firmware, progress=None) -> None:
    recs = [r.encode() for r in fw.records()]
    send_records(t, recs, len(recs), progress)


# --------------------------------------------------------------------------------------------
# Bootloader simulator: re-implements m_dfu's record handling (0xCA50/0xCAD2/0xCC3A in the
# stock bootloader) closely enough to verify that the host side produces exactly the bytes the
# real device would write to flash.
class SimulatedBootloader:
    def __init__(self, flash_size: int = 0x1000000):
        self.buf = bytearray(REC_SIZE)
        self.started = False
        self.offset = 0
        self.flash = bytearray(b"\xff" * flash_size)  # main flash relative to 0x60040000
        self.erased = set()
        self.version = b""
        self.done = False
        self.rejected = False

    def write(self, report: bytes) -> int:
        # Same contract as HidTransport.write: a 64-byte report, returns bytes written incl. report ID.
        if len(report) != 64:
            raise DfuError("sim: reports are 64 bytes")
        if report[0] == 0x56:
            return 65
        if report[0] != 0x01:
            return 65
        i = report[1]
        self.buf[i * FRAG:(i + 1) * FRAG] = report[4:64]
        if i == 8:
            self._process(bytes(self.buf))
        return 65

    def _erase(self, off: int) -> None:
        blk = off & ~0xFFFF
        self.flash[blk:blk + 0x10000] = b"\xff" * 0x10000
        self.erased.add(blk)

    def _program(self, off: int, data: bytes) -> None:
        cur = self.flash[off:off + len(data)]
        if any((c & d) != d for c, d in zip(cur, data)):
            raise DfuError(f"sim: programming non-erased flash at {off:#x}")
        self.flash[off:off + len(data)] = data

    def _process(self, rec: bytes) -> None:
        cmd = (rec[2] << 8) | rec[3]
        if cmd == CMD_INFO:
            dev = bytes((~b) & 0xFF for b in rec[REC_HDR:REC_HDR + len(DEVICE_ID)])
            if dev != DEVICE_ID:
                self.rejected = True
                return
            self.version = bytes((~b) & 0xFF for b in rec[REC_HDR + 8:REC_HDR + 20])
            self.started = True
            return
        if not self.started or cmd != CMD_MAIN:
            return
        idx = int.from_bytes(rec[0x0C:0x10], "big")
        data = rec[REC_HDR:]
        if idx == 0:
            self.offset = 0
            self._erase(0)
        elif self.offset & 0xFFFF == 0:
            self._erase(self.offset)
        self._program(self.offset, data)
        self.offset += BLOCK
        if idx == END_INDEX:
            self.done = True

    def read(self, n, timeout_ms):
        return b""

    def close(self):
        pass
