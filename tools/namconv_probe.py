"""Probe Stomp Manager's converter DLL: convert a .nam file and dump what the callbacks receive.

usage: namconv_probe.py <hidden.dll> <file.nam> <out.json>
"""
import ctypes as C
import json
import sys
import threading

dll = C.WinDLL(sys.argv[1])
CB = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.c_void_p, C.c_void_p)
done = threading.Event()
got = {}


def snap(p, n):
    return C.string_at(p, n).hex() if p else None


@CB
def on_info(a, b, c, d):
    got["info"] = {"a": a, "b": b, "c": c, "d": d, "a_mem": snap(a, 0x2100)}


@CB
def on_end(a, b, c, d):
    f = C.cast(c, C.POINTER(C.c_float))[0] if c else None
    got["end"] = {"a": a, "b": b, "c": c, "d": d, "c_float": f,
                  "a_mem": snap(a, 0x2100) if a and a > 0x10000 else None,
                  "b_mem": snap(b, 0x2100) if b and b > 0x10000 else None}
    done.set()


dll.setNamInfoCallBack(on_info)
dll.setLoadNamEndCallBack(on_end)
dll.loadNamFile.argtypes = [C.c_wchar_p]
dll.loadNamFile(sys.argv[2])
done.wait(60)
json.dump(got, open(sys.argv[3], "w"))
print("callbacks:", list(got), {k: {kk: vv for kk, vv in v.items() if not kk.endswith("mem")} for k, v in got.items()})
