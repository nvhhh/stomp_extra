# 0.6.2-grace-test: start-up grace for the capture overload guards

Test build on top of 0.6.0. Audio, kernel, MPU and memory layout are 0.6.0; only the two capture
overload guards change.

## Why

With a NAM amp and a 1024-tap user IR, an EQ/MOD capture on 0.6.0 often latched dry right after it
was selected (7 of 9 activations, 2026-11-20). Each trip was the whole-callback guard (checkpoint 3)
seeing two consecutive callbacks just over the 100,000-cycle block (100.0k–105.5k). When a capture
got past its first ~0.1–0.3 s it ran steadily at 73–87k cycles. So the guard was reacting to a
start-up transient, not a sustained overload.

The 0.6.1-ampfft-test attempt to free CPU instead (AMP filters as FFT) was slower on the pedal; see
`docs/AMP-FFT.md`.

## Change

Generator flag `--guard-grace` in `patches/fx-controls/build_patch.py` (output
`patches/fx-guard-grace/`), constants in `patches/fx-controls/diagnostics.py`:

| | |
|---|---|
| `GRACE_CALLBACKS` | 3000 callbacks (~0.5 s) after a capture starts processing |
| `GRACE_HARD` | 115,000 cycles |
| `GRACE_STREAK` | 16 consecutive overruns |

- Each capture's metadata word +8 (unused before) holds its grace counter. The whole-callback guard
  (end of every audio callback) loads it while the capture initializes (stage 0) and counts it down
  while it processes (stage 1). Built-in OD models in EQ/MOD (keys 1–16) are not touched.
- While any processing capture is inside its window, an overrun below 115,000 cycles latches only
  after 16 in a row (instead of 2). An overrun at or above 115,000 counts as before (2 in a row).
  After the window, the 0.6.0 rules apply unchanged.
- The per-channel guard (95,000 cycles at a checkpoint inside the capture) also lets a capture in
  its window continue below 115,000.

## Risk

During the window, a callback can overrun the block by up to 15%, at most 15 times in a row.
That can click once when a capture is switched on. A capture that genuinely does not fit is still
latched dry, within ~3 ms (16 callbacks) or immediately at 115k, and always 0.5 s after start.

## Verification (emulator, built image)

`tests/test_guard_grace.py`, 8 tests, all pass: window loading and countdown; 15 overruns
tolerated, the 16th latches, one in-budget callback resets the streak; 115k overruns latch after
2; 0.6.0 rules after the window; a capture in its window covers a steady one in the same callback;
native OD keys untouched; per-channel guard. Plus 0.6.0's capture and long-IR suites (including the
0.6.0 guard tests and MPU test) against this image. 0.5.2 and 0.6.0 patches regenerate
byte-identically. Container selftest passed.

## Hardware result (2026-11-20)

Flashed `232e09aa…0e287` (29,937 records, 96 s), normal boot. Captures restored from
`backups/library-1795150702716770900.zip` without touching the live edit. Setup: NAM USER AMP 06,
user IR "Marshall Box - 9" (1024-tap path), MOD = capture FX01, chain Gate → OD → EQ → MOD → AMP
→ DEL → REV → CAB. Log: `work/grace-0.6.2-mod-activation.jsonl`.

- MOD capture switched on 8 times (override off 0.5 s, on, polled for 3 s): **8/8 stayed active**
  (stage 0 → 1 in ~50 ms, no trip). Peak during activations 100,682 cycles: the start-up overrun
  is real and small (<1%), and the grace window absorbed it.
- Then 30 s steady: 120 samples, median 81,052, max sampled 94,705 cycles, stage 1 throughout,
  0 unfinished passes. Peak since boot 102,336 (single overruns, never two in a row).
- Capture cost in the steady state: starts ~12.7k cycles into the block, ends ~31.2k (~18.5k).
- Not tested: EQ + MOD captures together (that combination hung the pedal on 0.6.0).

## Build

```
.venv/Scripts/python patches/fx-controls/build_patch.py --diagnostic --cache-state --split-bank --display-fix --solid-fill --capture-guard --fast-fir --chain-fir --partition-fir --long-ir --guard-grace
.venv/Scripts/python cfw.py build -c cfw-guard-grace-test.toml
.venv/Scripts/python cfw.py selftest -c cfw-guard-grace-test.toml
cd tests && ../.venv/Scripts/python test_guard_grace.py
```
