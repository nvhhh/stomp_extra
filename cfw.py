#!/usr/bin/env python3
"""Soran Dual Stomp Lite custom-firmware tool.

  cfw.py info     <fw.bin>                 show container/image details (+ CFW tag if present)
  cfw.py unpack   <fw.bin> <dir>           extract flat image, regions, notes, manifest
  cfw.py pack     <dir> <out.bin>          rebuild a .bin from an unpacked dir (flat.bin)
  cfw.py build    [-c cfw.toml]            stock firmware + patches -> custom firmware
  cfw.py diff     <a.bin> <b.bin>          list changed ranges between two firmware images
  cfw.py selftest [-c cfw.toml]            round-trip + simulated DFU transfer checks
  cfw.py devices                           list pedal USB/HID interfaces (normal & DFU mode)
  cfw.py query                             ask a pedal in DFU mode for its version
  cfw.py flash    <fw.bin> [--yes]         write firmware to a pedal in DFU mode
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import tomllib
from pathlib import Path

from nuxfw import dfu, layout, patcher
from nuxfw.container import BLOCK, Firmware

ROOT = Path(__file__).resolve().parent


def load(path) -> Firmware:
    return Firmware.parse(Path(path).read_bytes())


def cmd_info(a):
    fw = load(a.file)
    print(json.dumps(fw.summary(), indent=2))
    print("\nregions (flat offset -> flash address):")
    for r in layout.regions_for(len(fw.image)):
        print(f"  {r.name:8s} {r.start:#09x}-{r.end:#09x}  @{layout.FLASH_BASE + r.start:#010x}"
              f"  {'[protected] ' if r.protected else ''}{r.desc}")
    tag = patcher.read_tag(fw.image)
    print("\ncustom firmware tag:", json.dumps(tag, indent=2) if tag else "none (stock image)")


def cmd_unpack(a):
    fw = load(a.file)
    out = Path(a.dir)
    (out / "regions").mkdir(parents=True, exist_ok=True)
    (out / "flat.bin").write_bytes(fw.image)
    for r in layout.regions_for(len(fw.image)):
        (out / "regions" / f"{r.start:06x}_{r.name}.bin").write_bytes(fw.image[r.start:r.end])
    (out / "header.bin").write_bytes(fw.header)
    (out / "notes.txt").write_bytes(fw.notes)
    (out / "extr.bin").write_bytes(fw.extra)
    (out / "info.bin").write_bytes(fw.info)
    (out / "final.bin").write_bytes(fw.final)
    man = {**fw.summary(), "info_progress": fw.info_progress, "progress": fw.progress}
    (out / "manifest.json").write_text(json.dumps(man))
    print(f"unpacked to {out}  (edit flat.bin, then `cfw.py pack {out} out.bin`)")


def cmd_pack(a):
    d = Path(a.dir)
    man = json.loads((d / "manifest.json").read_text())
    fw = Firmware(header=(d / "header.bin").read_bytes(), notes=(d / "notes.txt").read_bytes(),
                  extra=(d / "extr.bin").read_bytes(), info=(d / "info.bin").read_bytes(),
                  image=(d / "flat.bin").read_bytes(), final=(d / "final.bin").read_bytes(),
                  info_progress=man["info_progress"], progress=man["progress"])
    if len(fw.image) // BLOCK + 1 != len(fw.progress):
        fw.progress = []
    out = fw.build()
    Firmware.parse(out)
    Path(a.out).write_bytes(out)
    print(f"wrote {a.out} ({len(out)} bytes)")


def read_config(path):
    p = Path(path)
    cfg = tomllib.loads(p.read_text(encoding="utf-8"))
    base = (p.parent / cfg["base"]["file"]).resolve()
    if not base.exists():
        sys.exit(f"base firmware not found: {base}\n"
                 "Download it from soranaudio.com (Device Firmware Updater zip) -- see README.")
    return p.parent, cfg, base


def do_build(cfg_path, quiet=False):
    root, cfg, base_path = read_config(cfg_path)
    raw = base_path.read_bytes()
    want = cfg["base"].get("sha256")
    if want and patcher.sha256(raw) != want:
        sys.exit(f"base firmware sha256 mismatch: {patcher.sha256(raw)} != {want}")
    fw = Firmware.parse(raw)
    if patcher.read_tag(fw.image):
        sys.exit("base firmware already carries a CFW tag; use the stock image as base")

    writes, names = [], []
    for pf in cfg["build"].get("patches", []):
        name, desc, w = patcher.load_patch(root / pf)
        names.append(name)
        writes += w
        if not quiet:
            print(f"  patch {name}: {len(w)} op(s)  {desc}")
    image = patcher.apply(fw.image, writes)

    tag_cfg = cfg.get("tag", {})
    if tag_cfg.get("enabled", True):
        tag = patcher.build_tag(cfg["build"]["version"], cfg["base"]["version"],
                                patcher.sha256(fw.image), names)
        lo, _ = layout.FREE["master"]
        image = patcher.apply(image, [patcher.Write("cfw-tag", "master", lo, tag, None, False)])

    out_fw = fw.with_image(image)
    out = out_fw.build()
    Firmware.parse(out)  # must round-trip
    dest = root / cfg["build"]["output"].format(version=cfg["build"]["version"],
                                                base=cfg["base"]["version"])
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(out)
    return fw, out_fw, dest


def cmd_build(a):
    fw, out_fw, dest = do_build(a.config)
    changed = diff_ranges(fw.image, out_fw.image)
    print(f"built {dest}")
    for lo, hi in changed:
        name, off = layout.locate(lo)
        print(f"  changed {name}+{off:#x} .. +{off + hi - lo:#x} ({hi - lo} bytes)")
    print(f"  sha256 {patcher.sha256(dest.read_bytes())}")


def diff_ranges(a: bytes, b: bytes, gap=16):
    if len(a) != len(b):
        return [(min(len(a), len(b)), max(len(a), len(b)))]
    out = []
    i, n = 0, len(a)
    step = 4096
    while i < n:
        if a[i:i + step] == b[i:i + step]:
            i += step
            continue
        end = min(n, i + step)
        for j in range(i, end):
            if a[j] != b[j]:
                if out and j - out[-1][1] <= gap:
                    out[-1][1] = j + 1
                else:
                    out.append([j, j + 1])
        i = end
    return [tuple(x) for x in out]


def cmd_diff(a):
    fa, fb = load(a.a), load(a.b)
    for k in ("device_name", "device_id", "info_version", "dfu_usb_id"):
        if fa.summary()[k] != fb.summary()[k]:
            print(f"  {k}: {fa.summary()[k]} -> {fb.summary()[k]}")
    rs = diff_ranges(fa.image, fb.image)
    for lo, hi in rs:
        name, off = layout.locate(lo)
        print(f"  {name}+{off:#x}: {hi - lo} bytes   {fa.image[lo:min(hi, lo + 16)].hex()} -> "
              f"{fb.image[lo:min(hi, lo + 16)].hex()}")
    print(f"{len(rs)} changed range(s)")


def cmd_selftest(a):
    ok = True

    def check(label, cond):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {label}")

    root, cfg, base_path = read_config(a.config)
    raw = base_path.read_bytes()
    fw = Firmware.parse(raw)
    check("stock image parses and rebuilds byte-identical", fw.build() == raw)
    fw2 = Firmware.parse(raw)
    fw2.progress = []
    check("rebuild with computed progress bytes is byte-identical", fw2.build() == raw)
    check("BL encoder matches stock bootloader (0xc35a -> 0xca50)",
          patcher.encode_bl(0xC35A, 0xCA50) == bytes.fromhex("00f079fb"))
    check("BL encoder matches stock bootloader backwards (0xca68 -> 0xca3c)",
          patcher.encode_bl(0xCA68, 0xCA3C) == bytes.fromhex("fff7e8ff"))
    lo, hi = layout.FREE["master"]
    check("master CFW area is blank in stock image", not any(fw.image[lo:hi]))
    check("master stock code ends below CFW area", not any(fw.image[0x36D08:lo]))

    _, out_fw, dest = do_build(a.config, quiet=True)
    built = Firmware.parse(dest.read_bytes())
    rs = diff_ranges(fw.image, built.image)
    allowed = [(lo, hi)]
    for path in cfg['build'].get('patches', []):
        _, _, writes = patcher.load_patch(root / path)
        allowed.extend((w.flat, w.flat + len(w.data)) for w in writes)
    check(f"custom build differs only in declared patch ranges or CFW area ({len(rs)} range(s))",
          all(all(fw.image[off] == built.image[off] or any(a <= off < b for a,b in allowed)
                  for off in range(x,y)) for x,y in rs))
    m = layout.region("m_dfu")
    check("DFU bootloader region identical to stock",
          built.image[m.start:m.end] == fw.image[m.start:m.end])
    check("CFW tag readable with valid CRC", (patcher.read_tag(built.image) or {}).get("crc_ok"))

    for label, f in (("stock", fw), ("custom", built)):
        sim = dfu.SimulatedBootloader()
        t0 = time.time()
        dfu.flash(sim, f)
        n = len(f.image)
        check(f"simulated DFU of {label} image writes exactly the image "
              f"({time.time() - t0:.1f}s, {len(sim.erased)} erases)",
              sim.done and not sim.rejected and sim.flash[:n] == f.image
              and sim.flash[n:n + BLOCK] == f.final)
    bad = Firmware.parse(raw)
    info = bytearray(bad.info); info[0] ^= 0xFF; bad.info = bytes(info)
    sim = dfu.SimulatedBootloader(); dfu.flash(sim, bad)
    check("simulated bootloader rejects wrong device id", sim.rejected and not sim.done)
    print("selftest", "PASSED" if ok else "FAILED")
    sys.exit(0 if ok else 1)


def cmd_devices(a):
    import subprocess
    print("DFU mode (HID 9527:c157):")
    for d in dfu.list_devices()["dfu"]:
        print(f"  {d['product_string']!r} {d['manufacturer_string']!r} path={d['path']!r}")
    if not dfu.list_devices()["dfu"]:
        print("  none  (power on the pedal while holding Left + Right to enter DFU mode)")
    if sys.platform == "win32":
        ps = ("Get-PnpDevice -PresentOnly | ? InstanceId -match 'VID_3962&PID_2000' | "
              "% { '  ' + $_.Class + '  ' + $_.FriendlyName + '  ' + $_.InstanceId }")
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
        print("Normal mode (USB 3962:2000):")
        print(r.stdout.rstrip() or "  none")


def open_dfu():
    devs = dfu.list_devices()["dfu"]
    if not devs:
        sys.exit("no pedal in DFU mode found (power on while holding Left + Right)")
    if len(devs) > 1:
        sys.exit("more than one DFU device connected; connect only one pedal")
    return dfu.HidTransport(devs[0]["path"])


def cmd_query(a):
    t = open_dfu()
    try:
        print("product:", t.product)
        r = dfu.query_version(t)
        print("reply:", r.hex(), repr(bytes(b for b in r if 32 <= b < 127)))
    finally:
        t.close()


def cmd_flash(a):
    fw = load(a.file)
    s = fw.summary()
    tag = patcher.read_tag(fw.image)
    print(f"file: {a.file}\n  device {s['device_name']} / id {s['device_id']} / {s['records']} records")
    print(f"  {'CFW ' + tag['cfw_version'] + ' on ' + tag['base_version'] if tag else 'stock image (no CFW tag)'}")
    t = open_dfu()
    print("  target:", t.product)
    if not a.yes:
        if input("Write this firmware to the pedal? Do not unplug during the update. [y/N] ").lower() != "y":
            t.close()
            sys.exit("aborted")
    t0 = time.time()

    def prog(n, total):
        if n % 200 == 0 or n == total:
            el = time.time() - t0
            eta = el / n * (total - n)
            print(f"\r  {n}/{total} records  {100 * n // total:3d}%  eta {eta:5.0f}s", end="", flush=True)
    try:
        dfu.flash(t, fw, prog)
    finally:
        t.close()
    print(f"\ndone in {time.time() - t0:.0f}s. Power-cycle the pedal.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("info"); p.add_argument("file"); p.set_defaults(f=cmd_info)
    p = sub.add_parser("unpack"); p.add_argument("file"); p.add_argument("dir"); p.set_defaults(f=cmd_unpack)
    p = sub.add_parser("pack"); p.add_argument("dir"); p.add_argument("out"); p.set_defaults(f=cmd_pack)
    for name, fn in (("build", cmd_build), ("selftest", cmd_selftest)):
        p = sub.add_parser(name); p.add_argument("-c", "--config", default=str(ROOT / "cfw.toml")); p.set_defaults(f=fn)
    p = sub.add_parser("diff"); p.add_argument("a"); p.add_argument("b"); p.set_defaults(f=cmd_diff)
    p = sub.add_parser("devices"); p.set_defaults(f=cmd_devices)
    p = sub.add_parser("query"); p.set_defaults(f=cmd_query)
    p = sub.add_parser("flash"); p.add_argument("file"); p.add_argument("--yes", action="store_true"); p.set_defaults(f=cmd_flash)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
