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
- **Editor:** every preset and parameter, drag-and-drop effect order, NAM and IR import,
  `.jmePreset` import/export.

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

Setup (Windows, once):

```sh
git clone https://github.com/nvhhh/stomp_extra && cd stomp_extra
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
```

Each time:

1. Connect the pedal by USB and close Stomp Manager.
2. Start the bridge: `.venv/Scripts/python editor/server.py --pages`
3. Open **https://nvhhh.github.io/stomp_extra/** in Chrome or Edge, click **Connect bridge**, and
   allow local network access if asked.

The bridge talks to the pedal over USB and runs the NAM/IR conversion on your PC. Files go
straight to the bridge, never to GitHub. If the browser blocks the connection, use the local URL
the bridge prints (or run `editor/server.py` without `--pages`). NAM import needs Stomp Manager
installed (it uses its converter DLL); set `SORAN_NAM_DLL` if it isn't found.

### Which conversion to choose

The import dialog offers two conversions and remembers your choice separately for NAM and IR.

| | NAM | IR |
|---|---|---|
| **Accurate** | **Default, recommended.** Fits the pedal's filters to the whole model; takes about a minute. | Fits the IR into 8 ms. Only for stock / 0.5.2 firmware. |
| **Stomp Manager (original)** | Same result as Stomp Manager. | **Default, recommended on 0.6.0.** Uploads the IR's real start, which 0.6.0 plays as 21 ms. |

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
[patches](patches/README.md). Emulator tests are in `tests/`.
