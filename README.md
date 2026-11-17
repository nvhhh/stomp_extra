# Stomp Extra: custom firmware and editor for the Soran Dual Stomp Lite

Custom firmware (CFW) for the **Soran Dual Stomp Lite** on stock firmware V1.1.1, plus a browser
editor. The CFW is the stock firmware with every feature kept; it only adds to it.

**Latest release: [0.6.0 — 1024-tap user cab IRs](https://github.com/nvhhh/stomp_extra/releases/latest)**
· **Editor: https://nvhhh.github.io/stomp_extra/**

## What you get

- **Longer user cab IRs.** The 10 user IR slots play 21 ms of the IR (1024 samples) instead
  of 8 ms (384 samples). Low end and cab resonance are much closer to the original IR, with no
  added latency. ([details](docs/LONG-IR.md))
- **20 capture slots.** USER AMP 01–10 for the AMP block, FX 01–10 for EQ and MOD.
- **OD/FX models in more slots**, selectable on the pedal.
- **Faster capture processing**, so AMP + EQ + MOD captures can run together, with overload
  protection: if the DSP runs out of time, captures switch to dry instead of crashing.
- **Editor in the browser, nothing to install:** every preset and parameter, drag-and-drop effect
  order, NAM and IR import, `.jmePreset` import/export.

Built-in amps, cabs, effects, looper, drums, USB audio and Bluetooth are the vendor's own code,
unchanged.

## Flashing

> **Back up first.** Flashing erases part of the capture storage (at least FX 01) and can clear
> user IR/NAM slots. Keep your `.nam` and `.wav` files so you can re-import them.

1. **Back up** presets, captures and the current edit (close the editor bridge first):
   `.venv/Scripts/python tools/test_partition_capture_hardware.py backup`
   This writes `backups/library-<time>.zip`.
2. **Enter DFU mode:** hold **Left + Right** while powering on.
3. **Flash** the `.bin` from the release, with the official Soran *Device Firmware Updater* or with
   `.venv/Scripts/python cfw.py flash soran-cfw-<version>.bin`.
4. **Power-cycle** normally, without holding any footswitch.
5. **Restore** captures and the edit:
   `.venv/Scripts/python tools/restore_capture_session.py backups/library-<time>.zip`
   Then re-import any empty IR/NAM slot.

**Recovery:** DFU mode lives in a separate bootloader that the CFW never touches. If anything goes
wrong, enter DFU mode and flash the stock firmware or an earlier release.

## Editor

Open **https://nvhhh.github.io/stomp_extra/** in **Chrome or Edge** on a computer:

1. Connect the pedal by USB and close Stomp Manager.
2. Click **Connect pedal**, and allow MIDI device control when the browser asks.

Nothing to install. The page talks to the pedal over USB MIDI, and NAM/IR files are converted in
the browser (open-stomp, compiled to WebAssembly); they never leave your computer. An Accurate NAM
conversion takes about 4 minutes in the browser; keep the tab open until it finishes.

**Optional Python bridge.** Only needed for the Stomp Manager (original) NAM conversion, or for a
faster Accurate NAM fit (about 40 s). Set up once on Windows:

```sh
git clone https://github.com/nvhhh/stomp_extra && cd stomp_extra
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
```

Then run `.venv/Scripts/python editor/server.py --pages`. It opens the editor connected to the bridge.
The original NAM conversion needs Stomp Manager installed (it uses its converter DLL); set
`SORAN_NAM_DLL` if it isn't found.

### Which conversion to choose

The import dialog offers two conversions and remembers your choice separately for NAM and IR.

| | NAM | IR |
|---|---|---|
| **Accurate** | **Default, recommended.** Fits the pedal's filters to the whole model; about 4 minutes in the browser, 40 s with the bridge. | Fits the IR into 8 ms. Only for stock / 0.5.2 firmware. |
| **Stomp Manager (original)** | Same result as Stomp Manager. Python bridge only. | **Default, recommended on 0.6.0.** Uploads the IR's real start, which 0.6.0 plays as 21 ms. |

## Credits and license notes

NAM and IR conversion uses [open-stomp](https://github.com/JackMechem/open-stomp-lib)
(© 2026 The open-stomp contributors, MIT OR Apache-2.0), see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Soran's firmware and Stomp Manager files are not
included in this repository.

## For developers

```sh
# put the stock JME-EN_V1.1.1_modified.bin in firmware/stock/ (from the Soran updater zip)
.venv/Scripts/python cfw.py build -c cfw-long-ir-test.toml     # current release config
.venv/Scripts/python cfw.py selftest -c cfw-long-ir-test.toml  # format, patch and simulated DFU checks
```

`cfw.py` also has `info`, `diff`, `unpack`/`pack`, `devices`/`query` and `flash`. Docs:
[flash map, file format and DFU protocol](docs/FORMAT.md), [USB MIDI protocol](docs/PROTOCOL.md),
[long IRs](docs/LONG-IR.md), [captures](docs/PARTITIONED-CAPTURE.md),
[patches](patches/README.md). Emulator tests are in `tests/`. The browser converter
(`editor/static/stomp_convert.wasm`) is rebuilt with `python tools/build_converter_wasm.py` (needs Rust).
