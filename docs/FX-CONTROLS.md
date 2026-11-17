# FX Controls 0.3.1-dev ? wheel crash correction

The installed 0.3.0 build was reported to freeze when scrolling from 10-band EQ
to the first OD/FX model, with MIDI replies stopping. The 0.3.1 candidate replaces
an unaligned word read at 0x2907a and packed word store with explicit byte
accesses. A regression executes the old image and detects that read at the
reported transition; all ten firmware tests and DFU-package checks pass for
0.3.1. The cause is not hardware-confirmed (no fault-register capture), and the
0.3.1 DFU transfer completed (29,937 records, no reported write errors).
Normal boot and the physical wheel fix remain unverified.

Candidate: `build/soran-cfw-0.3.1-dev-on-1.1.1.bin`.

# FX Controls 0.3.0-dev

Development firmware for Dual Stomp Lite, based on stock V1.1.1.
Output: `build/soran-cfw-0.3.0-dev-on-1.1.1.bin`.

**DFU transfer completed successfully; normal boot and physical audio are not yet verified.**
Real-time performance with multiple capture processors, SDRAM/cache behavior,
and the physical display still require hardware testing. Do not interpret the
emulator checks as evidence that every combination fits the audio deadline.
The 0.3.0-dev image was transferred in full (29,937 records); power-cycle the pedal to boot it.

## Controls

On the EQ page, select the model field with EDIT, then turn EDIT to move through
the two native EQ models, sixteen OD/FX models, and ten user captures.
MOD similarly contains its native models, sixteen OD/FX models, and ten captures.
The selector stops at each end, as the stock selector does.

OD/FX selections display their existing model artwork and parameter labels.
Captures display the name stored in the user library and GAIN / LEVEL controls.
LEVEL 50 is unity; changes are smoothed. Each added capture has independent left
and right processing state. AMP's capture state is not borrowed or overwritten.
Native selections retain stock processing. DEL retains the 0.2 editor-based
OD/FX extension; its on-pedal selector is unchanged.

Import `.nam` files through **User Captures (NAM)** in the custom editor. The ten
library entries are shared by AMP, EQ and MOD: replacing an entry changes all
presets referencing that entry. No additional library capacity is created.
Select a capture in the EQ or MOD list, adjust it, and save the preset normally.
Chain reordering remains available and moves the selected effect with its slot.

This supports **Stomp Manager's converted capture format**, not arbitrary native
NAM networks or general-purpose user DSP plugins. Conversion produces the pedal's
two-filter/nonlinearity representation. EQ/MOD run that capture core without the
AMP tone stack; GAIN controls the core and LEVEL controls its output. This does
not add downloadable chorus, delay, or other time-varying effect algorithms.
Empty entries and entries containing nonfinite coefficients pass dry audio.

## Compatibility and implementation

The preset layout is unchanged. Bytes 67/68/69 retain the original OD/FX marker
range `0x50..0x5f`. EQ and MOD additionally accept `0x60..0x69` for captures 1–10.
The native carrier models remain EQ 0, MOD 5, DEL 2. Native selection through the
new wheel clears the override, so returning to a carrier does not resurrect it.
Preset save, recall, export and chain changes preserve these bytes.

The custom SysEx `0x30` capability signature is now `FXA\x02`. Write choices
1–16 remain OD/FX; 17–26 select captures in EQ/MOD. Zero clears an override.
The editor gates capture choices on protocol version 2 and verifies write replies.
Re-selecting a capture restarts initialization, including after an editor upload.
Initialization copies/clears at most 512 state bytes per audio invocation and
passes dry audio until ready. Model switches can therefore be audible.

Official Stomp Manager still sees carrier models; use the custom editor for the
extended selections. Stock firmware does not understand the marker bytes.
Firmware downgrades require adjusting affected presets.

The existing bootloader, other application slot, assets and reserved app tail are
unchanged. The update package still contains the stock factory-preset region;
back up presets before flashing and keep the stock image for recovery.

## Build and checks

```powershell
.venv/Scripts/python patches/fx-controls/build_patch.py
.venv/Scripts/python cfw.py build -c cfw-fx-controls.toml
.venv/Scripts/python cfw.py selftest -c cfw-fx-controls.toml
.venv/Scripts/python -m unittest discover -s tests -p test_fx_controls.py -v
.venv/Scripts/python -m unittest discover -s tests -p test_fx_editor.py -v
.venv/Scripts/python -m unittest discover -s tests -p test_chain.py -v
.venv/Scripts/python tests/test_jme_capture.py
```

Tests execute the generated Thumb code: selector round trips, native dispatch,
OD/FX regressions, display-command generation, parameter bounds, independent
capture instances, capture-core parity with stock, bounded initialization,
invalid captures, protocol validation, preset recall and chain dispatch.
The DFU self-test verifies protected ranges and simulates the complete transfer.
Unicorn does not model Cortex-M7 timing or hardware caches.
