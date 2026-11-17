# Third-party notices

## open-stomp

- Project: open-stomp (`open_stomp` Python package), https://github.com/JackMechem/open-stomp-lib
- Version used: 0.6.1
- Copyright (c) 2026 The open-stomp contributors
- License: MIT OR Apache-2.0, at the licensee's option. This project uses it under the MIT
  license. Both license texts are reproduced in [`licenses/open-stomp/`](licenses/open-stomp/).
  The project has no Apache-2.0 NOTICE file.

**How it is used.** The editor's NAM and IR import uses open-stomp to convert `.nam` models and
`.wav` cab IRs into the data the pedal plays:
- "Accurate" conversion is open-stomp's fitted (`optimised`) conversion.
- "Stomp Manager (original)" uses open-stomp's reimplementation of the official conversion.

It is used in two places:
- **Python bridge:** `nuxfw/namconv.py` and `nuxfw/irconv.py` call the `open_stomp` package, which
  `requirements.txt` installs as the prebuilt Windows wheel from the open-stomp GitHub release.
- **Browser editor:** `editor/static/stomp_convert.wasm` is open-stomp 0.6.1 compiled to WebAssembly
  (`tools/build_converter_wasm.py`, wrapper in `editor/wasm/`). One change was made to its source:
  the optimiser's thread pool runs inline when only one thread is available, since browsers' WebAssembly
  has no threads. The conversion results are otherwise open-stomp's own.

The pedal-side behavior these conversions rely on (two 512-tap filters around a fixed saturation for
NAM, 384 played taps for IRs) was documented by the open-stomp project.

## Rust crates in the WebAssembly converter

`stomp_convert.wasm` also contains these crates, each used under its MIT license. Their license
texts and copyright notices are in [`licenses/wasm-crates.txt`](licenses/wasm-crates.txt).

| Crate | License |
|---|---|
| itoa | MIT OR Apache-2.0 |
| memchr | Unlicense OR MIT |
| num-complex, num-integer, num-traits | MIT OR Apache-2.0 |
| primal-check | MIT OR Apache-2.0 |
| rustfft, strength_reduce, transpose | MIT OR Apache-2.0 |
| serde_core, serde_json | MIT OR Apache-2.0 |
| zmij | MIT |
