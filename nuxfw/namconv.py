"""NAM (.nam) -> pedal user-amp blob, using Stomp Manager's own converter DLL.

The pedal does not run the WaveNet model; Stomp Manager reduces it to two 1024-tap float32
filters plus a gain (verified: its upload equals this converter's output byte for byte).
The DLL ships inside Stomp Manager (it writes it to %TEMP% at startup); point SORAN_NAM_DLL or
the `dll` argument at a copy. Conversion runs in a child process so a crash cannot take the
editor down.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_DLL_PATHS = [
    Path(__file__).resolve().parents[1] / "vendor" / "sm_tempdll" / "hidden.dll",
    Path(os.environ.get("TEMP", "")) / "fsdwe-12ssds-fdgh-sser2-sd334d.tmp",
]

CHILD = r"""
import ctypes as C, json, sys, threading
dll = C.WinDLL(sys.argv[1]); CB = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.c_void_p, C.c_void_p)
done = threading.Event(); out = {}
@CB
def info(a, b, c, d): out['half'] = b
@CB
def end(a, b, c, d):
    n = out.get('half') or 4096
    if a and b:
        out['blob'] = (C.string_at(a, n) + C.string_at(b, n)).hex()
    out['gain'] = C.cast(c, C.POINTER(C.c_float))[0] if c else 1.0
    done.set()
dll.setNamInfoCallBack(info); dll.setLoadNamEndCallBack(end)
dll.loadNamFile.argtypes = [C.c_wchar_p]; dll.loadNamFile(sys.argv[2])
done.wait(120); print(json.dumps(out))
"""


def find_dll(dll: str | None = None) -> Path | None:
    for p in ([Path(dll)] if dll else []) + ([Path(os.environ["SORAN_NAM_DLL"])] if os.environ.get("SORAN_NAM_DLL") else []) + DEFAULT_DLL_PATHS:
        if p and p.is_file():
            return p
    return None


def convert(nam_bytes: bytes, dll: str | None = None) -> tuple[bytes, float]:
    path = find_dll(dll)
    if not path:
        raise FileNotFoundError("NAM converter DLL not found (run Stomp Manager once, or set SORAN_NAM_DLL)")
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "model.nam"
        f.write_bytes(nam_bytes)
        r = subprocess.run([sys.executable, "-c", CHILD, str(path), str(f)],
                           capture_output=True, text=True, timeout=180)
    try:
        out = json.loads(r.stdout.strip().splitlines()[-1])
    except (IndexError, ValueError):
        raise RuntimeError(f"NAM conversion failed: {r.stderr.strip()[-300:]}")
    if "blob" not in out:
        raise RuntimeError("NAM conversion produced no data (unsupported .nam file?)")
    blob = bytes.fromhex(out["blob"])
    if len(blob) != 8192:
        raise RuntimeError(f"unexpected converter output size {len(blob)}")
    return blob, float(out["gain"])
