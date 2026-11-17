# FX Anywhere 0.2.0-fx — Dual Stomp Lite, stock base V1.1.1

For the newer, unflashed wheel and EQ/MOD capture development build, see
[FX Controls](FX-CONTROLS.md). This document describes the installed 0.2 version.

This experimental firmware adds all 16 OD/FX models to the **EQ, MOD and DEL**
model lists in the custom Stomp Editor. Each slot has independent parameters and
DSP state. The original OD/FX slot remains available, allowing four OD/FX blocks.
Native EQ, modulation and delay choices remain in their lists.

**Installed on the connected pedal; boot and capability response verified. DSP
behavior has been tested in CPU emulation, but physical audio has not been tested.**
Emulation does not establish real-time CPU headroom, SDRAM/cache behavior, or
physical audio quality. The patch uses SDRAM inferred to be unused by static
analysis; this allocation still needs verification during hardware testing.

## Install and use

1. Keep `firmware/stock/JME-EN_V1.1.1_modified.bin` available for rollback.
   Back up presets using the editor before updating: the firmware package includes
   the vendor's factory preset region, so an update can overwrite stored presets.
2. Put the pedal in DFU mode by powering on with Left + Right held.
3. Run `.venv/Scripts/python cfw.py flash build/soran-cfw-0.2.0-fx-on-1.1.1.bin`,
   or select that file in the official Device Firmware Updater.
4. Restart the pedal normally. Run `.venv/Scripts/python editor/server.py`,
   open `http://127.0.0.1:8765`, and reconnect. Close Stomp Manager to release MIDI.
5. Select EQ, MOD or DEL. Its model list now includes `OD/FX · ...` entries.
   Pick one, adjust the named parameters, and save the preset as usual.
   Choose a native entry in the custom editor to remove that slot's override.

The editor probes for this firmware extension before showing the extra choices.
They are intentionally hidden on stock firmware. Save, recall and `.jmePreset`
export/import preserve the three override bytes.

### Rearranging the signal chain

Drag a block onto another position, or select it and use **Left / Right** below
the chain. **Default order** restores Gate → OD/FX → Amp → Cab → EQ → Mod →
Delay → Reverb. The change applies live; **Save** stores it with the preset.
An OD/FX override moves with its EQ/MOD/DEL slot and keeps its parameters.
This uses the existing vendor `0x0D` command, so no additional firmware update
is required. Live command/readback was verified on the connected pedal.

**The pedal display and Soran Stomp Manager do not gain new model names.** They
show the native carrier: 6-band EQ, Flanger or Mod Delay. Use this custom editor
to select and remove overrides. Selecting another native model on the pedal
temporarily makes that slot native; returning to its carrier reactivates the
stored override. Stock firmware ignores the override bytes and plays the carrier
instead, so custom presets need adjustment after a rollback.

Changing an OD/FX model initializes its coefficients in bounded chunks (at most
512 bytes copied or cleared per audio block). During this short preparation
period the slot passes dry audio; processing starts when initialization finishes.
Changes may be audible. New selections start with middle parameter values.

The patch leaves the DFU image, Tiny Stomp app, assets, factory preset data and
reserved app tail byte-identical to stock. Recovery still depends on the device
being able to enter its existing DFU mode; rollback has not been hardware-tested.

## Rebuild and validate

```powershell
.venv/Scripts/python -m pip install -r requirements-firmware.txt
.venv/Scripts/python patches/fx-anywhere/build_patch.py
.venv/Scripts/python cfw.py build -c cfw-fx-anywhere.toml
.venv/Scripts/python cfw.py selftest -c cfw-fx-anywhere.toml
.venv/Scripts/python tests/test_fx_anywhere.py
.venv/Scripts/python tests/test_fx_editor.py
.venv/Scripts/python tests/test_jme_capture.py
```

The builder checks the exact stock SHA-256, emulates its data initialization
instead of relying on a saved RAM dump, validates coefficient descriptor bounds,
and emits guarded patches, generated assembly, a symbol map and payload.
The payload is deterministic; container build tags include the current time.

The CPU tests run the actual assembled Thumb code and vendor DSP. They compare
all 16 models in all three destination slots with separately initialized stock
engines, check interleaved instances, initialization bounds, model switches,
native dispatch arguments, parameter limits, preset recall and SysEx handling.
Shared coefficient tables are loaded using the vendor's startup routine.
Unicorn's Cortex-M7 model lacks the double-precision instructions used by some
stock models, so DSP tests use its ARM A15 Thumb/VFP execution model. This is
functional instruction testing, not a simulation of the physical M7's timing.

## Implementation

* Code/tables start at ITCM `0x38100`, below `0x3B000`.
* Extra A state: `0x3B000`, `0x3C000`, `0x3D000`, each 4 KiB.
* Extra B state: `0x81FA0000`, `0x81FA8000`, `0x81FB0000`, each 32 KiB.
* Metadata/parameter shadows: `0x3E020`, `0x3E040`, `0x3E060`.
* 31 OD/FX literal pointers now address four-entry instance tables. Entry zero
  retains the stock state addresses. Stock initializer `0x14244` remains unchanged.
* The guarded call at `0x3090E` runs a boot hook after IAR data initialization.
  It installs 22 native-model dispatch wrappers and then tail-calls stock main.
* Preset bytes 67/68/69 encode EQ/MOD/DEL overrides as `0x50 + OD/FX model`.
  Other values select native behavior. The carrier must also match.
* OD parameters are clamped to 99, matching the stock OD parameter update path.

### SysEx extension

Read: `F0 00 21 7A 70 30 00 F7`.

Write: `F0 00 21 7A 70 30 01 <slot> <choice> F7`, where slot is 7/3/4 and
choice is 0 for native or 1–16 for OD/FX model 0–15. Writes affect the live edit
buffer only. Select the carrier using the existing CC first; saving is explicit.

Reply: standard command `30`, sub 2 (read) or 3 (write), payload
`46 58 41 01 <EQ marker> <MOD marker> <DEL marker>` (`FXA`, protocol version 1).
Malformed writes are ignored. The host requires this capability signature.

## Hardware verification still required

Start with a backed-up test preset and low monitoring volume. Check clean boot,
native presets, each new slot independently, repeated instances of one effect,
all four instances together, bypass, preset save/recall across power cycling,
USB audio, and worst-case chains with amp/cab processing, looper and drums.
Listen for dropouts and verify DFU rollback before treating the build as reliable
for performance use.
