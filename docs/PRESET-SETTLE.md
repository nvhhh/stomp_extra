# 0.6.3: preset-switch freeze fix (preset settle + debt guard)

0.6.2 plus three additions. Audio processing, kernels, MPU and memory layout are unchanged.

## Symptom

On 0.6.2, switching to a preset with an EQ/MOD capture (profiles 2, 4, 5) stopped USB for
0.33–0.85 s every time, and sometimes the pedal froze with "crunched" audio until power-cycled
(reproduced 2 times in ~20 switches). Presets without a capture, and live changes (amp, capture
on/off, cab, chain, native model under the capture) never stalled.

## Diagnosis (0.6.3-diag stall profiler)

`0.6.3-diag` added a main-loop heartbeat (loop spin at `0x7778`) and, in the audio callback,
sampling of the interrupted main-loop PC/LR while the heartbeat stops. During a 1,989-callback
(0.33 s) stall after loading profile 5:

- the main loop was in the full-screen LCD push (`0xD4C2`, reads the framebuffer at SDRAM
  `0x80000000`, writes each pixel over SEMC to `0x9C000000`) and a ring-buffer copy (`0x16980`);
- every sample showed audio callbacks starting 103,000–110,000 cycles apart instead of 100,000:
  the audio interrupt was using all of the CPU.

The preset redraw floods the SEMC bus and the cache. EQ/MOD capture and long-IR state live in
cacheable SDRAM, so the callback grows from ~80k to just over 100k cycles. The main loop starves,
the redraw (normally 43–64 ms) takes 0.33 s, and occasionally never finishes: a freeze. The 0.6.2
grace window tolerated these overruns for 0.5 s, and overruns that alternate over and under budget
never tripped the 0.6.0 "2 consecutive" rule either.

Measured redraw timeline after a program change (no capture): redraw 1 starts 25–35 ms after the
recall and lasts 43–64 ms; redraw 2 starts ~0.52 s after and lasts ~46 ms.

## Change

Generator flags `--stall-profiler --preset-settle` (output `patches/fx-settle/`), constants in
`patches/fx-controls/diagnostics.py`:

1. **Preset settle.** The preset recall `0x4F1E` (every load path: program change, footswitches,
   editor) starts a hold. While it is set, EQ/MOD captures output dry without initializing or
   processing. It ends when a main-loop stall of at least 20 ms (the redraw) was seen and the main
   loop then ran for 10 ms (stalls under 2 ms count as running), or after 0.5 s. Captures then
   continue; nothing is latched.
2. **Debt guard.** At the end of each callback, `debt = max(0, debt + elapsed − 100,000)`. Above
   400,000 cycles (4 blocks behind real time) processing captures latch dry (checkpoint 3, as in
   0.6.0), whatever the overrun pattern.
3. **Stall profiler** kept (read-only command `0x33`, `Pedal.profiler()`), header 32 words:
   settle and debt counters included.

`0.6.3-diag` (`patches/fx-stall-diag/`, 16-word header) was the diagnostic build that found the
cause. It was generated before the header grew, so the current generator no longer reproduces it.

## Verification

Emulator, built image (`tests/test_stall_profiler.py`, 17 tests, all pass): heartbeat hook; stall
sampling through the real audio-callback prologue (`0x12278`, exception frame at sp+72; PSP frame on
a Cortex-M7 model); longest-stall record; bounded buffers; read command; recall hook copies presets
like stock; hold until redraw then quiet; brief tasks; hold limit; capture dry and not initialized
while held; debt latch with alternating overruns, no debt in budget, recovery below the limit; plus
0.6.2's grace tests and the 0.6.0 capture / long-IR / MPU / split-bank suites. 0.5.2, 0.6.0 and
0.6.2 patches regenerate byte-identically. Container selftest passed.

## Hardware result (2026-11-21, IR slots empty)

Flashed `soran-cfw-0.6.3-on-1.1.1.bin` (sha256 `82cd1bca…aab2`, 29,937 records, 97 s). Captures
restored from `backups/library-1795239747156411100.zip`. `tools/hw_freeze_suite.py`, 251 steps
(`work/hw-suite-0.6.3-noir.jsonl`):

| Test | Steps | Result |
|---|---|---|
| Preset pairs 5↔4, 5↔8, 4↔2, 2↔5, 4↔8, 1↔5, 5 rounds each | 60 | no stall; capture running after every switch |
| Rapid switching, 0.15 s per preset | 49 | no stall |
| All 99 presets | 99 | no stall, nothing latched |
| Live: capture on/off, FX01/02/03, NAM ↔ stock amp, MOD bypass | 26 | no stall |
| EQ + MOD captures + NAM amp | 11 | no freeze; guards latched both dry (peak 116k) |
| 30 s steady, profile 5 | 1 | fine |

Longest USB gap 0.08 s (0.6.2: 0.33 s per capture-preset load). Longest main-loop stall 381
callbacks (63 ms, a normal redraw). 212 of 214 settles ended on redraw + quiet, 2 at the 0.5 s limit.
Debt maximum 7,570 cycles in normal use, 38,997 in the dual test; the debt guard never fired.

Not yet tested: the same suite with the 1024-tap user IRs loaded.

## Build

```
.venv/Scripts/python patches/fx-controls/build_patch.py --diagnostic --cache-state --split-bank --display-fix --solid-fill --capture-guard --fast-fir --chain-fir --partition-fir --long-ir --guard-grace --stall-profiler --preset-settle
.venv/Scripts/python cfw.py build -c cfw-settle.toml
.venv/Scripts/python cfw.py selftest -c cfw-settle.toml
cd tests && ../.venv/Scripts/python test_stall_profiler.py
.venv/Scripts/python tools/hw_freeze_suite.py      # on hardware, 0.6.3 flashed
```
