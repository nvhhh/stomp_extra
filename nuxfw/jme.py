"""MIDI protocol for the Soran Dual Stomp / Dual Stomp Lite (NUX "JME" platform).

Reverse engineered from the pedal firmware and from Stomp Manager's traffic (docs/PROTOCOL.md).

Framing   F0 00 21 7A 70 <cmd> <sub> <payload> F7      sub: 0 read, 1 write, 2 read-reply, 3 write-ack
Info      F0 00 21 7A 00 F7 -> F0 00 21 7A 10 <version, model>    (class 0x40 -> serial/build)
Bulk      payload = pack(12-byte header + data); header = [a, b, c, 0, u32 offset, u32 total]
          data in <= 136-byte chunks, each acknowledged with sub 3.
Live      Program Change = select preset; CC n (0..7) = module slot model | 0x40 bypass;
          CC 8..58 = parameters; CC 59 = focused slot. The pedal echoes changes as CCs.
"""
from __future__ import annotations

import queue
import struct
import threading
import time
from dataclasses import dataclass

HDR = bytes([0xF0, 0x00, 0x21, 0x7A])
CHUNK = 136
REC_LEN = 98

CMD_IR_TABLE = 0x09
CMD_PRESET = 0x0B
CMD_EDIT = 0x0C
CMD_CHAIN = 0x0D
DEFAULT_CHAIN = (6, 0, 1, 2, 7, 3, 4, 5)
CMD_IR_DATA = 0x10
CMD_NAME = 0x12
CMD_STATE = (0x14, 0x15, 0x18, 0x19)
CMD_NAM = 0x58
CMD_FX_ANYWHERE = 0x30
CMD_DIAGNOSTICS = 0x31
FX_SLOTS = {7: (67, 0), 3: (68, 5), 4: (69, 2)}
NAM_NAME, NAM_DATA, NAM_READ_NAME = 3, 1, 4


def pack7(data: bytes) -> bytes:
    """8-bit -> 7-bit, little-endian bit stream (inverse of the firmware's unpacker)."""
    out, acc, n = bytearray(), 0, 0
    for b in data:
        acc |= b << n
        n += 8
        while n >= 7:
            out.append(acc & 0x7F)
            acc >>= 7
            n -= 7
    if n:
        out.append(acc & 0x7F)
    return bytes(out)


def unpack7(data: bytes) -> bytes:
    out, acc, n = bytearray(), 0, 0
    for b in data:
        acc |= (b & 0x7F) << n
        n += 7
        while n >= 8:
            out.append(acc & 0xFF)
            acc >>= 8
            n -= 8
    return bytes(out)


def bulk_header(a: int, b: int = 0, c: int = 0, offset: int = 0, total: int = 0) -> bytes:
    return bytes([a, b, c, 0]) + struct.pack("<II", offset, total)


def sysex(cmd: int, sub: int, payload: bytes = b"") -> bytes:
    return HDR + bytes([0x70, cmd, sub]) + payload + b"\xF7"


def validate_chain(order) -> bytes:
    if (not isinstance(order, (list, tuple, bytes)) or len(order) != 8
            or any(type(v) is not int for v in order) or sorted(order) != list(range(8))):
        raise ValueError('Chain must contain each of the eight effect slots exactly once')
    return bytes(order)


def bulk_messages(cmd: int, a: int, b: int, c: int, data: bytes) -> list[bytes]:
    """Write messages for a bulk transfer (one per 136-byte chunk)."""
    msgs = []
    for off in range(0, max(len(data), 1), CHUNK):
        part = data[off:off + CHUNK]
        msgs.append(sysex(cmd, 1, pack7(bulk_header(a, b, c, off, len(data)) + part)))
    return msgs


def ir_entry(name: str | None) -> bytes:
    """36-byte IR table entry: u32 used + 16-char name + 16 spare. Empty slots read '--------'."""
    if name is None:
        return struct.pack("<I", 0) + b"--------".ljust(32, b"\0")
    return struct.pack("<I", 1) + name.encode("ascii", "replace")[:16].ljust(32, b"\0")


def nam_name_record(name: str, gain: float) -> bytes:
    rec = bytearray(128)
    enc = name.encode("ascii", "replace")[:32]
    rec[:len(enc)] = enc
    rec[33] = 1
    struct.pack_into("<f", rec, 52, gain)
    return bytes(rec)


@dataclass
class Event:
    kind: str          # "cc" | "pc" | "sysex"
    data: bytes


class Pedal:
    """USB-MIDI connection. Threaded: incoming CC/PC go to `events`, replies to waiting requests."""

    def __init__(self, match: str = "JME"):
        import rtmidi
        self.mi, self.mo = rtmidi.MidiIn(), rtmidi.MidiOut()
        ins = [i for i, p in enumerate(self.mi.get_ports()) if match in p]
        outs = [i for i, p in enumerate(self.mo.get_ports()) if match in p]
        if not ins or not outs:
            raise ConnectionError(f"no MIDI port matching {match!r} (is the pedal connected over USB?)")
        self.mi.open_port(ins[0])
        self.mo.open_port(outs[0])
        self.mi.ignore_types(sysex=False, timing=True, active_sense=True)
        self.mi.set_callback(self._rx)
        self.events: "queue.Queue[Event]" = queue.Queue()
        self._waiters: list[tuple[callable, queue.Queue]] = []
        self._lock = threading.Lock()
        self._io = threading.Lock()

    def close(self):
        self.mi.close_port()
        self.mo.close_port()

    # ---- low level ---------------------------------------------------------------------
    def _rx(self, msg, _):
        data = bytes(msg[0])
        with self._lock:
            for i, (pred, q) in enumerate(self._waiters):
                if pred(data):
                    q.put(data)
                    del self._waiters[i]
                    return
        st = data[0] & 0xF0
        self.events.put(Event("cc" if st == 0xB0 else "pc" if st == 0xC0 else "sysex", data))

    def send(self, data: bytes):
        self.mo.send_message(list(data))

    def request(self, msg: bytes, pred, timeout: float = 2.0, retries: int = 2) -> bytes:
        for attempt in range(retries + 1):
            q: queue.Queue = queue.Queue()
            with self._lock:
                self._waiters.append((pred, q))
            try:
                self.send(msg)
                return q.get(timeout=timeout)
            except queue.Empty:
                pass
            finally:
                with self._lock:
                    self._waiters = [w for w in self._waiters if w[1] is not q]
        raise TimeoutError(f"no reply to {msg[:8].hex()}")

    @staticmethod
    def _is(cmd: int, sub: int, first: int | None = None):
        def pred(d: bytes):
            return (d[:5] == HDR + b"\x70" and len(d) > 7 and d[5] == cmd and d[6] == sub
                    and (first is None or d[7] == first))
        return pred

    def _bulk_pred(self, cmd, sub, a):
        def pred(d: bytes):
            if not (d[:5] == HDR + b"\x70" and d[5] == cmd and d[6] == sub):
                return False
            return a is None or unpack7(d[7:-1])[:1] == bytes([a])
        return pred

    # ---- device ------------------------------------------------------------------------
    def info(self) -> dict:
        with self._io:
            r1 = self.request(HDR + b"\x00\xF7", lambda d: d[:5] == HDR + b"\x10")
            r2 = self.request(HDR + b"\x40\xF7", lambda d: d[:5] == HDR + b"\x10")
        cs = lambda b: b.split(b"\0", 1)[0].decode("ascii", "replace")
        return {"firmware": cs(r1[5:37]), "model": cs(r1[37:45]),
                "build": cs(r2[5:21]), "extra": cs(r2[21:37])}

    def read_state(self) -> dict:
        out = {}
        with self._io:
            for c in CMD_STATE:
                r = self.request(sysex(c, 0), self._is(c, 2))
                out[f"{c:02x}"] = r[7:-1].hex()
        return out

    def fx_anywhere(self) -> bool:
        """Read-only capability probe; stock firmware does not advertise this extension."""
        self.fx_version = 0
        with self._io:
            try:
                r = self.request(sysex(CMD_FX_ANYWHERE, 0), self._is(CMD_FX_ANYWHERE, 2),
                                 timeout=0.4, retries=0)
            except TimeoutError:
                return False
        if len(r) == 15 and r[7:10] == b'FXA' and r[10] in (1, 2, 3):
            self.fx_version = r[10]
        return self.fx_version > 0

    def diagnostics(self) -> dict:
        """Read the optional diagnostic build; never change effect selection."""
        with self._io:
            r = self.request(sysex(CMD_DIAGNOSTICS, 0),
                             self._is(CMD_DIAGNOSTICS, 2), timeout=0.5, retries=0)
        payload = r[7:-1]
        if len(payload) != 84 or payload[:4] != b'DGT1' or any(v > 127 for v in payload):
            raise ValueError('invalid diagnostic reply')
        names = ('passes', 'start_cycles', 'period_cycles', 'elapsed_cycles',
                 'peak_elapsed_cycles', 'busy', 'unfinished_passes',
                 'eq_key', 'eq_stage', 'mod_key', 'mod_stage', 'del_key',
                 'del_stage', 'vendor_timer_ticks', 'dwt_control', 'passes_after')
        values = [sum(v << (7*i) for i,v in enumerate(payload[p:p+5]))
                  for p in range(4,84,5)]
        if any(v > 0xffffffff for v in values):
            raise ValueError('diagnostic value exceeds uint32')
        d = dict(zip(names,values))
        d['consistent'] = d['passes'] == d['passes_after']
        return d

    def capture_metrics(self) -> dict:
        """Read optional CGC1 capture checkpoints (0.4.5 diagnostic build)."""
        with self._io:
            r = self.request(sysex(0x32, 0), self._is(0x32, 2), timeout=0.5, retries=0)
        payload=r[7:-1]
        if len(payload)!=54 or payload[:4]!=b'CGC1' or any(v>127 for v in payload):
            raise ValueError('invalid capture checkpoint reply')
        values=[sum(v<<(7*i) for i,v in enumerate(payload[p:p+5])) for p in range(4,54,5)]
        if any(v>0xffffffff for v in values):
            raise ValueError('capture checkpoint exceeds uint32')
        names=('key','stage','before_cycles','after_cycles','trip_checkpoint')
        return {slot:dict(zip(names,values[i*5:i*5+5])) for i,slot in enumerate(('eq','mod'))}

    def profiler(self, pages: int = 50, header: int = 32) -> dict:
        """Read the stall profiler (command 0x33, read-only). 0.6.3: pages=50, header=32;
        0.6.3-diag: pages=49, header=16."""
        words = []
        with self._io:
            for page in range(pages):
                r = self.request(sysex(0x33, 0, bytes([page])), self._is(0x33, 2), timeout=0.5, retries=1)
                payload = r[7:-1]
                if len(payload) != 84 or payload[:4] != b'PRF1' or any(v > 127 for v in payload):
                    raise ValueError('invalid profiler reply')
                words += [sum(v << (7*i) for i, v in enumerate(payload[p:p+5])) & 0xffffffff
                          for p in range(4, 84, 5)]
        names = ('heartbeat', 'heartbeat_seen', 'stall_callbacks', 'stall_samples', 'longest_stall',
                 'longest_samples', 'stalls', 'gap_since_sample', 'longest_start_pass',
                 'current_start_pass', 'last_stall', 'longest_gap', 'settle_left', 'settle_quiet',
                 'settle_redraw_seen', 'recalls', 'debt', 'max_debt', 'debt_latches',
                 'settles_by_quiet', 'settles_by_limit')
        out = dict(zip(names, words[:header]))
        def samples(first, count):
            return [dict(pc=words[k], lr=words[k+1], exc_return=words[k+2], gap=words[k+3])
                    for k in range(first, first + 4*count, 4)]
        out['current'] = samples(header, out['stall_samples'])
        out['longest'] = samples(header + 4*96, out['longest_samples'])
        return out

    def set_fx_override(self, slot: int, model: int | None):
        maximum = 26 if slot in (7, 3) and getattr(self, 'fx_version', 0) >= 2 else 16
        if slot not in FX_SLOTS or (model is not None and not 0 <= model < maximum):
            raise ValueError('invalid FX Anywhere slot or model')
        with self._io:
            r = self.request(sysex(CMD_FX_ANYWHERE, 1, bytes([slot, 0 if model is None else model+1])),
                             self._is(CMD_FX_ANYWHERE, 3))
        if len(r) != 15 or r[7:10] != b'FXA' or r[10] not in (1, 2, 3):
            raise RuntimeError('firmware did not acknowledge FX Anywhere')
        expected = 0 if model is None else 0x50 + model
        if r[11 + (7, 3, 4).index(slot)] != expected:
            raise RuntimeError('firmware did not apply the requested effect')

    # ---- presets -----------------------------------------------------------------------
    def read_preset(self, index: int) -> bytes:
        with self._io:
            r = self.request(sysex(CMD_PRESET, 0, pack7(bulk_header(index))),
                             self._bulk_pred(CMD_PRESET, 2, index))
        u = unpack7(r[7:-1])
        return u[12:12 + REC_LEN]

    def read_edit(self) -> bytes:
        with self._io:
            r = self.request(sysex(CMD_EDIT, 0, pack7(bulk_header(0))), self._is(CMD_EDIT, 2))
        return unpack7(r[7:-1])[12:12 + REC_LEN]

    def read_chain(self) -> list[int]:
        with self._io:
            r = self.request(sysex(CMD_CHAIN, 0), self._is(CMD_CHAIN, 2))
        return list(validate_chain(r[7:-1]))

    def set_chain(self, order):
        payload = validate_chain(order)
        with self._io:
            # Vendor handler acknowledges a write with sub 2, not the usual sub 3.
            r = self.request(sysex(CMD_CHAIN, 1, payload), self._is(CMD_CHAIN, 2))
        if r[7:-1] != payload:
            raise RuntimeError('Pedal did not acknowledge the requested effect order')

    def write_preset(self, index: int, record: bytes, name: str | None = None):
        """Save a 98-byte record to a preset slot (what Stomp Manager does on Save)."""
        rec = bytearray(record)
        if name is not None:
            enc = name.encode("ascii", "replace")[:16]
            rec[82:98] = enc.ljust(16, b"\0")
            name_bytes = bytes(rec[82:98])
        with self._io:
            if name is not None:
                self.request(sysex(CMD_NAME, 1, bytes([index]) + name_bytes), self._is(CMD_NAME, 3))
            (msg,) = bulk_messages(CMD_PRESET, index, 0, 0, bytes(rec))
            self.request(msg, self._bulk_pred(CMD_PRESET, 3, index))
        self.select(index)

    def select(self, index: int):
        self.send(bytes([0xC0, index & 0x7F]))

    def cc(self, number: int, value: int):
        self.send(bytes([0xB0, number & 0x7F, max(0, min(127, int(value)))]))

    # ---- IR (cab) slots ----------------------------------------------------------------
    def ir_table(self, slot: int) -> dict:
        with self._io:
            r = self.request(sysex(CMD_IR_TABLE, 0, bytes([slot])), self._is(CMD_IR_TABLE, 2, slot))
        e = unpack7(r[8:-1])
        used = struct.unpack_from("<I", e, 0)[0]
        return {"slot": slot, "used": bool(used),
                "name": e[4:36].split(b"\0", 1)[0].decode("ascii", "replace") if used else None}

    def upload_ir(self, slot: int, coeffs: bytes, name: str, progress=None):
        """coeffs: 8192 bytes = 2048 float32 (time-reversed IR, see nuxfw.irconv)."""
        msgs = bulk_messages(CMD_IR_DATA, slot, 0, 0, coeffs)
        with self._io:
            for i, m in enumerate(msgs):
                self.request(m, self._bulk_pred(CMD_IR_DATA, 3, slot))
                if progress:
                    progress(i + 1, len(msgs))
            self.request(sysex(CMD_IR_TABLE, 1, bytes([slot]) + pack7(ir_entry(name))),
                         self._is(CMD_IR_TABLE, 3))

    # ---- NAM (user amp) slots ----------------------------------------------------------
    def nam_name(self, slot: int) -> str:
        with self._io:
            r = self.request(sysex(CMD_NAM, 0, pack7(bulk_header(0, slot, NAM_READ_NAME))),
                             lambda d: self._bulk_pred(CMD_NAM, 2, None)(d) and unpack7(d[7:-1])[1] == slot)
        return unpack7(r[7:-1])[12:44].split(b"\0", 1)[0].decode("ascii", "replace")

    def upload_nam(self, slot: int, blob: bytes, name: str, gain: float, progress=None):
        """blob: 8192 bytes produced by Stomp Manager's converter (nuxfw.namconv)."""
        msgs = bulk_messages(CMD_NAM, 0, slot, NAM_NAME, nam_name_record(name, gain))
        msgs += bulk_messages(CMD_NAM, 0, slot, NAM_DATA, blob)
        pred = lambda d: self._bulk_pred(CMD_NAM, 3, None)(d) and unpack7(d[7:-1])[1] == slot
        with self._io:
            for i, m in enumerate(msgs):
                self.request(m, pred)
                if progress:
                    progress(i + 1, len(msgs))


# ---- .jmePreset files (Stomp Manager export) -------------------------------------------
JMEPRESET_LEN = 8359


def export_jmepreset(index: int, record: bytes) -> bytes:
    f = bytearray(JMEPRESET_LEN)
    f[35] = index
    f[36:36 + REC_LEN] = record
    f[134] = 0xFF                       # no embedded user amp / IR
    struct.pack_into("<f", f, 167, 1.0)
    return bytes(f)


def import_jmepreset(data: bytes) -> tuple[int, bytes, bool]:
    """-> (original index, 98-byte record, has embedded user data)."""
    if len(data) != JMEPRESET_LEN:
        raise ValueError(f"not a .jmePreset file ({len(data)} bytes, expected {JMEPRESET_LEN})")
    return data[35], data[36:36 + REC_LEN], data[134] != 0xFF
