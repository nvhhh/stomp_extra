# 0.6.0-longir-test: 1024-tap user cab IRs (FFT)

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
It requires the `--chain-fir`, `--cache-state` and `--partition-fir` flags.

User IRs run through a partitioned FFT convolution (`patches/fx-controls/cab_partitioned.c`). It reuses
the FFT, packing and assembly helpers of the 0.5.2 partitioned capture kernel:

- **Head:** taps 0–63, direct 8-output VMLA (`partition_head8`), so there's no added latency.
- **Tail:** taps 64–1023 as thirty 32-tap partitions, 64-point real FFT, overlap-add. The tail
  work is spread over four audio callbacks (FFT / first 15 partitions / last 15 / inverse FFT),
  so each callback costs about the same.
- **Output:** one-sample delay like the stock FIR. It equals the direct 1024-tap FIR up to
  floating-point rounding (relative error < 1e-5). FFT doesn't change the sound.

Hooks:

- **Loader:** the main-loop call to the IR loader (`0x15020`, `bl 0x14FAC`) goes to `cab_load_hook`.
  It runs the stock loader, then `cab_load(index)`. For a user IR (240–249) that function checks the 1024 taps
  are finite, computes the 30 partition spectra, clears the filter history and marks the index ready.
  This all runs in the main loop; the audio callback never pays for setup.
- **FIR call sites** (`0x14D22`, `0x14E5E`) branch to `cab_long_fir`. It calls `cab_process(in, out,
  active)` with the active CAB index (`obj+2`). That function only plays when the index is a user IR
  and matches the spectra that `cab_load` prepared. Anything else (built-in cabs, a failed load)
  jumps to the unchanged 0.5.2 `capture_fir8`.
- **State:** `Cab` struct (spectra + filter history, 16,992 bytes) at SDRAM `0x81FB8000`.
- **MPU:** region 10 SRD changes from 0xC0 to 0x00, so the whole 128 KB window `0x81FA0000–0x81FBFFFF`
  (FX state + cab state) is cacheable. Static .bss (ends `0x81F9D900`) and the rest of the top of SDRAM stay
  uncached, as stock. No stock code references `0x81FB8000` or above.

Side effect: the stock cab runs 384 taps on a 512-sample ring, which adds 128 samples (2.7 ms) of
delay. User IRs on this build don't have that delay. Built-in cabs keep it.

The 0.5.2 patch (`patches/fx-partition-fir`) regenerates byte-identically with this generator.

An earlier version of this build ran the 1024 taps directly (`test-longer-fir` branch). It cost
12,639 emulator instructions per callback. This FFT version costs 5,492 on average.

## Verification (emulator, built image)

Run `tests/test_long_ir.py`; all 7 tests pass:

- **User IR exactness:** output equals the convolution with the IR's first 1024 samples
  (one-sample stock FIR delay), relative error < 1e-5. Tested on the real "Marshall Box - 57 E"
  IR and a random IR, over 3200 samples.
- **Built-in cab:** bit-identical to 0.5.2, both at the FIR call and through the whole CAB
  processor (`0x14BD0`) with the main-loop loader (`0x1500C`).
- **Whole processor, user IR slot 8:** the fade-out → load → fade-in sequence completes, the
  active index becomes 247, and the long path plays.
- **IR switch** (user → user, and user → built-in → user): playback starts from clean history.
- **FP callee-saved registers** are preserved.
- **MPU region** covers exactly `0x81FA0000–0x81FBFFFF`, write-back, execute-never.
- **Cost** (emulator instructions per 8-sample callback, not hardware cycles):

  | Path | Mean | Max |
  |---|---|---|
  | 0.5.2, any cab (384 taps) | 4,782 | 4,782 |
  | This build, user IR (1024 taps, FFT) | 5,492 | 5,961 |
  | This build, built-in cab | 4,795 | 4,795 |
  | Earlier direct 1024-tap version | 12,639 | 12,639 |

The 0.5.2 capture regression suite (`test_capture_partitioned.py`) also passes against this image
(same 131.7 dB SNR and instruction counts). The only exception is one test that asserts the 0.5.2 MPU
value; that difference is intended. Container selftest passed.

## Risks / hardware test plan

- **CPU budget:** about +700 instructions per callback on average, +1,200 at peak, while a user IR
  is selected. The 0.5.2 measurement with EQ + MOD captures active was 87–92k of 100k cycles (peak 99.3k).
  This should fit. Cache behaviour isn't emulated: the cab state adds 17 KB to the cacheable working set,
  so check the guard telemetry on hardware. If it's over, the capture guard switches the captures to dry;
  it doesn't crash.
- **Flashing erases part of capture storage** (see PARTITIONED-CAPTURE.md). Before flashing, back up
  the presets, the 20 captures and the IR slots, and the live edit, then restore afterwards
  (`tools/restore_capture_session.py`).
- **IR conversion:** upload IRs with **Stomp Manager (original)** conversion on this build. It uploads
  the IR's real first 2048 samples. "Accurate" fits only 384 taps, so it gains nothing here.
- **Hardware steps:**
  1. Back up.
  2. Flash `build/soran-cfw-0.6.0-longir-test-on-1.1.1.bin`.
  3. Restore.
  4. Select a user IR cab with your usual AMP + EQ + MOD captures; listen and check the guard telemetry.
  5. Switch between user IRs and built-in cabs while playing (no clicks beyond the stock fade).
- **Recovery:** DFU mode (Left + Right at power-on), then flash 0.5.2 or stock.

## Build

```
.venv/Scripts/python patches/fx-controls/build_patch.py --diagnostic --cache-state --split-bank --display-fix --solid-fill --capture-guard --fast-fir --chain-fir --partition-fir --long-ir
.venv/Scripts/python cfw.py build -c cfw-long-ir-test.toml
.venv/Scripts/python cfw.py selftest -c cfw-long-ir-test.toml
cd tests && ../.venv/Scripts/python test_long_ir.py
```
