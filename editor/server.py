"""Stomp Editor: local web editor for the Soran Dual Stomp / Dual Stomp Lite (USB MIDI).

usage: python editor/server.py [--port 8765] [--no-browser]
Then open http://127.0.0.1:8765
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from nuxfw import irconv, jme, namconv  # noqa: E402

CATALOG = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
N_PRESETS, N_USER = 99, 10


def cc_offset(cc: int) -> int | None:
    """Record byte offset for a CC number (see docs/PROTOCOL.md)."""
    if 0 <= cc < 8:
        return cc
    if cc == CATALOG["volume"]["cc"]:
        return CATALOG["volume"]["offset"]
    for m in CATALOG["modules"]:
        if m["cc_base"] <= cc < m["cc_base"] + m["capacity"]:
            return m["count_offset"] + 1 + (cc - m["cc_base"])
    return None


class App:
    def __init__(self):
        self.cond = threading.Condition()
        self.pedal: jme.Pedal | None = None
        self.version = 0
        self.s = {"connected": False, "error": None, "info": None, "presets": [None] * N_PRESETS,
                  "current": None, "edit": None, "dirty": False, "ir": [None] * N_USER,
                  "nam": [None] * N_USER, "raw_state": None, "task": None}
        self._refresh_at = 0.0
        self._model_lock = threading.Lock()
        threading.Thread(target=self._refresher, daemon=True).start()

    # ---- state ---------------------------------------------------------------------------
    def bump(self, **kw):
        with self.cond:
            self.s.update(kw)
            self.version += 1
            self.cond.notify_all()

    def snapshot(self, since: int, wait: float = 20.0) -> dict:
        with self.cond:
            if since >= self.version:
                self.cond.wait(timeout=wait)
            return {"version": self.version, **self.s}

    def set_byte(self, off: int, val: int, dirty=True):
        with self.cond:
            if self.s["edit"] is None:
                return
            rec = bytearray.fromhex(self.s["edit"])
            rec[off] = val
            self.s["edit"] = rec.hex()
            if dirty:
                self.s["dirty"] = True
        self.bump()

    # ---- connection ----------------------------------------------------------------------
    def connect(self):
        if self.pedal:
            try:
                self.pedal.close()
            except Exception:
                pass
        self.pedal = None
        self.bump(connected=False, fx_anywhere=False, split_captures=False, error=None, task={"label": "Connecting", "done": 0, "total": 1})
        try:
            p = jme.Pedal()
            self.pedal = p
            info = p.info()
            fx_anywhere = p.fx_anywhere()
            split_captures = getattr(p, 'fx_version', 0) == 3
            raw = p.read_state()
            current = bytes.fromhex(raw["15"])[0]
            self.bump(connected=True, fx_anywhere=fx_anywhere, capture_slots=getattr(p, 'fx_version', 0) >= 2,
                      split_captures=split_captures, info=info, raw_state=raw, current=current,
                      edit=p.read_edit().hex(), dirty=False)
            threading.Thread(target=self._events, args=(p,), daemon=True).start()
            names = []
            for i in range(N_PRESETS):
                names.append(self._name(p.read_preset(i)))
                if i % 10 == 9:
                    self.bump(presets=names + [None] * (N_PRESETS - len(names)),
                              task={"label": "Reading presets", "done": i + 1, "total": N_PRESETS})
            ir = [p.ir_table(i) for i in range(N_USER)]
            nam = [p.nam_name(i) for i in range(20 if split_captures else N_USER)]
            self.bump(presets=names, ir=ir, nam=nam, task=None)
        except Exception as e:
            self.bump(connected=False, error=str(e), task=None)

    @staticmethod
    def _name(rec: bytes) -> str:
        return rec[82:98].split(b"\0", 1)[0].decode("ascii", "replace")

    def _events(self, p: jme.Pedal):
        while self.pedal is p:
            try:
                ev = p.events.get(timeout=1)
            except Exception:
                continue
            d = ev.data
            if ev.kind == "cc" and len(d) == 3:
                cc, val = d[1], d[2]
                off = cc_offset(cc)
                if off is not None:
                    self.set_byte(off, val, dirty=False)
                if cc < 8:                       # model change: pedal loads model defaults
                    self._refresh_at = time.time() + 0.4
            elif ev.kind == "pc" and len(d) >= 2:
                self.bump(current=d[1], dirty=False)
                self._refresh_at = time.time() + 0.3

    def _refresher(self):
        while True:
            time.sleep(0.1)
            if self._refresh_at and time.time() >= self._refresh_at and self.pedal:
                self._refresh_at = 0
                try:
                    with self.cond:
                        dirty = self.s["dirty"]
                    self.bump(edit=self.pedal.read_edit().hex(), dirty=dirty)
                except Exception as e:
                    self.bump(error=f"refresh failed: {e}")

    # ---- actions -------------------------------------------------------------------------
    def need(self) -> jme.Pedal:
        if not self.pedal:
            raise RuntimeError("pedal not connected")
        return self.pedal

    def select(self, index: int):
        with self._model_lock:
            self.need().select(index)
            self.bump(current=index, dirty=False)
            self._refresh_at = time.time() + 0.3

    def cc(self, cc: int, value: int, focus: int | None = None):
        p = self.need()
        if focus is not None:
            p.cc(59, focus)
        p.cc(cc, value)
        off = cc_offset(cc)
        if off is not None:
            self.set_byte(off, value)
        if cc < 8:
            self._refresh_at = time.time() + 0.4

    def save(self, index: int, name: str):
        with self._model_lock:
            p = self.need()
            rec = p.read_edit()
            p.write_preset(index, rec, name)
            with self.cond:
                self.s["presets"][index] = name[:16]
            self.bump(current=index, dirty=False)
            self._refresh_at = time.time() + 0.3

    def model(self, slot: int, model: int):
        """Virtual model IDs 32..47 select OD/FX in the three extended slots."""
        mod = next((m for m in CATALOG['modules'] if m['slot'] == slot), None)
        if mod is None:
            raise ValueError('unknown slot')
        capture = 48 <= model < 58 and slot in (7, 3)
        extended = (32 <= model < 48 and slot in jme.FX_SLOTS) or capture
        if not extended and not any(m['index'] == model for m in mod['models']):
            raise ValueError('unknown model')
        capable = self.s.get('fx_anywhere', False)
        if extended and not capable:
            raise ValueError('Install FX Anywhere firmware to use OD/FX in this slot')
        if capture and not self.s.get('capture_slots', False):
            raise ValueError('Install firmware with EQ/MOD capture support first')
        with self._model_lock:
            p = self.need()
            rec = p.read_edit()
            bypass = rec[slot] & 0x40
            if slot in jme.FX_SLOTS and capable:
                p.set_fx_override(slot, None)
            p.cc(59, slot)
            carrier = jme.FX_SLOTS[slot][1] if extended else model
            p.cc(slot, carrier | bypass)
            def wait_for(predicate):
                deadline = time.monotonic() + 2.0
                while time.monotonic() < deadline:
                    time.sleep(0.03)
                    current = p.read_edit()
                    if predicate(current):
                        return current
                raise TimeoutError('Pedal did not apply the model/parameter change')
            wait_for(lambda r: r[slot] == carrier | bypass)
            if extended:
                fx = ({'params': []} if capture else
                      next(m for m in CATALOG['modules'] if m['slot'] == 0)['models'][model-32])
                enum_pos = {q.get('pos', i) for i, q in enumerate(fx['params']) if q.get('type') == 'enum'}
                defaults = [0 if i in enum_pos else 50 for i in range(4)]
                for i in range(4):
                    p.cc(mod['cc_base'] + i, defaults[i])
                off = mod['count_offset'] + 1
                wait_for(lambda r: list(r[off:off+4]) == defaults)
                p.set_fx_override(slot, model - 32)
            self.bump(edit=p.read_edit().hex(), dirty=True)
            self._refresh_at = time.time() + 0.4

    def export(self, index: int) -> tuple[str, bytes]:
        rec = self.need().read_preset(index)
        return f"P{index + 1:02d} {self._name(rec)}.jmePreset", jme.export_jmepreset(index, rec)

    def chain(self, order):
        requested = jme.validate_chain(order)
        with self._model_lock:
            p = self.need()
            p.set_chain(list(requested))
            rec = p.read_edit()
            if rec[70:78] != requested:
                raise RuntimeError('Chain readback does not match; reconnect to refresh the pedal state')
            self.bump(edit=rec.hex(), dirty=True)

    def import_preset(self, index: int, data: bytes) -> str:
        _, rec, embedded = jme.import_jmepreset(data)
        self.need().write_preset(index, rec)
        with self.cond:
            self.s["presets"][index] = self._name(rec)
        self.bump(current=index, dirty=False)
        self._refresh_at = time.time() + 0.3
        return "imported" + (" (file also carried user amp/IR data, which was not imported)" if embedded else "")

    def _task(self, label, fn):
        def prog(done, total):
            self.bump(task={"label": label, "done": done, "total": total})
        def run():
            try:
                fn(prog)
                self.bump(task=None)
            except Exception as e:
                traceback.print_exc()
                self.bump(task=None, error=f"{label} failed: {e}")
        threading.Thread(target=run, daemon=True).start()

    def upload_ir(self, slot: int, name: str, wav: bytes, method: str = "app"):
        coeffs = irconv.wav_to_coeffs(wav, method)
        p = self.need()

        def run(prog):
            p.upload_ir(slot, coeffs, name, prog)
            with self.cond:
                self.s["ir"][slot] = p.ir_table(slot)
            self.bump()
        self._task(f"Uploading IR to slot {slot + 1}", run)

    def upload_nam(self, slot: int, name: str, nam: bytes, method: str = "optimised"):
        if method not in namconv.METHODS:
            raise ValueError(f"unknown conversion method {method!r}")
        p = self.need()
        split = self.s.get('split_captures', False)
        if not 0 <= slot < (20 if split else 10):
            raise ValueError('invalid capture slot')
        fx_slot = slot - (10 if split else 0)

        def run(prog):
            self.bump(task={"label": "Converting NAM" + (" (accurate fit, about a minute)" if method == "optimised" else ""),
                            "done": 0, "total": 1})
            blob, gain = namconv.convert(nam, method=method)
            p.upload_nam(slot, blob, name, gain, prog)
            if self.s.get('capture_slots', False):
                with self._model_lock:
                    rec = p.read_edit()
                    for effect_slot in (7, 3):
                        spare, carrier = jme.FX_SLOTS[effect_slot]
                        if 0 <= fx_slot < 10 and rec[effect_slot] & 63 == carrier and rec[spare] == 0x60 + fx_slot:
                            p.set_fx_override(effect_slot, 16 + fx_slot)
            with self.cond:
                self.s["nam"][slot] = p.nam_name(slot)
            self.bump()
        self._task(f"Uploading NAM to slot {slot + 1}", run)


APP = App()


class Handler(BaseHTTPRequestHandler):
    def _origin_allowed(self):
        origin = self.headers.get('Origin')
        local = f'http://127.0.0.1:{self.server.server_port}'
        return not origin or origin in (local, f'http://localhost:{self.server.server_port}', getattr(self.server, 'pages_origin', None))

    def end_headers(self):
        origin = self.headers.get('Origin')
        if origin and self._origin_allowed():
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.send_header('Access-Control-Expose-Headers', 'Content-Disposition')
            self.send_header('Access-Control-Allow-Private-Network', 'true')
        super().end_headers()

    def do_OPTIONS(self):
        self._json({}, 200 if self._origin_allowed() else 403)

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _body(self) -> bytes:
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def do_GET(self):
        if not self._origin_allowed():
            return self._json({'error': 'Origin not allowed'}, 403)
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path in ("/", "/index.html"):
                b = (ROOT / "static" / "index.html").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)
            elif u.path == "/api/catalog":
                self._json(CATALOG)
            elif u.path == "/api/state":
                self._json(APP.snapshot(int(q.get("since", -1))))
            elif u.path == "/api/diagnostics":
                if not APP.pedal:
                    raise RuntimeError('pedal is not connected')
                self._json(APP.pedal.diagnostics())
            elif u.path == "/api/export":
                name, data = APP.export(int(q["index"]))
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Disposition", f'attachment; filename="{name}"')
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self._json({"error": "not found"}, 404)
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def do_POST(self):
        if not self._origin_allowed():
            return self._json({'error': 'Origin not allowed'}, 403)
        u = urlparse(self.path)
        q = {k: unquote(v[0]) for k, v in parse_qs(u.query).items()}
        try:
            if u.path == "/api/connect":
                threading.Thread(target=APP.connect, daemon=True).start()
                return self._json({"ok": True})
            if u.path in ("/api/ir", "/api/nam", "/api/import"):
                body = self._body()
                if u.path == "/api/ir":
                    APP.upload_ir(int(q["slot"]), q.get("name", "IR"), body, q.get("method", "app"))
                    return self._json({"ok": True})
                if u.path == "/api/nam":
                    APP.upload_nam(int(q["slot"]), q.get("name", "NAM"), body, q.get("method", "optimised"))
                    return self._json({"ok": True})
                return self._json({"ok": True, "message": APP.import_preset(int(q["index"]), body)})
            a = json.loads(self._body() or b"{}")
            if u.path == "/api/select":
                APP.select(int(a["index"]))
            elif u.path == "/api/cc":
                APP.cc(int(a["cc"]), int(a["value"]), a.get("focus"))
            elif u.path == "/api/model":
                APP.model(int(a['slot']), int(a['model']))
            elif u.path == "/api/chain":
                APP.chain(a['order'])
            elif u.path == "/api/save":
                APP.save(int(a["index"]), str(a["name"]))
            elif u.path == "/api/dismiss":
                APP.bump(error=None)
            else:
                return self._json({"error": "not found"}, 404)
            self._json({"ok": True})
        except Exception as e:
            traceback.print_exc()
            self._json({"error": str(e)}, 500)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--pages", action="store_true", help="Allow the hosted editor at https://nvhhh.github.io/stomp_extra/")
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    srv.pages_origin = 'https://nvhhh.github.io' if a.pages else None
    url = f"http://127.0.0.1:{a.port}"
    print(f"Stomp Editor running at {url}  (Ctrl+C to quit)", flush=True)
    threading.Thread(target=APP.connect, daemon=True).start()
    if not a.no_browser:
        webbrowser.open(f'https://nvhhh.github.io/stomp_extra/?port={a.port}' if a.pages else url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
