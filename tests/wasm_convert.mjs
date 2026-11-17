// Run editor/static/stomp_convert.wasm in Node (the same module the browser editor uses).
// usage: node tests/wasm_convert.mjs <ir|nam> <input> <output.bin> [app|optimised]
import { readFileSync, writeFileSync } from 'node:fs';

const [kind, input, output, method = 'optimised'] = process.argv.slice(2);
const bytes = readFileSync(new URL('../editor/static/stomp_convert.wasm', import.meta.url));
let last = 0;
const { instance } = await WebAssembly.instantiate(bytes, {
  env: { progress: (done, total) => { const now = Date.now(); if (now - last > 5000) { last = now; console.error(`progress ${done}/${total}`); } } },
});
const w = instance.exports, file = readFileSync(input);
const ptr = w.alloc(file.length);
new Uint8Array(w.memory.buffer, ptr, file.length).set(file);
const t0 = Date.now();
let rc;
try {
  rc = kind === 'ir' ? w.ir_convert(ptr, file.length, method === 'app' ? 0 : 1) : w.nam_convert(ptr, file.length);
} catch (e) {
  const msg = new TextDecoder().decode(new Uint8Array(w.memory.buffer, w.err_ptr(), w.err_len()));
  console.error('trap:', msg || e.message); process.exit(3);
}
if (rc !== 0) {
  console.error('error:', new TextDecoder().decode(new Uint8Array(w.memory.buffer, w.err_ptr(), w.err_len())));
  process.exit(2);
}
writeFileSync(output, new Uint8Array(w.memory.buffer, w.out_ptr(), w.out_len()).slice());
console.error(`ok ${w.out_len()} bytes in ${((Date.now() - t0) / 1000).toFixed(1)} s`);
