# soran-cfw: custom firmware for the Soran Dual Stomp Lite

A reproducible build pipeline for custom firmware on the Soran Dual Stomp Lite (JME-02), and by
extension the Dual Stomp and Tiny Stomp, which share the same NUX "JME" platform.

The latest firmware is **0.6.0-longir-test**, configured in `cfw-long-ir-test.toml`. It is
0.5.2 plus **1024-tap user cab IRs**: the 10 IR slots play the IR's first 1024 samples (21.3 ms)
instead of 384 (8 ms), with no added latency. On eleven cab IRs the error of what the pedal plays
dropped from 1.43 to 0.11 dB rms (0.20 dB in the 31–160 Hz bands). It uses partitioned FFT
convolution, which has the same output as a direct 1024-tap filter, and adds about 700 emulator
instructions per audio callback. Built-in cabs and everything else behave exactly as in 0.5.2. See
[long-IR design and results](docs/LONG-IR.md). On the pedal, 60 s with a user NAM amp, a user IR
and a MOD capture ran at a median of 81k of the 100k-cycle budget (highest sampled 92k), with no
overruns or guard trips. The full AMP + EQ + MOD capture setup hasn't been measured on this build yet.

The previous release, **0.5.2-deadline** (`cfw-fx-fixed-deadline.toml`), added expanded effects,
20 capture slots (10 USER AMP slots for AMP and 10 FX slots for EQ/MOD), and optimized capture
processing. See [capture implementation and hardware results](docs/PARTITIONED-CAPTURE.md).
Earlier configurations are retained for development history; the default
`cfw.toml` builds the original feature-preserving baseline below.

**Before flashing any CFW**, back up your presets, user captures, IRs and NAMs. A full image
erases part of the user capture storage (FX01 on recent builds), so restore captures afterwards
(`tools/restore_capture_session.py`), and re-upload IRs/NAMs if any slot comes back empty.

The editor supports effect-chain rearrangement, editable capture names during
NAM import (defaulting to the filename), and separate AMP/FX libraries with
improved contrast and readable capture names.

The CFW is the **stock V1.1.1 firmware with every feature kept**, plus a build-info tag in unused
flash and a guarded patch system for adding features. Nothing is rewritten from scratch: the DSP
engine, amp/effect models, NAM/IR loader, looper, drums, USB audio and BLE stay the vendor's code.

## Quick start

```sh
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
# put the stock JME-EN_V1.1.1_modified.bin in firmware/stock/ (from the Soran updater zip)
.venv/Scripts/python cfw.py selftest      # verifies format, build and simulated DFU
.venv/Scripts/python cfw.py build         # -> build/soran-cfw-0.1.0-on-1.1.1.bin
```

Flash, either with:

* **this tool:** power the pedal on while holding **Left + Right** (DFU mode), then
  `.venv/Scripts/python cfw.py flash build/soran-cfw-0.1.0-on-1.1.1.bin`
* **or the official Soran "Device Firmware Updater":** the output uses the same container
  format, so select the CFW `.bin` there.

**Recovery:** DFU mode lives in a separate bootloader that the CFW never modifies. If anything
goes wrong, enter DFU mode again and flash the stock `firmware/stock/JME-EN_V1.1.1_modified.bin`.

## Stomp Editor (presets, effects, NAM / IR import)

```sh
.venv/Scripts/python editor/server.py      # opens http://127.0.0.1:8765
```

It's a local editor that talks to the pedal over USB MIDI:
- browse and recall all 99 presets; edit every block (model, on/off, every parameter, preset volume)
- rearrange all eight effects by dragging blocks, or select a block and use Left/Right;
  changes apply live, and Save stores the order with the preset (no extra firmware flash needed)
- rename and save (also to another slot); export and import Stomp Manager `.jmePreset` files
- import NAM captures into the 10 user‑amp slots, and cab IRs (.wav) into the 10 IR slots

Protocol details are in `docs/PROTOCOL.md`. `tests/test_jme_capture.py` checks the implementation
against recorded Stomp Manager traffic.

**NAM / IR conversion.** Choose the conversion in the import dialog. NAM defaults to
Accurate and IRs to Stomp Manager (original); the last choice for each is remembered. **Accurate** uses the [open-stomp](https://github.com/JackMechem/open-stomp-lib)
converter (MIT / Apache-2.0, installed by `requirements.txt` on Windows). The pedal does not run NAM
directly: a user amp is two 512-tap filters around a fixed saturation, and on stock/0.5.2 an IR slot
plays only 384 taps (8 ms). Accurate fits those to the whole model or IR instead of taking the start
of the file. On ten Marshall cab IRs it cut the error of what a 384-tap slot plays from 3.25 to
1.54 dB rms (`tests/test_conversion.py`); NAM fitting takes about a minute per model.
**Stomp Manager (original)** reproduces the official conversion (IR within 1e-7 of a captured
upload; NAM within 0.015 %, using the official excitation read from Stomp Manager's converter DLL,
set `SORAN_NAM_DLL` if it isn't found). Without open-stomp, imports fall back to the old path.

**On 0.6.0, import IRs with Stomp Manager (original)**, the default. It uploads the IR's real first 2048
samples, of which 0.6.0 plays 1024. Accurate squeezes the IR into 384 taps, so it gains nothing there.
For NAM, Accurate stays the better choice on every firmware.
Close Stomp Manager while using the editor.

## GitHub Pages editor

Open **https://nvhhh.github.io/stomp_extra/**. The interface is hosted on Pages;
USB MIDI and NAM conversion run on your Windows PC through the local bridge.
Files are sent directly to the bridge, not uploaded to GitHub.

1. Clone this repository and install Python dependencies as described above.
2. Connect the pedal by USB and close other pedal editors/bridge instances.
3. Run `.venv/Scripts/python editor/server.py --pages` from the project folder.
4. In Chrome or Edge, click **Connect bridge** and allow local network access
   if prompted. The default port is 8765; use `--port 8766` and the matching
   port in the page if needed.

NAM imports still require Stomp Manager's converter DLL (see above).
If browser policy blocks local access, use the local editor URL printed by the
bridge. The bridge listens only on loopback and accepts the hosted origin only
when started with `--pages`. The workflow deploys editor changes pushed to main.

## Credits

NAM and IR conversion uses [open-stomp](https://github.com/JackMechem/open-stomp-lib)
(© 2026 The open-stomp contributors, MIT OR Apache-2.0). It also documented the pedal-side
NAM/IR structure that the Accurate conversion relies on. See
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [`licenses/open-stomp/`](licenses/open-stomp/).

## CLI reference

| | |
|---|---|
| `cfw.py info <bin>` | container details, region map, CFW tag |
| `cfw.py unpack <bin> <dir>` / `pack <dir> <bin>` | raw editing of the flat image |
| `cfw.py build` | stock + `cfw.toml` patches → custom `.bin` |
| `cfw.py diff <a> <b>` | changed ranges, mapped to regions |
| `cfw.py devices` / `query` | find the pedal / read version in DFU mode |
| `cfw.py flash <bin>` | write over USB HID in DFU mode |

## Layout

```
cfw.py            CLI
cfw.toml          build config (base firmware + patch list)
nuxfw/            container format, flash layout, patch engine, DFU transport + simulator
patches/          feature patches (see patches/README.md)
tools/            analysis helpers (disassembler, structure survey)
docs/FORMAT.md    everything reverse engineered: hardware, flash map, file format, DFU protocol
```

Vendor binaries (`firmware/stock/*.bin`, `vendor/`) are Soran's and are gitignored, not
redistributed.
