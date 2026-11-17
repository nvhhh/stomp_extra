# 0.4.0-split-dev: separate AMP and FX capture banks

Built for the Soran Dual Stomp Lite stock V1.1.1 image. Development build;
not flashed or verified on hardware.

- USER AMP 01–10: existing physical capture slots 0–9, available to AMP.
- FX 01–10: physical capture slots 10–19, available only to EQ and MOD.
- EQ/MOD markers remain 0x60–0x69, but now resolve exclusively to the FX bank.
  Both slots share these ten FX captures. DEL remains limited to native/OD FX.
- AMP descriptors and processing are unchanged. Its bank cannot select FX data.
- Pedal EQ/MOD pages and the split-bank editor show fixed FX 01–10 labels.
  The editor shows USER AMP 01–10 for AMP. Stock AMP display behavior is retained,
  including uploaded capture names. Imports retain their metadata names.
- Capability version FXA 3 distinguishes split-bank firmware from older shared
  banks. The updated editor reads 20 captures only on this version. IR stays ten.
- Includes the existing extra-state cache fix and timing/fault diagnostics.

Existing EQ/MOD capture selections now refer to the same numbered FX slot, not
the old AMP capture. Nothing is automatically copied between banks. Empty FX
entries pass audio through. Built-in OD/FX selections retain their meanings.

## Build and validation

```
.venv/Scripts/python patches/fx-controls/build_patch.py --diagnostic --cache-state --split-bank
.venv/Scripts/python cfw.py selftest -c cfw-fx-split-captures.toml
.venv/Scripts/python tests/test_split_captures.py
.venv/Scripts/python tests/test_fx_editor.py
```

Seven split-bank tests cover all ten coefficient mappings, empty-bank isolation,
unchanged AMP descriptors/processor, wheel and native dispatch, labels,
capability reply, actual decoded USB read/write bounds, and inherited cache,
timing, full USB transport, fault-record and three-effect DSP regressions.
Host tests cover bank-aware upload refresh and bounds as well as model selection.
Container selftest checks declared patch ranges, CRC and simulated DFU transfer.
These checks do not reproduce physical flash behavior or audio timing.

## Hardware validation outstanding

The FX bank occupies 0x60ede000 through 0x60efbfff. Physical chip capacity and
ownership/contents of this region remain unverified; see CAPTURE-EXPANSION.md.
This build does not probe or automatically erase/initialize the region on boot.
It enables stock upload operations on the additional slots. Do not treat the
offline tests as evidence that this region is safe to write on the actual unit.

Before installing, back up both capture metadata and coefficients plus presets,
and inspect the proposed area with a read-only storage diagnostic. Firmware
updates use erase blocks larger than individual capture sectors; the stock
image's final erase block also overlaps the start of the proposed FX bank.
Plan capture restoration after updating, including future updates. Existing
preset ZIPs alone are not capture backups.

Then verify slot 11/20 upload and readback, reboot persistence, AMP and FX
isolation, names, wheel traversal and saved preset recall on the pedal.
