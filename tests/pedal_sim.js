// A simulated pedal behind a fake Web MIDI access, then the editor's App connected to it.
const fs = require('fs'), vm = require('vm'), path = require('path');
const [pedalJs, workerJs, wasmPath, irPath] = process.argv.slice(1);
const hex = b => Buffer.from(b).toString('hex');
let P;                                                   // pedal.js internals (encoders)
// ---- simulated pedal state
const presets = Array.from({length: 99}, (_, i) => { const r = new Uint8Array(98); r.set([1, 2, 3, 4, 5, 6, 7, 8]);
  r.set(Buffer.from(('Preset ' + (i + 1)).padEnd(16, '\0')), 82); r.set([6, 0, 1, 2, 7, 3, 4, 5], 70); r[66] = 50; return r; });
let edit = Uint8Array.from(presets[4]), current = 4;
const irs = Array.from({length: 10}, (_, i) => i === 1 ? 'Marshall Box - 9' : null), irData = {};
const nams = Array.from({length: 20}, (_, i) => 'USER AMP ' + String(i % 10 + 1).padStart(2, '0')), namData = {};
const sent = [];
const ccOffset = cc => cc < 8 ? cc : cc === 58 ? 66 : null;
const reply = (cmd, sub, payload) => Uint8Array.from([0xF0, 0, 0x21, 0x7A, 0x70, cmd, sub, ...payload, 0xF7]);
const text = (s, n) => [...Buffer.from(s.padEnd(n, '\0'))];
function pedal(d) {
  sent.push(hex(d));
  if (d[0] === 0xC0) { current = d[1]; edit = Uint8Array.from(presets[current]); return [Uint8Array.from([0xC0, current])]; }
  if (d[0] === 0xB0) { const off = ccOffset(d[1]); if (off != null) edit[off] = d[2]; return []; }
  if (d[4] === 0x00) return [Uint8Array.from([0xF0, 0, 0x21, 0x7A, 0x10, ...text('V1.1.1', 32), ...text('JME-01', 8), 0xF7])];
  if (d[4] === 0x40) return [Uint8Array.from([0xF0, 0, 0x21, 0x7A, 0x10, ...text('202606041731', 16), ...text('V0', 16), 0xF7])];
  const [cmd, sub] = [d[5], d[6]], body = d.subarray(7, d.length - 1), u = P.unpack7(body);
  if ([0x14, 0x15, 0x18, 0x19].includes(cmd)) return [reply(cmd, 2, cmd === 0x15 ? [current, 0, 0, 0] : [1, 2, 3])];
  if (cmd === 0x30 && sub === 0) return [reply(0x30, 2, [...Buffer.from('FXA'), 3, 0, 0, 0])];
  if (cmd === 0x0C) return [reply(0x0C, 2, P.pack7([...P.bulkHeader(0, 0, 0, 0, 98), ...edit]))];
  if (cmd === 0x0B && sub === 0) return [reply(0x0B, 2, P.pack7([...P.bulkHeader(u[0], 0, 0, 0, 98), ...presets[u[0]]]))];
  if (cmd === 0x0B && sub === 1) { presets[u[0]] = u.slice(12, 110); return [reply(0x0B, 3, P.pack7(u.slice(0, 12)))]; }
  if (cmd === 0x12) { presets[body[0]].set(body.subarray(1, 17), 82); return [reply(0x12, 3, [body[0]])]; }
  if (cmd === 0x0D && sub === 1) { edit.set(body, 70); return [reply(0x0D, 2, body)]; }
  if (cmd === 0x09 && sub === 0) return [reply(0x09, 2, [body[0], ...P.pack7(P.irEntry(irs[body[0]]))])];
  if (cmd === 0x09 && sub === 1) {
    const e = P.unpack7(body.subarray(1));
    irs[body[0]] = e[0] ? Buffer.from(e.subarray(4, 20)).toString().replace(/\0.*$/s, '') : null;
    return [reply(0x09, 3, [body[0]])];
  }
  if (cmd === 0x10 && sub === 1) {
    const off = new DataView(u.buffer).getUint32(4, true);
    (irData[u[0]] ??= new Uint8Array(8192)).set(u.subarray(12), off);
    return [reply(0x10, 3, P.pack7(u.slice(0, 12)))];
  }
  if (cmd === 0x58 && sub === 0) {
    const r = P.namNameRecord(nams[u[1]], 1);
    return [reply(0x58, 2, P.pack7([...P.bulkHeader(0, u[1], 4, 0, 128), ...r]))];
  }
  if (cmd === 0x58 && sub === 1) {
    const off = new DataView(u.buffer).getUint32(4, true);
    if (u[2] === 3) nams[u[1]] = Buffer.from(u.subarray(12, 44)).toString().replace(/\0.*$/s, '');
    else (namData[u[1]] ??= new Uint8Array(8192)).set(u.subarray(12), off);
    return [reply(0x58, 3, P.pack7(u.slice(0, 12)))];
  }
  return [];
}
// ---- fake Web MIDI
const port = (name, type) => ({name, type, state: 'connected', onmidimessage: null, open: async () => {}, close() {}});
const input = port('JME STOMPBOX', 'input'), output = port('JME STOMPBOX', 'output');
output.send = d => { for (const r of pedal(Uint8Array.from(d))) setTimeout(() => input.onmidimessage?.({data: r}), 1); };
const access = {inputs: new Map([['i', input]]), outputs: new Map([['o', output]]), onstatechange: null};
// ---- Worker shim running convert-worker.js with the real wasm
class Worker {
  constructor() {
    this.ctx = {self: {location: {href: 'http://x/convert-worker.js'}, postMessage: m => setTimeout(() => this.onmessage?.({data: m}))},
      fetch: async () => ({arrayBuffer: async () => fs.readFileSync(wasmPath)}), WebAssembly, performance, TextDecoder, URL};
    vm.createContext(this.ctx); vm.runInContext(fs.readFileSync(workerJs, 'utf8'), this.ctx);
  }
  postMessage(m) { this.ctx.self.onmessage({data: m}); }
  terminate() {}
}
const ctx = {window: {}, console, URL, TextEncoder, TextDecoder, Response, setTimeout, clearTimeout, performance, Worker,
             navigator: {requestMIDIAccess: async () => access}, document: {baseURI: 'http://x/'}};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(pedalJs, 'utf8'), ctx);
P = ctx.window.DirectPedal._internals;
const catalog = JSON.parse(fs.readFileSync(path.join(path.dirname(pedalJs), '..', 'catalog.json'), 'utf8'));
const pause = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const api = ctx.window.DirectPedal.start(catalog);
  const get = async p => (await api(p)).json(), post = async (p, b) => (await api(p, {method: 'POST', body: b})).json();
  const idle = async () => { let s; for (let i = 0; i < 500; i++) { s = await get('/api/state'); if (s.connected && !s.task) break; await pause(20); } return s; };
  let s = await idle();
  const out = {connected: s.connected, error: s.error, info: s.info, current: s.current, presets: [s.presets[0], s.presets[98]],
               ir: s.ir.map(e => e.name), nam0: s.nam[0], nam_count: s.nam.length, split: s.split_captures};
  out.cc = await post('/api/cc', JSON.stringify({cc: 58, value: 77}));
  out.vol = (await get('/api/state')).edit.slice(132, 134);
  out.chain = await post('/api/chain', JSON.stringify({order: [0, 6, 1, 2, 7, 3, 4, 5]}));
  out.save = await post('/api/save', JSON.stringify({index: 9, name: 'Web MIDI test'}));
  out.saved = hex(presets[9]);
  out.select = await post('/api/select', JSON.stringify({index: 3}));
  out.exp = (await api('/api/export?index=3')).headers.get('Content-Disposition');
  out.ir_up = await post('/api/ir?slot=2&name=Test%20IR&method=app', fs.readFileSync(irPath));
  await pause(50); s = await idle();
  out.ir_after = s.ir[2]; out.ir_data = irData[2] ? hex(irData[2]) : null; out.err = s.error;
  out.nam_app = await post('/api/nam?slot=0&name=x&method=app', '{}');
  out.sent = sent.length;
  process.stdout.write(JSON.stringify(out));
  process.exit(0);
})().catch(e => { console.error(e); process.exit(1); });
