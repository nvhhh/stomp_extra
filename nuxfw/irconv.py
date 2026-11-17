"""Cab IR (.wav) -> the 2048-tap float32 block the pedal expects.

Verified against Stomp Manager's upload: coefficients = gain * reverse(ir[0:2048]) at 48 kHz.
Conversion uses open-stomp when installed (see wav_to_coeffs). The fallback approximates Stomp
Manager's gain by matching its output L2 level (0.65372 for the captured IR, error < 1e-7).
"""
from __future__ import annotations

import struct

import numpy as np

TAPS = 2048
RATE = 48000
L2_TARGET = 0.6537202


def read_wav(data: bytes) -> tuple[np.ndarray, int]:
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("not a WAV file")
    pos, fmt, raw = 12, None, None
    while pos + 8 <= len(data):
        cid, size = data[pos:pos + 4], struct.unpack_from("<I", data, pos + 4)[0]
        body = data[pos + 8:pos + 8 + size]
        if cid == b"fmt ":
            tag, ch, rate, _, _, bits = struct.unpack_from("<HHIIHH", body)
            if tag == 0xFFFE and len(body) >= 26:
                tag = struct.unpack_from("<H", body, 24)[0]
            fmt = (tag, ch, rate, bits)
        elif cid == b"data":
            raw = body
        pos += 8 + size + (size & 1)
    if not fmt or raw is None:
        raise ValueError("WAV without fmt/data chunk")
    tag, ch, rate, bits = fmt
    if tag == 3 and bits == 32:
        x = np.frombuffer(raw[:len(raw) // 4 * 4], "<f4").astype(np.float64)
    elif tag == 3 and bits == 64:
        x = np.frombuffer(raw[:len(raw) // 8 * 8], "<f8")
    elif tag == 1 and bits in (16, 24, 32):
        w = bits // 8
        n = len(raw) // w
        if bits == 24:
            b = np.frombuffer(raw[:n * 3], np.uint8).reshape(-1, 3).astype(np.int32)
            v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
            v = np.where(v & 0x800000, v - 0x1000000, v)
            x = v / 8388608.0
        else:
            x = np.frombuffer(raw[:n * w], "<i2" if bits == 16 else "<i4") / float(1 << (bits - 1))
    elif tag == 1 and bits == 8:
        x = (np.frombuffer(raw, np.uint8).astype(np.float64) - 128) / 128.0
    else:
        raise ValueError(f"unsupported WAV encoding (format {tag}, {bits} bit)")
    return x.reshape(-1, ch)[:, 0].astype(np.float64), rate   # first channel


def resample(x: np.ndarray, src: int, dst: int = RATE) -> np.ndarray:
    if src == dst:
        return x
    n = int(round(len(x) * dst / src))
    return np.interp(np.arange(n) * (src / dst), np.arange(len(x)), x)


METHODS = ("optimised", "app")


def wav_to_coeffs(data: bytes, method: str = "optimised") -> bytes:
    """WAV bytes -> 8192-byte IR upload.

    The pedal plays only the first 384 taps (8 ms) of an IR slot.
    method "optimised": open-stomp's converter (github.com/JackMechem/open-stomp-lib, MIT/Apache-2.0)
        fits a 384-tap minimum-phase filter to the whole IR (30 Hz-16 kHz). On the cab IRs tested here
        it cut the error of what the pedal plays from ~3.0 to ~1.4 dB rms.
    method "app": Stomp Manager's conversion (open-stomp's exact reimplementation, within 3e-8 of a
        captured upload). Without open-stomp installed, both use the local approximation below.
    """
    if method not in METHODS:
        raise ValueError(f"unknown IR conversion method {method!r}")
    read_wav(data)  # validate early with a clear error
    try:
        import open_stomp as o
    except ImportError:
        o = None
    if o is not None:
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "ir.wav"
            f.write_bytes(data)
            r = o.ir.convert(str(f), method=method)
        return np.asarray(r.data, dtype="<f4").tobytes()
    x, rate = read_wav(data)
    x = resample(x, rate)[:TAPS]
    x = np.pad(x, (0, TAPS - len(x)))
    l2 = float(np.sqrt((x ** 2).sum()))
    if l2 == 0:
        raise ValueError("IR is silent")
    return (x[::-1] * (L2_TARGET / l2)).astype("<f4").tobytes()
