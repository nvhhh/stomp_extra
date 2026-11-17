"""NAM / IR conversion checks against Stomp Manager uploads captured from the real pedal.

usage: python tests/test_conversion.py [--quick]     (--quick skips the ~1 minute NAM fit)

Ground truth: work/midi3.jsonl (Stomp Manager session) uploaded
  * IR  "Marshall Box - 57 E - 24bit - 48kHz - 500ms.wav" to IR slot 8
  * NAM "Marshall JCM 25_50 Model 2555 Lead.nam" to user amp slot 6
The source files must be in ~/Downloads (as in that session); missing files skip their checks.
"""
import glob
import json
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nuxfw import irconv, jme, namconv  # noqa: E402

DL = Path.home() / "Downloads"
ok = True


def check(label, cond):
    global ok
    ok &= bool(cond)
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}")


def captured(cmd, typ=None):
    buf = bytearray(0x2000)
    for line in open(ROOT / "work/midi3.jsonl"):
        m = json.loads(line)
        h = bytes.fromhex(m["hex"])
        if m["dir"] == "host" and h[:5] == jme.HDR + b"\x70" and h[5] == cmd and h[6] == 1:
            u = jme.unpack7(h[7:-1])
            if typ is not None and u[2] != typ:
                continue
            off, tot = struct.unpack_from("<II", u, 4)
            n = min(jme.CHUNK, tot - off)
            buf[off:off + n] = u[12:12 + n]
    return np.frombuffer(bytes(buf), "<f4").astype(np.float64)


def f32(b):
    return np.frombuffer(b, "<f4").astype(np.float64)


def band_error(ref, upload):
    """rms / max dB error (1/3 octave, 31.5 Hz-16 kHz, level-matched) of what the pedal plays."""
    played = f32(upload)[::-1][:384]
    n, sr = 1 << 16, 48000
    f = np.fft.rfftfreq(n, 1 / sr)
    c = 1000 * 2.0 ** (np.arange(-15, 15) / 3)
    c = c[(c >= 31.5) & (c <= 16000)]

    def bands(h):
        H = np.abs(np.fft.rfft(h, n))
        return np.array([20 * np.log10(np.sqrt(np.mean(H[(f >= x / 2 ** (1 / 6)) & (f < x * 2 ** (1 / 6))] ** 2)) + 1e-12)
                         for x in c])
    d = bands(played) - bands(ref)
    d -= d[(c >= 100) & (c <= 8000)].mean()
    return float(np.sqrt(np.mean(d ** 2)))


def main():
    try:
        import open_stomp  # noqa: F401
    except ImportError:
        print("open_stomp is not installed: conversion falls back to the legacy path; nothing to check")
        return 0
    wav = next(iter(glob.glob(str(DL / "**/*57 E - 24bit - 48kHz - 500ms.wav"), recursive=True)), None)
    nam = next(iter(glob.glob(str(DL / "**/Marshall JCM 25_50 Model 2555 Lead.nam"), recursive=True)), None)

    if wav:
        data = Path(wav).read_bytes()
        ref = captured(jme.CMD_IR_DATA)
        app = irconv.wav_to_coeffs(data, "app")
        check("IR 'app' matches the captured Stomp Manager upload (max diff < 1e-7)",
              len(app) == 8192 and np.abs(f32(app) - ref).max() < 1e-7)
        opt = irconv.wav_to_coeffs(data, "optimised")
        check("IR 'optimised' is 8192 bytes of finite float32", len(opt) == 8192 and np.isfinite(f32(opt)).all())
    else:
        print("  [SKIP] IR ground-truth WAV not found in Downloads")

    irs = sorted(set(glob.glob(str(DL / "**/Marshall Box - *.wav"), recursive=True)))
    if irs:
        errs = []
        for f in irs:
            x, rate = irconv.read_wav(Path(f).read_bytes())
            x = irconv.resample(x, rate)
            b = Path(f).read_bytes()
            errs.append((band_error(x, irconv.wav_to_coeffs(b, "app")), band_error(x, irconv.wav_to_coeffs(b, "optimised"))))
        e = np.array(errs)
        print(f"     {len(irs)} cab IRs, error of what the pedal plays: app {e[:, 0].mean():.2f} dB rms, "
              f"optimised {e[:, 1].mean():.2f} dB rms")
        check("optimised IR conversion is more accurate on average", e[:, 1].mean() < e[:, 0].mean())

    if nam:
        model = Path(nam).read_bytes()
        ref = captured(jme.CMD_NAM, jme.NAM_DATA)
        try:
            blob, factor = namconv.convert(model, method="app")
            rel = np.abs(f32(blob) - ref).max() / np.abs(ref).max()
            check(f"NAM 'app' matches the captured upload (relative max diff {rel:.1e} < 1e-3)",
                  len(blob) == 8192 and rel < 1e-3 and factor == 1.0)
        except FileNotFoundError as e:
            print(f"  [SKIP] NAM 'app': {e}")
        if "--quick" not in sys.argv:
            blob, factor = namconv.convert(model, method="optimised")
            d = f32(blob)
            check(f"NAM 'optimised' is 8192 bytes of finite float32 (factor {factor:g})",
                  len(blob) == 8192 and np.isfinite(d).all() and np.isfinite(factor))
            check("NAM 'optimised' keeps the pedal's layout (both filters peak in their last 512 floats)",
                  np.argmax(np.abs(d[:1024])) >= 512 and np.argmax(np.abs(d[1024:])) >= 512)
    else:
        print("  [SKIP] NAM ground-truth model not found in Downloads")

    print("ALL PASSED" if ok else "FAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
