// Converts one NAM or IR file with stomp_convert.wasm (open-stomp, MIT / Apache-2.0) off the page's
// main thread. Message in: {kind: 'ir'|'nam', method: 'app'|'optimised', bytes: Uint8Array}.
// Messages out: {progress: [done, total]} while fitting, then {data: Uint8Array(8192), factor} or {error}.
'use strict';
let wasmModule = null;

self.onmessage = async e => {
  const {kind, method, bytes} = e.data;
  let w = null;
  try {
    wasmModule ??= await WebAssembly.compile(await (await fetch(new URL('stomp_convert.wasm', self.location.href))).arrayBuffer());
    let last = 0;
    const instance = await WebAssembly.instantiate(wasmModule, {env: {progress: (done, total) => {
      const now = performance.now();
      if (now - last > 250 || done === total) { last = now; self.postMessage({progress: [done, total]}); }
    }}});
    w = instance.exports;
    const ptr = w.alloc(bytes.length);
    new Uint8Array(w.memory.buffer, ptr, bytes.length).set(bytes);
    const rc = kind === 'ir' ? w.ir_convert(ptr, bytes.length, method === 'optimised' ? 1 : 0)
                             : w.nam_convert(ptr, bytes.length);
    if (rc !== 0) throw new Error(message(w) || 'conversion failed');
    const out = new Uint8Array(w.memory.buffer, w.out_ptr(), w.out_len()).slice();
    const data = out.slice(0, 8192);
    const factor = kind === 'nam' ? new DataView(out.buffer).getFloat32(8192, true) : 1;
    self.postMessage({data, factor}, [data.buffer]);
  } catch (err) {
    // A Rust panic traps the instance; its message was stored before the trap.
    self.postMessage({error: (w && message(w)) || err.message || String(err)});
  }
};

function message(w) {
  try { return new TextDecoder().decode(new Uint8Array(w.memory.buffer, w.err_ptr(), w.err_len())); } catch { return ''; }
}
