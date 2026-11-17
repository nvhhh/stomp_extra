// Stomp Editor, direct mode: talks to the pedal over Web MIDI (Chrome / Edge) and converts NAM/IR
// files in a Web Worker (stomp_convert.wasm, open-stomp). It answers the same /api/... requests as
// the Python bridge (editor/server.py), so the page works the same with either.
// Protocol: nuxfw/jme.py and docs/PROTOCOL.md.
'use strict';
(() => {
const HDR = [0xF0, 0x00, 0x21, 0x7A];
const CHUNK = 136, REC_LEN = 98, N_PRESETS = 99, N_USER = 10;
const CMD = {IR_TABLE: 0x09, PRESET: 0x0B, EDIT: 0x0C, CHAIN: 0x0D, IR_DATA: 0x10, NAME: 0x12,
             NAM: 0x58, FX_ANYWHERE: 0x30, DIAGNOSTICS: 0x31};
const CMD_STATE = [0x14, 0x15, 0x18, 0x19];
const FX_SLOTS = {7: [67, 0], 3: [68, 5], 4: [69, 2]};
const NAM_NAME = 3, NAM_DATA = 1, NAM_READ_NAME = 4;

const sleep = ms => new Promise(r => setTimeout(r, ms));
const hex = b => Array.from(b, x => x.toString(16).padStart(2, '0')).join('');
const unhex = h => Uint8Array.from(h.match(/../g) || [], x => parseInt(x, 16));
const cat = (...parts) => { const out = []; for (const p of parts) out.push(...p); return Uint8Array.from(out); };
const ascii = (s, n) => { const b = new Uint8Array(n); [...String(s)].slice(0, n).forEach((c, i) => { const k = c.charCodeAt(0); b[i] = k < 128 ? k : 63; }); return b; };
const cstr = b => { const i = b.indexOf(0); return String.fromCharCode(...(i < 0 ? b : b.subarray(0, i))); };

function pack7(data) {
  const out = []; let acc = 0, n = 0;
  for (const b of data) { acc |= b << n; n += 8; while (n >= 7) { out.push(acc & 0x7F); acc >>= 7; n -= 7; } }
  if (n) out.push(acc & 0x7F);
  return out;
}
function unpack7(data) {
  const out = []; let acc = 0, n = 0;
  for (const b of data) { acc |= (b & 0x7F) << n; n += 7; while (n >= 8) { out.push(acc & 0xFF); acc >>= 8; n -= 8; } }
  return Uint8Array.from(out);
}
function bulkHeader(a, b = 0, c = 0, offset = 0, total = 0) {
  const h = new Uint8Array(12), v = new DataView(h.buffer);
  h.set([a, b, c, 0]); v.setUint32(4, offset, true); v.setUint32(8, total, true);
  return h;
}
const sysex = (cmd, sub, payload = []) => cat(HDR, [0x70, cmd, sub], payload, [0xF7]);
function bulkMessages(cmd, a, b, c, data) {
  const msgs = [];
  for (let off = 0; off < Math.max(data.length, 1); off += CHUNK)
    msgs.push(sysex(cmd, 1, pack7(cat(bulkHeader(a, b, c, off, data.length), data.subarray(off, off + CHUNK)))));
  return msgs;
}
function validateChain(order) {
  if (!Array.isArray(order) || order.length !== 8 || order.some(v => !Number.isInteger(v)) ||
      [...order].sort().join() !== '0,1,2,3,4,5,6,7')
    throw new Error('Chain must contain each of the eight effect slots exactly once');
  return Uint8Array.from(order);
}
function irEntry(name) {
  const e = new Uint8Array(36);
  if (name == null) { e.set(ascii('--------', 8), 4); return e; }
  e[0] = 1; e.set(ascii(name, 16), 4); return e;
}
function namNameRecord(name, gain) {
  const r = new Uint8Array(128);
  r.set(ascii(name, 32)); r[33] = 1; new DataView(r.buffer).setFloat32(52, gain, true);
  return r;
}
const isMsg = (cmd, sub, first) => d => d.length > 7 && d[0] === 0xF0 && d[1] === 0 && d[2] === 0x21 && d[3] === 0x7A &&
  d[4] === 0x70 && d[5] === cmd && d[6] === sub && (first == null || d[7] === first);
const bulkPred = (cmd, sub, a) => d => isMsg(cmd, sub)(d) && (a == null || unpack7(d.subarray(7, -1))[0] === a);
const payload = d => d.subarray(7, d.length - 1);

class Mutex {
  constructor() { this.tail = Promise.resolve(); }
  run(fn) { const r = this.tail.then(fn, fn); this.tail = r.catch(() => {}); return r; }
}

class Pedal {
  static async open(access) {
    const find = ports => [...ports.values()].find(p => /JME/i.test(p.name || '') && p.state !== 'disconnected');
    const input = find(access.inputs), output = find(access.outputs);
    if (!input || !output) throw new Error('Pedal not found. Connect it by USB, close Stomp Manager and other editors, then try again.');
    const p = new Pedal(input, output);
    await input.open(); await output.open();
    return p;
  }
  constructor(input, output) {
    this.input = input; this.output = output; this.waiters = []; this.onevent = null;
    this.io = new Mutex(); this.fxVersion = 0;
    input.onmidimessage = e => this.rx(e.data);
  }
  close() { this.input.onmidimessage = null; try { this.input.close(); this.output.close(); } catch {} }
  rx(d) {
    const i = this.waiters.findIndex(w => w.pred(d));
    if (i >= 0) { const [w] = this.waiters.splice(i, 1); w.resolve(d); return; }
    const st = d[0] & 0xF0;
    this.onevent?.(st === 0xB0 ? 'cc' : st === 0xC0 ? 'pc' : 'sysex', d);
  }
  send(data) { this.output.send(data); }
  async request(msg, pred, timeout = 2000, retries = 2) {
    for (let attempt = 0; attempt <= retries; attempt++) {
      let w;
      const reply = new Promise(resolve => { w = {pred, resolve}; this.waiters.push(w); });
      this.send(msg);
      const r = await Promise.race([reply, sleep(timeout).then(() => null)]);
      this.waiters = this.waiters.filter(x => x !== w);
      if (r) return r;
    }
    throw new Error(`No reply from the pedal (${hex(msg.subarray(0, 8))})`);
  }
  // ---- device
  info() {
    return this.io.run(async () => {
      const isInfo = d => d[0] === 0xF0 && d[1] === 0 && d[2] === 0x21 && d[3] === 0x7A && d[4] === 0x10;
      const r1 = await this.request(Uint8Array.from([...HDR, 0x00, 0xF7]), isInfo);
      const r2 = await this.request(Uint8Array.from([...HDR, 0x40, 0xF7]), isInfo);
      return {firmware: cstr(r1.subarray(5, 37)), model: cstr(r1.subarray(37, 45)),
              build: cstr(r2.subarray(5, 21)), extra: cstr(r2.subarray(21, 37))};
    });
  }
  readState() {
    return this.io.run(async () => {
      const out = {};
      for (const c of CMD_STATE) out[c.toString(16).padStart(2, '0')] = hex(payload(await this.request(sysex(c, 0), isMsg(c, 2))));
      return out;
    });
  }
  fxAnywhere() {
    this.fxVersion = 0;
    return this.io.run(async () => {
      let r;
      try { r = await this.request(sysex(CMD.FX_ANYWHERE, 0), isMsg(CMD.FX_ANYWHERE, 2), 400, 0); } catch { return false; }
      if (r.length === 15 && cstr(r.subarray(7, 10)) === 'FXA' && [1, 2, 3].includes(r[10])) this.fxVersion = r[10];
      return this.fxVersion > 0;
    });
  }
  diagnostics() {
    return this.io.run(async () => {
      const p = payload(await this.request(sysex(CMD.DIAGNOSTICS, 0), isMsg(CMD.DIAGNOSTICS, 2), 500, 0));
      if (p.length !== 84 || cstr(p.subarray(0, 4)) !== 'DGT1' || p.some(v => v > 127)) throw new Error('invalid diagnostic reply');
      const names = ['passes', 'start_cycles', 'period_cycles', 'elapsed_cycles', 'peak_elapsed_cycles', 'busy',
        'unfinished_passes', 'eq_key', 'eq_stage', 'mod_key', 'mod_stage', 'del_key', 'del_stage',
        'vendor_timer_ticks', 'dwt_control', 'passes_after'];
      const d = {};
      names.forEach((n, i) => { let v = 0; for (let k = 4; k >= 0; k--) v = v * 128 + p[4 + i * 5 + k]; d[n] = v; });
      if (Object.values(d).some(v => v > 0xFFFFFFFF)) throw new Error('diagnostic value exceeds uint32');
      d.consistent = d.passes === d.passes_after;
      return d;
    });
  }
  setFxOverride(slot, model) {
    const maximum = [7, 3].includes(slot) && this.fxVersion >= 2 ? 26 : 16;
    if (!FX_SLOTS[slot] || (model != null && !(model >= 0 && model < maximum))) throw new Error('invalid FX Anywhere slot or model');
    return this.io.run(async () => {
      const r = await this.request(sysex(CMD.FX_ANYWHERE, 1, [slot, model == null ? 0 : model + 1]), isMsg(CMD.FX_ANYWHERE, 3));
      if (r.length !== 15 || cstr(r.subarray(7, 10)) !== 'FXA' || ![1, 2, 3].includes(r[10])) throw new Error('firmware did not acknowledge FX Anywhere');
      if (r[11 + [7, 3, 4].indexOf(slot)] !== (model == null ? 0 : 0x50 + model)) throw new Error('firmware did not apply the requested effect');
    });
  }
  // ---- presets
  readPreset(index) {
    return this.io.run(async () => unpack7(payload(await this.request(sysex(CMD.PRESET, 0, pack7(bulkHeader(index))),
      bulkPred(CMD.PRESET, 2, index)))).slice(12, 12 + REC_LEN));
  }
  readEdit() {
    return this.io.run(async () => unpack7(payload(await this.request(sysex(CMD.EDIT, 0, pack7(bulkHeader(0))),
      isMsg(CMD.EDIT, 2)))).slice(12, 12 + REC_LEN));
  }
  setChain(order) {
    const p = validateChain(order);
    return this.io.run(async () => {
      // The vendor handler acknowledges a chain write with sub 2, not the usual 3.
      const r = await this.request(sysex(CMD.CHAIN, 1, p), isMsg(CMD.CHAIN, 2));
      if (hex(payload(r)) !== hex(p)) throw new Error('Pedal did not acknowledge the requested effect order');
    });
  }
  async writePreset(index, record, name) {
    const rec = Uint8Array.from(record);
    if (name != null) rec.set(ascii(name, 16), 82);
    await this.io.run(async () => {
      if (name != null) await this.request(sysex(CMD.NAME, 1, cat([index], rec.subarray(82, 98))), isMsg(CMD.NAME, 3));
      const [msg] = bulkMessages(CMD.PRESET, index, 0, 0, rec);
      await this.request(msg, bulkPred(CMD.PRESET, 3, index));
    });
    this.select(index);
  }
  select(index) { this.send(Uint8Array.from([0xC0, index & 0x7F])); }
  cc(number, value) { this.send(Uint8Array.from([0xB0, number & 0x7F, Math.max(0, Math.min(127, Math.trunc(value)))])); }
  // ---- user IR / NAM slots
  irTable(slot) {
    return this.io.run(async () => {
      const e = unpack7((await this.request(sysex(CMD.IR_TABLE, 0, [slot]), isMsg(CMD.IR_TABLE, 2, slot))).subarray(8, -1));
      const used = new DataView(e.buffer).getUint32(0, true);
      return {slot, used: !!used, name: used ? cstr(e.subarray(4, 36)) : null};
    });
  }
  uploadIr(slot, coeffs, name, progress) {
    const msgs = bulkMessages(CMD.IR_DATA, slot, 0, 0, coeffs);
    return this.io.run(async () => {
      for (let i = 0; i < msgs.length; i++) { await this.request(msgs[i], bulkPred(CMD.IR_DATA, 3, slot)); progress?.(i + 1, msgs.length); }
      await this.request(sysex(CMD.IR_TABLE, 1, cat([slot], pack7(irEntry(name)))), isMsg(CMD.IR_TABLE, 3));
    });
  }
  namName(slot) {
    return this.io.run(async () => {
      const r = await this.request(sysex(CMD.NAM, 0, pack7(bulkHeader(0, slot, NAM_READ_NAME))),
        d => bulkPred(CMD.NAM, 2, null)(d) && unpack7(payload(d))[1] === slot);
      return cstr(unpack7(payload(r)).subarray(12, 44));
    });
  }
  uploadNam(slot, blob, name, gain, progress) {
    const msgs = [...bulkMessages(CMD.NAM, 0, slot, NAM_NAME, namNameRecord(name, gain)),
                  ...bulkMessages(CMD.NAM, 0, slot, NAM_DATA, blob)];
    const pred = d => bulkPred(CMD.NAM, 3, null)(d) && unpack7(payload(d))[1] === slot;
    return this.io.run(async () => {
      for (let i = 0; i < msgs.length; i++) { await this.request(msgs[i], pred); progress?.(i + 1, msgs.length); }
    });
  }
}

// ---- .jmePreset files (Stomp Manager export)
const JMEPRESET_LEN = 8359;
function exportJmePreset(index, record) {
  const f = new Uint8Array(JMEPRESET_LEN);
  f[35] = index; f.set(record, 36); f[134] = 0xFF;          // no embedded user amp / IR
  new DataView(f.buffer).setFloat32(167, 1.0, true);
  return f;
}
function importJmePreset(data) {
  if (data.length !== JMEPRESET_LEN) throw new Error(`not a .jmePreset file (${data.length} bytes, expected ${JMEPRESET_LEN})`);
  return [data[35], data.slice(36, 36 + REC_LEN), data[134] !== 0xFF];
}

// ---- file conversion (Web Worker + WebAssembly, open-stomp)
function convert(kind, method, bytes, onProgress) {
  return new Promise((resolve, reject) => {
    const worker = new Worker(new URL('convert-worker.js', document.baseURI));
    worker.onmessage = e => {
      const m = e.data;
      if (m.progress) return onProgress?.(m.progress[0], m.progress[1]);
      worker.terminate();
      m.error ? reject(new Error(m.error)) : resolve(m);
    };
    worker.onerror = e => { worker.terminate(); reject(new Error(e.message || 'converter failed to start')); };
    worker.postMessage({kind, method, bytes}, [bytes.buffer]);
  });
}

// ---- editor state and actions (port of the bridge's App)
class App {
  constructor(catalog) {
    this.CAT = catalog; this.version = 0; this.pedal = null; this.access = null;
    this.s = {connected: false, error: null, info: null, presets: Array(N_PRESETS).fill(null), current: null,
              edit: null, dirty: false, ir: Array(N_USER).fill(null), nam: Array(N_USER).fill(null),
              raw_state: null, task: null, direct: true};
    this.waiting = []; this.refreshTimer = null; this.modelLock = new Mutex();
  }
  bump(kw = {}) {
    Object.assign(this.s, kw); this.version++;
    const w = this.waiting; this.waiting = []; w.forEach(f => f());
  }
  async snapshot(since) {
    if (since >= this.version) await new Promise(r => { this.waiting.push(r); setTimeout(r, 20000); });
    return {version: this.version, ...this.s};
  }
  ccOffset(cc) {
    if (cc >= 0 && cc < 8) return cc;
    if (cc === this.CAT.volume.cc) return this.CAT.volume.offset;
    const m = this.CAT.modules.find(m => m.cc_base <= cc && cc < m.cc_base + m.capacity);
    return m ? m.count_offset + 1 + (cc - m.cc_base) : null;
  }
  setByte(off, val, dirty = true) {
    if (this.s.edit == null) return;
    const rec = unhex(this.s.edit); rec[off] = val; this.s.edit = hex(rec);
    if (dirty) this.s.dirty = true;
    this.bump();
  }
  refreshSoon(ms) {
    clearTimeout(this.refreshTimer);
    this.refreshTimer = setTimeout(async () => {
      if (!this.pedal) return;
      try { const dirty = this.s.dirty; this.bump({edit: hex(await this.pedal.readEdit()), dirty}); }
      catch (e) { this.bump({error: `refresh failed: ${e.message}`}); }
    }, ms);
  }
  async connect() {
    this.pedal?.close(); this.pedal = null;
    this.bump({connected: false, fx_anywhere: false, split_captures: false, error: null, task: {label: 'Connecting', done: 0, total: 1}});
    try {
      if (!navigator.requestMIDIAccess) throw new Error('This browser has no Web MIDI. Use Chrome or Edge on a computer.');
      if (!this.access) {
        this.access = await navigator.requestMIDIAccess({sysex: true});
        this.access.onstatechange = e => {
          if (this.pedal && e.port.state === 'disconnected' && (e.port === this.pedal.input || e.port === this.pedal.output)) {
            this.pedal.close(); this.pedal = null;
            this.bump({connected: false, error: 'Pedal disconnected. Reconnect it, then click Reconnect.', task: null});
          }
        };
      }
      const p = await Pedal.open(this.access);
      this.pedal = p;
      const info = await p.info();
      const fxAnywhere = await p.fxAnywhere();
      const split = p.fxVersion === 3;
      const raw = await p.readState();
      this.bump({connected: true, fx_anywhere: fxAnywhere, capture_slots: p.fxVersion >= 2, split_captures: split,
                 info, raw_state: raw, current: unhex(raw['15'])[0], edit: hex(await p.readEdit()), dirty: false});
      p.onevent = (kind, d) => this.onEvent(p, kind, d);
      const names = [];
      for (let i = 0; i < N_PRESETS; i++) {
        names.push(cstr((await p.readPreset(i)).subarray(82, 98)));
        if (i % 10 === 9) this.bump({presets: [...names, ...Array(N_PRESETS - names.length).fill(null)],
                                     task: {label: 'Reading presets', done: i + 1, total: N_PRESETS}});
      }
      const ir = []; for (let i = 0; i < N_USER; i++) ir.push(await p.irTable(i));
      const nam = []; for (let i = 0; i < (split ? 20 : N_USER); i++) nam.push(await p.namName(i));
      this.bump({presets: names, ir, nam, task: null});
    } catch (e) {
      const msg = e.name === 'SecurityError' || e.name === 'NotAllowedError'
        ? 'MIDI access was blocked. Allow MIDI (with system exclusive messages) for this site, then click Reconnect.' : e.message;
      this.bump({connected: false, error: msg, task: null});
    }
  }
  onEvent(p, kind, d) {
    if (this.pedal !== p) return;
    if (kind === 'cc' && d.length === 3) {
      const off = this.ccOffset(d[1]);
      if (off != null) this.setByte(off, d[2], false);
      if (d[1] < 8) this.refreshSoon(400);              // model change: the pedal loads model defaults
    } else if (kind === 'pc' && d.length >= 2) {
      this.bump({current: d[1], dirty: false}); this.refreshSoon(300);
    }
  }
  need() { if (!this.pedal) throw new Error('pedal not connected'); return this.pedal; }
  select(index) {
    return this.modelLock.run(async () => { this.need().select(index); this.bump({current: index, dirty: false}); this.refreshSoon(300); });
  }
  cc(cc, value, focus) {
    const p = this.need();
    if (focus != null) p.cc(59, focus);
    p.cc(cc, value);
    const off = this.ccOffset(cc);
    if (off != null) this.setByte(off, value);
    if (cc < 8) this.refreshSoon(400);
  }
  save(index, name) {
    return this.modelLock.run(async () => {
      const p = this.need();
      await p.writePreset(index, await p.readEdit(), name);
      this.s.presets[index] = name.slice(0, 16);
      this.bump({current: index, dirty: false}); this.refreshSoon(300);
    });
  }
  model(slot, model) {
    // Virtual model IDs 32..47 select OD/FX in the three extended slots, 48..57 captures in EQ/MOD.
    const mod = this.CAT.modules.find(m => m.slot === slot);
    if (!mod) throw new Error('unknown slot');
    const capture = model >= 48 && model < 58 && [7, 3].includes(slot);
    const extended = (model >= 32 && model < 48 && FX_SLOTS[slot]) || capture;
    if (!extended && !mod.models.some(m => m.index === model)) throw new Error('unknown model');
    const capable = !!this.s.fx_anywhere;
    if (extended && !capable) throw new Error('Install FX Anywhere firmware to use OD/FX in this slot');
    if (capture && !this.s.capture_slots) throw new Error('Install firmware with EQ/MOD capture support first');
    return this.modelLock.run(async () => {
      const p = this.need();
      const bypass = (await p.readEdit())[slot] & 0x40;
      if (FX_SLOTS[slot] && capable) await p.setFxOverride(slot, null);
      p.cc(59, slot);
      const carrier = extended ? FX_SLOTS[slot][1] : model;
      p.cc(slot, carrier | bypass);
      const waitFor = async pred => {
        const deadline = performance.now() + 2000;
        while (performance.now() < deadline) { await sleep(30); const r = await p.readEdit(); if (pred(r)) return r; }
        throw new Error('Pedal did not apply the model/parameter change');
      };
      await waitFor(r => r[slot] === (carrier | bypass));
      if (extended) {
        const fx = capture ? {params: []} : this.CAT.modules.find(m => m.slot === 0).models[model - 32];
        const enumPos = new Set(fx.params.map((q, i) => q.type === 'enum' ? (Number.isInteger(q.pos) ? q.pos : i) : -1));
        const defaults = [0, 1, 2, 3].map(i => enumPos.has(i) ? 0 : 50);
        defaults.forEach((v, i) => p.cc(mod.cc_base + i, v));
        const off = mod.count_offset + 1;
        await waitFor(r => defaults.every((v, i) => r[off + i] === v));
        await p.setFxOverride(slot, model - 32);
      }
      this.bump({edit: hex(await p.readEdit()), dirty: true}); this.refreshSoon(400);
    });
  }
  async exportPreset(index) {
    const rec = await this.need().readPreset(index);
    return [`P${String(index + 1).padStart(2, '0')} ${cstr(rec.subarray(82, 98))}.jmePreset`, exportJmePreset(index, rec)];
  }
  chain(order) {
    const requested = validateChain(order);
    return this.modelLock.run(async () => {
      const p = this.need();
      await p.setChain([...requested]);
      const rec = await p.readEdit();
      if (hex(rec.subarray(70, 78)) !== hex(requested)) throw new Error('Chain readback does not match; reconnect to refresh the pedal state');
      this.bump({edit: hex(rec), dirty: true});
    });
  }
  async importPreset(index, data) {
    const [, rec, embedded] = importJmePreset(data);
    await this.need().writePreset(index, rec);
    this.s.presets[index] = cstr(rec.subarray(82, 98));
    this.bump({current: index, dirty: false}); this.refreshSoon(300);
    return 'imported' + (embedded ? ' (file also carried user amp/IR data, which was not imported)' : '');
  }
  task(label, fn) {
    const prog = (done, total) => this.bump({task: {label, done, total}});
    (async () => {
      try { await fn(prog); this.bump({task: null}); }
      catch (e) { console.error(e); this.bump({task: null, error: `${label} failed: ${e.message}`}); }
    })();
  }
  async uploadIr(slot, name, wav, method = 'app') {
    if (!['app', 'optimised'].includes(method)) throw new Error(`unknown conversion method ${method}`);
    const p = this.need();
    const {data} = await convert('ir', method, wav);       // conversion errors go back to the dialog
    this.task(`Uploading IR to slot ${slot + 1}`, async prog => {
      await p.uploadIr(slot, data, name, prog);
      this.s.ir[slot] = await p.irTable(slot); this.bump();
    });
  }
  uploadNam(slot, name, nam, method = 'optimised') {
    if (method !== 'optimised')
      throw new Error('Stomp Manager (original) NAM conversion needs the Python bridge (it uses Stomp Manager’s converter). Choose Accurate.');
    const p = this.need(), split = !!this.s.split_captures;
    if (!(slot >= 0 && slot < (split ? 20 : 10))) throw new Error('invalid capture slot');
    const fxSlot = slot - (split ? 10 : 0);
    this.task(`Uploading NAM to slot ${slot + 1}`, async prog => {
      this.bump({task: {label: 'Converting NAM (accurate fit, a few minutes)', done: 0, total: 1}});
      const {data, factor} = await convert('nam', method, nam,
        (done, total) => this.bump({task: {label: 'Converting NAM (accurate fit)', done, total}}));
      await p.uploadNam(slot, data, name, factor, prog);
      if (this.s.capture_slots) await this.modelLock.run(async () => {
        const rec = await p.readEdit();
        for (const effectSlot of [7, 3]) {
          const [spare, carrier] = FX_SLOTS[effectSlot];
          if (fxSlot >= 0 && fxSlot < 10 && (rec[effectSlot] & 63) === carrier && rec[spare] === 0x60 + fxSlot)
            await p.setFxOverride(effectSlot, 16 + fxSlot);
        }
      });
      this.s.nam[slot] = await p.namName(slot); this.bump();
    });
  }
}

// ---- /api router: same requests and replies as editor/server.py
let app = null;
const json = (obj, status = 200) => new Response(JSON.stringify(obj), {status, headers: {'Content-Type': 'application/json'}});
async function bodyBytes(options) {
  const b = options.body;
  if (b == null) return new Uint8Array();
  if (b instanceof ArrayBuffer) return new Uint8Array(b.slice(0));
  if (ArrayBuffer.isView(b)) return new Uint8Array(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength));
  return new TextEncoder().encode(String(b));
}
async function handle(path, options = {}) {
  const u = new URL(path, 'http://direct'), q = Object.fromEntries(u.searchParams), method = (options.method || 'GET').toUpperCase();
  try {
    if (method === 'GET') {
      if (u.pathname === '/api/state') return json(await app.snapshot(Number(q.since ?? -1)));
      if (u.pathname === '/api/catalog') return json(app.CAT);
      if (u.pathname === '/api/diagnostics') return json(await app.need().diagnostics());
      if (u.pathname === '/api/export') {
        const [name, data] = await app.exportPreset(Number(q.index));
        return new Response(data, {headers: {'Content-Type': 'application/octet-stream', 'Content-Disposition': `attachment; filename="${name}"`}});
      }
      return json({error: 'not found'}, 404);
    }
    if (u.pathname === '/api/connect') { app.connect(); return json({ok: true}); }
    const body = await bodyBytes(options);
    if (u.pathname === '/api/ir') { await app.uploadIr(Number(q.slot), q.name ?? 'IR', body, q.method ?? 'app'); return json({ok: true}); }
    if (u.pathname === '/api/nam') { app.uploadNam(Number(q.slot), q.name ?? 'NAM', body, q.method ?? 'optimised'); return json({ok: true}); }
    if (u.pathname === '/api/import') return json({ok: true, message: await app.importPreset(Number(q.index), body)});
    const a = body.length ? JSON.parse(new TextDecoder().decode(body)) : {};
    if (u.pathname === '/api/select') await app.select(Number(a.index));
    else if (u.pathname === '/api/cc') app.cc(Number(a.cc), Number(a.value), a.focus ?? null);
    else if (u.pathname === '/api/model') await app.model(Number(a.slot), Number(a.model));
    else if (u.pathname === '/api/chain') await app.chain(a.order);
    else if (u.pathname === '/api/save') await app.save(Number(a.index), String(a.name));
    else if (u.pathname === '/api/dismiss') app.bump({error: null});
    else return json({error: 'not found'}, 404);
    return json({ok: true});
  } catch (e) {
    console.error(e);
    return json({error: e.message}, 500);
  }
}

window.DirectPedal = {
  supported: () => !!navigator.requestMIDIAccess,
  start(catalog) { app = new App(catalog); app.connect(); return handle; },
  handle,
  // exported for tests
  _internals: {pack7, unpack7, bulkHeader, sysex, bulkMessages, irEntry, namNameRecord, exportJmePreset, importJmePreset, Pedal, App},
};
})();
