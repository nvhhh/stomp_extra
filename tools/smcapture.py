"""Launch Stomp Manager under Frida and log the traffic between its Dart code and native plugins.

usage: smcapture.py <path to Stomp Manager.exe> <out.jsonl>

Hooks
  * flutter_windows.dll platform-channel API: every Dart->native message (e.g. universal_ble
    writeValue, flutter_midi_command send) and native->Dart message/response (BLE notifications,
    MIDI input). This sees the device protocol whatever the transport (BLE MIDI or USB MIDI).
  * winmm MIDI API, in case a build talks to WinMM directly.

Each JSONL line: {"t": s, "dir": "d2n"|"n2d"|"resp"|"out"|"in"|"meta", "ch": channel, "hex": payload}
"""
import json
import sys
import threading
import time
from pathlib import Path

import frida

HOOK = r"""
function hookFlutter(m) {
  const cbs = new Set();
  const fn = n => m.getExportByName(n);
  // Dart -> native: the engine invokes the callback registered per channel.
  Interceptor.attach(fn('FlutterDesktopMessengerSetCallback'), {
    onEnter(a) {
      const ch = a[1].readUtf8String();
      const cb = a[2];
      send({dir: 'meta', kind: 'setCallback', ch});
      if (cb.isNull() || cbs.has(cb.toString())) return;
      cbs.add(cb.toString());
      Interceptor.attach(cb, {
        onEnter(b) {
          const msg = b[1];
          const chn = msg.add(8).readPointer().readUtf8String();
          const p = msg.add(16).readPointer();
          const n = msg.add(24).readU64().toNumber();
          send({dir: 'd2n', ch: chn}, n ? p.readByteArray(n) : null);
        }
      });
    }
  });
  // native -> Dart: events / pigeon callbacks.
  for (const name of ['FlutterDesktopMessengerSend', 'FlutterDesktopMessengerSendWithReply']) {
    Interceptor.attach(fn(name), {
      onEnter(a) {
        const ch = a[1].readUtf8String();
        const n = a[3].toUInt32();
        send({dir: 'n2d', ch}, n ? a[2].readByteArray(n) : null);
      }
    });
  }
  // native -> Dart: replies to method calls (e.g. readValue results).
  Interceptor.attach(fn('FlutterDesktopMessengerSendResponse'), {
    onEnter(a) {
      const n = a[3].toUInt32();
      send({dir: 'resp', ch: ''}, n ? a[2].readByteArray(n) : null);
    }
  });
  send({dir: 'meta', kind: 'flutter-hooked'});
}

function hookWinmm(m) {
  const hdr = (p, rec) => p.readPointer().readByteArray(rec ? p.add(12).readU32() : p.add(8).readU32());
  Interceptor.attach(m.getExportByName('midiOutLongMsg'), { onEnter(a) { send({dir: 'out', ch: 'winmm'}, hdr(a[1], false)); } });
  Interceptor.attach(m.getExportByName('midiOutShortMsg'), { onEnter(a) { send({dir: 'out', ch: 'winmm', short: a[1].toUInt32()}); } });
  send({dir: 'meta', kind: 'winmm-hooked'});
}

// WinMM MIDI driver layer (wdmaud2.drv = Windows MIDI Services). Every WinMM MIDI call ends here,
// whatever entry point the app used.
function hookDriver(m) {
  const hdr = (p, rec) => p.readPointer().readByteArray(rec ? p.add(12).readU32() : p.add(8).readU32());
  Interceptor.attach(m.getExportByName('modMessage'), { onEnter(a) {
    const msg = a[1].toUInt32();
    if (msg === 8) send({dir: 'out', ch: 'drv'}, hdr(a[3], false));              // MODM_LONGDATA
    else if (msg === 7) send({dir: 'out', ch: 'drv', short: a[3].toUInt32()});   // MODM_DATA
  }});
  send({dir: 'meta', kind: 'driver-hooked', name: m.name});
}
function hookCallback(m) {
  const hdr = p => p.readPointer().readByteArray(p.add(12).readU32());
  Interceptor.attach(m.getExportByName('DriverCallback'), { onEnter(a) {
    const msg = a[3].toUInt32();
    if (msg === 0x3C4) send({dir: 'in', ch: 'drv'}, hdr(a[5]));                 // MIM_LONGDATA
    else if (msg === 0x3C3) send({dir: 'in', ch: 'drv', short: a[5].toUInt32()}); // MIM_DATA
  }});
  send({dir: 'meta', kind: 'callback-hooked', name: m.name});
}

const done = {};
function check(m) {
  const n = m.name.toLowerCase();
  if (n === 'flutter_windows.dll' && !done.f) { done.f = 1; hookFlutter(m); }
  if (n === 'winmm.dll' && !done.w) { done.w = 1; hookWinmm(m); }
  if (n === 'wdmaud2.drv' && !done.d) { done.d = 1; hookDriver(m); }
  if (n === 'winmmbase.dll' && !done.c) { done.c = 1; hookCallback(m); }
}
Process.enumerateModules().forEach(check);
Process.attachModuleObserver({ onAdded: check });
send({dir: 'meta', kind: 'hooks-ready'});
"""


def main():
    exe = Path(sys.argv[1]).resolve()
    out = open(sys.argv[2], "w", encoding="utf-8")
    t0 = time.time()
    lock = threading.Lock()
    counts = {}

    def on_message(msg, data):
        if msg["type"] != "send":
            print("frida:", msg, flush=True)
            return
        p = dict(msg["payload"])
        rec = {"t": round(time.time() - t0, 4), **p}
        if data is not None:
            rec["hex"] = bytes(data).hex()
        if "short" in p:
            rec["hex"] = p.pop("short").to_bytes(4, "little").hex()
        with lock:
            out.write(json.dumps(rec) + "\n")
            out.flush()
            counts[rec["dir"]] = counts.get(rec["dir"], 0) + 1
        if rec["dir"] == "meta":
            print("meta:", rec, flush=True)

    dev = frida.get_local_device()
    pid = dev.spawn([str(exe)], cwd=str(exe.parent))
    session = dev.attach(pid)
    done = threading.Event()
    session.on("detached", lambda *a: done.set())
    script = session.create_script(HOOK)
    script.on("message", on_message)
    script.load()
    dev.resume(pid)
    print(f"capturing Stomp Manager pid {pid} -> {sys.argv[2]}", flush=True)
    try:
        while not done.wait(10):
            print(f"  t={time.time() - t0:6.0f}s  {counts}", flush=True)
    except KeyboardInterrupt:
        pass
    print("capture ended", counts, flush=True)


if __name__ == "__main__":
    main()
