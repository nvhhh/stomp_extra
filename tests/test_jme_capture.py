"""Offline check: nuxfw.jme must produce exactly the bytes Stomp Manager sent (work/midi3.jsonl).

usage: python tests/test_jme_capture.py
"""
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nuxfw import jme  # noqa: E402

M = [json.loads(l) for l in open(ROOT / "work/midi3.jsonl")]
HOST = [bytes.fromhex(m["hex"]) for m in M if m["dir"] == "host"]
DEV = [bytes.fromhex(m["hex"]) for m in M if m["dir"] == "dev"]
ok = True


def check(label, cond):
    global ok
    ok &= bool(cond)
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}")


def host(cmd, sub):
    return [h for h in HOST if h[:5] == jme.HDR + b"\x70" and h[5] == cmd and h[6] == sub]


# pack/unpack round trip on every captured message payload
rt = all(jme.pack7(jme.unpack7(h[7:-1]))[:len(h[7:-1])] == h[7:-1]
         for h in HOST + DEV if h[:5] == jme.HDR + b"\x70" and len(h) > 8 and h[5] not in (0x09, 0x12) + jme.CMD_STATE)
check("pack7(unpack7(x)) == x for all bulk payloads", rt)

reads = host(jme.CMD_PRESET, 0)
check(f"preset read requests identical ({len(reads)})",
      all(jme.sysex(jme.CMD_PRESET, 0, jme.pack7(jme.bulk_header(jme.unpack7(r[7:-1])[0]))) == r for r in reads))

saves = host(jme.CMD_PRESET, 1)
for s in saves:
    u = jme.unpack7(s[7:-1])
    idx, rec = u[0], u[12:12 + jme.REC_LEN]
    check(f"preset save message for P{idx + 1} identical",
          jme.bulk_messages(jme.CMD_PRESET, idx, 0, 0, rec) == [s])

(ren,) = host(jme.CMD_NAME, 1)
check("rename message identical",
      jme.sysex(jme.CMD_NAME, 1, bytes([ren[7]]) + "JP Leadasd".encode().ljust(16, b"\0")) == ren)

edit = host(jme.CMD_EDIT, 0)
check("edit-buffer read request identical", edit == [jme.sysex(jme.CMD_EDIT, 0, jme.pack7(jme.bulk_header(0)))])

nam_reads = host(jme.CMD_NAM, 0)
check(f"NAM slot-name read requests identical ({len(nam_reads)})",
      [jme.sysex(jme.CMD_NAM, 0, jme.pack7(jme.bulk_header(0, s, jme.NAM_READ_NAME))) for s in range(10)] == nam_reads)

# NAM upload: rebuild from the converter output (work/namconv.json, produced by tools/namconv_probe.py)
nam_msgs = host(jme.CMD_NAM, 1)
g = json.load(open(ROOT / "work/namconv.json"))
blob = bytes.fromhex(g["end"]["a_mem"])[:4096] + bytes.fromhex(g["end"]["b_mem"])[:4096]
mine = (jme.bulk_messages(jme.CMD_NAM, 0, 5, jme.NAM_NAME,
                          jme.nam_name_record("Marshall JCM 25_50 Model 2555 Lead", g["end"]["c_float"]))
        + jme.bulk_messages(jme.CMD_NAM, 0, 5, jme.NAM_DATA, blob))
check(f"NAM upload: all {len(nam_msgs)} messages identical", mine == nam_msgs)

ir_msgs = host(jme.CMD_IR_DATA, 1)
coeffs = bytearray(0x2000)
for m in ir_msgs:
    u = jme.unpack7(m[7:-1])
    off, tot = struct.unpack_from("<II", u, 4)
    coeffs[off:off + min(jme.CHUNK, tot - off)] = u[12:12 + min(jme.CHUNK, tot - off)]
check(f"IR upload: all {len(ir_msgs)} messages identical",
      jme.bulk_messages(jme.CMD_IR_DATA, 7, 0, 0, bytes(coeffs)) == ir_msgs)

(irt,) = host(jme.CMD_IR_TABLE, 1)
check("IR table write identical",
      jme.sysex(jme.CMD_IR_TABLE, 1, bytes([7]) + jme.pack7(jme.ir_entry("Marshall Box - 57 E - 24bit - 48kHz - 500ms"))) == irt)

# .jmePreset export identical to Stomp Manager's files
for path, idx in (("Marshall JCM 25_50 Model 2555 Lead/P35 Mayer Tone.jmePreset", 34),
                  ("Marshall 1960 4x12 Celestion G12M/P22 Govan Lead.jmePreset", 21)):
    f = Path("C:/Users/nguye/Downloads") / path
    if f.exists():
        data = f.read_bytes()
        i, rec, emb = jme.import_jmepreset(data)
        check(f"{f.name}: export(import(file)) == file", jme.export_jmepreset(i, rec) == data and i == idx and not emb)

print("ALL PASSED" if ok else "FAILURES")
sys.exit(0 if ok else 1)
