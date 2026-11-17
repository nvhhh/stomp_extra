# 0.6.0-longir-test: 1024-tap user cab IRs

Test build, not a release. User IR slots (cab models 30–39) play the IR's first 1024 samples
(21.3 ms) instead of 384 (8 ms). Built-in cabs are unchanged.

## Why

The IR upload is 2048 float32 values: the IR's first 2048 samples, reversed (data[2047−k] = ir[k]).
The firmware's IR loader (`0x14FAC`) copies all 2048 into the CAB object (`0x20004998` + 0x128).
Stock firmware then plays only the last 384 (`+0x1B28`), i.e. the IR's first 384 samples.

Measured on 11 cab IRs (10 Marshall Box, 1 Orange) against the full IR, 1/3-octave bands, level-matched:

| What the pedal plays | All bands | 31–160 Hz |
|---|---|---|
| 0.5.2, Accurate conversion (384-tap fit) | 1.43 dB rms | 1.06 dB rms |
| This build, Stomp Manager-layout upload (first 1024 samples) | **0.11 dB rms** | **0.20 dB rms** |

## Change

Generator flag `--long-ir` in `patches/fx-controls/build_patch.py` (output `patches/fx-long-ir/`).
It requires the `--chain-fir` and `--cache-state` flags.

The two CAB FIR call sites (`0x14D22`, `0x14E5E`) branch to `cab_long_fir`. It reads the active
CAB index (`obj+2`); the FIR only runs while that matches the loaded coefficients.

- **Index 240–249 (user IR):** plays coefficients `obj+0x1128` (the last 1024) through a
  1024-sample ring at SDRAM `0x81FB8000`. The ring is cleared whenever the active IR changes.
  It uses `cab_fir8_1024`, a 1024-tap / 1024-ring variant of the 0.5.2 eight-output VMLA kernel
  (`capture_fir.install(..., ring=1024)`). Tap order and VMLA rounding are unchanged.
- **Anything else (built-in cabs):** jumps to the unchanged 0.5.2 `capture_fir8`.
- **MPU:** region 10 SRD changes from 0xC0 to 0x80, so subregion 6 (`0x81FB8000–0x81FBBFFF`)
  becomes cacheable like the existing FX state. The rest of the top of SDRAM stays uncached, as stock.
- **State:** a halfword at ITCM `0x3E0C0` holds the last index (0xFFFF at boot).

Side effect: the stock cab runs 384 taps on a 512-sample ring, which adds 128 samples (2.7 ms) of
delay. User IRs on this build don't have that delay. Built-in cabs keep it.

The 0.5.2 patch (`patches/fx-partition-fir`) regenerates byte-identically with this generator.

## Verification (emulator, built image)

Run `tests/test_long_ir.py`; all 6 tests pass:

- **User IR exactness:** output equals the convolution with the IR's first 1024 samples
  (one-sample stock FIR delay), relative error < 1e-5. Tested on the real "Marshall Box - 57 E"
  IR and a random IR, over 3200 samples with ring wraps.
- **Built-in cab:** bit-identical to 0.5.2, both at the FIR call and through the whole CAB
  processor (`0x14BD0`) with the main-loop loader (`0x1500C`).
- **Whole processor, user IR slot 8:** the fade-out → load → fade-in sequence completes, the
  active index becomes 247, and the long path plays.
- **IR switch** (user → user, and user → built-in → user): playback starts from clean history.
- **FP callee-saved registers** are preserved.
- **Cost:** user IR 12,639 emulator instructions per 8-sample callback, against 4,781 for the
  384-tap path; built-in cab 4,792. These are emulator instructions, not hardware cycles.

Container selftest passed (12 checks). The 0.5.2 regression suite (`test_capture_partitioned.py`)
passes on 0.5.2.

## Risks / hardware test plan

- **CPU budget:** roughly +8k instructions per callback while a user IR is selected. The 0.5.2
  measurement with EQ + MOD captures active was 87–92k of 100k cycles (peak 99.3k). In that setup
  this build will likely trip the capture guard, which switches the captures to dry; it doesn't
  crash. Without EQ/MOD captures there should be ample room.
- **Flashing erases part of capture storage** (see PARTITIONED-CAPTURE.md). Before flashing, back up
  the presets, the 20 captures and the IR slots, and the live edit, then restore afterwards
  (`tools/restore_capture_session.py`).
- **IR conversion:** upload IRs with **Stomp Manager (original)** conversion on this build. It uploads
  the IR's real first 2048 samples. "Accurate" fits only 384 taps, so it gains nothing here.
- **Hardware steps:**
  1. Back up.
  2. Flash `build/soran-cfw-0.6.0-longir-test-on-1.1.1.bin`.
  3. Restore.
  4. Select a user IR cab without EQ/MOD captures and listen; check the guard telemetry.
  5. Repeat with EQ/MOD captures to measure the cycle cost.
- **Recovery:** DFU mode (Left + Right at power-on), then flash 0.5.2 or stock.

## Build

```
.venv/Scripts/python patches/fx-controls/build_patch.py --diagnostic --cache-state --split-bank --display-fix --solid-fill --capture-guard --fast-fir --chain-fir --partition-fir --long-ir
.venv/Scripts/python cfw.py build -c cfw-long-ir-test.toml
.venv/Scripts/python cfw.py selftest -c cfw-long-ir-test.toml
cd tests && ../.venv/Scripts/python test_long_ir.py
```
