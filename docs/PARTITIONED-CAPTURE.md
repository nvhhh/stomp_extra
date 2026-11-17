# 0.4.6-part-diag: partitioned capture filters

Replaces only the extra EQ/MOD captures' two long FIR stages with a direct
64-tap head and fourteen 32-tap tail partitions. Retains the stock nonlinear
waveshaper, gain smoothing, level control, all 512 coefficients in each FIR,
independent stereo histories and the stock one-sample delay per FIR. This is
the vendor converted-capture format, not a general neural-network interpreter.

The tail uses a 64-point FFT and overlap-add. Its 64-sample offset supplies a
32-sample computation window after the input block is complete. Forward FFT,
two halves of the spectral product, and inverse FFT run in separate eight-sample
callbacks. Four filters start at different phases, distributing the work evenly.
No additional buffering delay is introduced. FFT arithmetic changes rounding;
output is numerically close, not bit-identical.

Each capture instance uses 27,408 bytes within its existing 32 KiB allocation.
The first 96 bytes contain separate left/right level and drive smoothers. FFT
coefficients are shared between channels; histories and overlap are separate.
Initialization clears bounded slices, validates all 2,048 source floats, then
computes one coefficient FFT per call. Non-finite transformed coefficients are
also rejected. Initialization keeps the dry fallback and deadline guard.

Kernel source: patches/fx-controls/capture_partitioned.c. The builder compiles
with local LLVM Clang for Cortex-M7, hard-float ABI, FPv4-compatible single
precision instructions, without contraction or fast-math. Two assembly loops
handle the direct head and complex products. The ELF must link with no unresolved
dependencies. Code is placed in hash-verified blank ITCM below 0x38000; the
existing patch and guard remain in their prior regions. Stock AMP/CAB keep the
0.4.5 scheduled FIR optimization.

## Validation before flashing

- All twelve firmware/container selftests passed, including protected DFU
  bootloader identity and simulated complete flashing.
- Six partitioned-capture test groups passed: impulse and random FIR reference
  comparison through every tail partition and ring wrap; actual FX01 stereo
  comparison; simultaneous EQ/MOD and capture switching; all ten FX banks and
  memory bounds; invalid coefficients; deadline latching and inherited native
  DSP, cache, display, wheel, AMP isolation and USB regressions.
- Actual FX01 stereo maximum absolute error was 3.8743e-7 and signal/error ratio
  131.8 dB for the recorded random-input and varying-drive test. This is an
  offline arithmetic check, not a listening assessment or hardware SNR rating.
- Steady wrapper instruction counts were 25,001–25,002 across eight callbacks.
  These are emulator instructions, not measured hardware cycles.

Artifact: build/soran-cfw-0.4.6-part-diag-on-1.1.1.bin

SHA256: fa82b0f33b0ef22c17046b300b249aef8d6bb67212e1516df8dbd6313199d4f3

Hardware result: transferred successfully, 29,937 records in 96 seconds.
User confirmed boot; FX01 was restored and verified. EQ activation still tripped
the guard at checkpoint 1: before 61,484 cycles, after left 102,541, whole callback
peak 125,876. USB stayed responsive and the original edit was restored exactly.
The initialization completion and first DSP pass occurred in one callback,
inflating its cost; this result does not give a steady-state capture duration.
Evidence: work/fx01-partition-hardware.jsonl. MOD was not tested on this build.

## Follow-up 0.4.7-mono-diag

Initialization now returns dry even on its final step; audio starts next callback.
Bit-identical left/right input and identical histories share one calculation.
If input differs, a fresh stereo instance uses its independent zero histories;
if it becomes stereo later, the accumulated history is copied to the right before
either side processes the new input. Thereafter processing stays stereo until
the capture is reinitialized. Channels are never averaged or discarded. The
history-copy transition has a one-time cost that requires hardware validation.

Filter phases are L=(0,2), R=(1,3), distributing both mono and stereo work.
State now uses 27,420 bytes per slot. Seven test groups pass, adding matching
nonzero stereo input, initialization deferral and mono/stereo transition checks.
Mono wrapper instructions span 12,577–12,929; stereo 25,015–25,016, still not
hardware cycle measurements. No audible correctness claim follows from these
counts alone. Actual FX01 arithmetic error remains below 3.9e-7 in the test.

Build configuration: cfw-fx-partition-mono.toml. Other commands as above.
Artifact: build/soran-cfw-0.4.7-mono-diag-on-1.1.1.bin
SHA256: 8364c20f834ac254e514a24cabd3a0fe99538073bbac7a62e03d9ce9f3e7cf8e
Hardware result: transferred successfully, 29,937 records in 96 seconds.
After normal boot and FX01 restoration, EQ completed 50 samples over five seconds
with stage 1 active, final elapsed 82,998/100,002 cycles. MOD independently
completed 49 samples with stage 1 active, final elapsed 81,134/100,002 cycles.
Both edits were restored exactly; no unfinished passes were reported. These
short tests do not establish long-duration stability or every capture model.
Global peaks reached 106,516 and 107,192 cycles, including earlier callbacks;
their exact originating passes were not captured by the host polling.

Combined EQ/MOD activation still tripped MOD at checkpoint 1: 63,817 before,
105,088 after left, global peak 124,851. EQ remained stage 1. USB stayed
responsive and the full edit was restored. This build fixes the tested single
capture activation but does not resolve the combined case.
The 0.4.6 kernel source/symbol snapshot is in work/partition-0.4.6-source.

## Follow-up 0.4.8-tcm-diag

Moves one FIR's immutable head and tail spectrum to the existing per-slot A
allocation in ITCM: EQ 0x3b100..0x3bfff, MOD 0x3c100..0x3cfff. Exactly 3,840
bytes are used per slot, leaving its first 256 bytes for the stock scratch
(used through offset 0x8b). No additional memory region or cache policy changes.
Both channels share these immutable coefficients. The other FIR's coefficients
remain in cached SDRAM. The B copies remain available for inspection but are not
used by the first FIR. Switching to a built-in effect may reuse A; switching back
reinitializes the capture coefficients before audio processing.

All seven test groups and all twelve container checks passed. Memory-boundary
checks now cover the entire TCM coefficient footprint and preserved scratch
margin. Arithmetic results match 0.4.7 within the same tolerance.

Build configuration: cfw-fx-partition-tcm.toml.
Artifact: build/soran-cfw-0.4.8-tcm-diag-on-1.1.1.bin
SHA256: 51093c7b71267705a25f59f91d7dcac392ee8413da77169bdaa8e43687d9b15e
Hardware result: transferred successfully; normal boot and FX01 restore verified.
The combined test still tripped MOD at checkpoint 1, before 57,898 and after
97,010 cycles, whole-callback peak 116,700. EQ stayed active. The edit was
restored exactly and USB remained responsive. Thus combined operation is still
unresolved despite the reduced cost in this test.
The 0.4.7 kernel source/symbol snapshot is in work/partition-0.4.7-source.

## Follow-up 0.4.9-start-diag

Each FIR tracks how many history spectra have actually been filled (0..14).
Products for nonexistent zero-filled history are skipped during startup. All
four Filter structures are aligned to 32-byte cache boundaries; total state
is 27,520 bytes. Coefficients and eventual full filter length are unchanged.

Adds a period-relative whole-callback guard: two successive measured overruns
latch active user captures to dry, with checkpoint 3. Bounded initialization
steps do not count toward this streak. The guard must check capture keys >=17;
keys 1..16 belong to built-in OD algorithms whose stage values are initialization
cursors. A regression test explicitly verifies these are not modified.
This complements the existing per-channel guard; it is not hard real-time proof.

All eight test groups and all twelve container checks pass. The instruction
profile now warms 300 callbacks so it includes all 14 history partitions.
Audio errors remain below 3.9e-7 in the actual FX01 stereo test.

Build configuration: cfw-fx-partition-start.toml.
Artifact: build/soran-cfw-0.4.9-start-diag-on-1.1.1.bin
SHA256: 667db6655ae6e49c47901ce19486902cf211bd145d07e5494eae6c1d1591def7
Hardware result: corrected transfer completed and normal boot was confirmed.
The combined test reached processing but the whole-callback guard latched both
captures at 101,614 cycles (checkpoint 3), peak 106,534. Both settings were
restored exactly; USB stayed responsive. The prior image with the incomplete
built-in-key guard was overwritten in DFU before boot.
Logs: work/flash-0.4.9.log and work/flash-0.4.9-final.log.
The 0.4.8 kernel source/symbol snapshot is in work/partition-0.4.8-source.

## 0.5.0-fft-diag

Uses a 32-point complex transform plus real-spectrum reconstruction for each
64-point real transform. Inverse scaling stays 64 and the delay/partition layout
is unchanged. Also experimentally schedules separate VMUL/VADD instructions in
the head and complex-product loops. All ten test groups passed, adding DC,
Nyquist, random-transform roundtrip and assembly callee-saved register tests.

SHA256: 9df153ae400792906b85f6eca1b5df06b8237ae94fda01f253b4b09d408a0f12
Transferred and booted successfully. FX01 restored and verified. The combined
test still tripped the whole-callback guard at 100,070 cycles, peak 103,878.
Original edit restored exactly. This was not a successful combined-capture fix.

## 0.5.1-mac-diag

Retains the real FFT, but restores VMLA/VMLS in the custom arithmetic loops.
Also uses the eight-output VMLA FIR for native AMP/CAB instead of the scheduled
VMUL/VADD variant. The VMLA specialization now supports both 384- and 512-tap
filters on the stock 512-sample ring. All other block sizes/rings fall back to
the unmodified stock FIR. This tests instruction scheduling across the entire
chain rather than assuming fewer data dependencies mean fewer hardware cycles.

Ten test groups and twelve container checks pass. Native AMP/CAB output remains
bit-identical in parent-processor tests, including 384-tap register/ring-wrap
checks and randomized 512-tap history/in-place checks. Capture output keeps the
same numerical tolerance. No coefficients, channels or time samples are dropped.

Build configuration: cfw-fx-compact-fir.toml.
Artifact: build/soran-cfw-0.5.1-mac-diag-on-1.1.1.bin
SHA256: aa40aedd5a8a7635e4009462e61e4b26dbdc1ae46572e139e62f3c857cc52f69
Hardware status: transferred successfully, 29,937 records in 96 seconds; normal
USB re-enumeration confirmed. FX01 was restored and read back byte-for-byte.
The five-second combined EQ/MOD test completed with both capture keys 17, stage
1 active, final callback 91,237/100,002 cycles, peak 98,225 and no unfinished
passes. The live edit was restored exactly.

A subsequent OD-enabled combined test recorded 239 samples over 24.35 seconds
with both captures active and no guard latch, then Windows WinMM reported an
error preparing a SysEx header. A fresh connection replied immediately. Effect
selections had changed outside the test, so that run cannot establish a full
90-second unchanged-configuration result. Its restore step did not run after
the transport error; the newly observed live edit was saved separately instead
of overwriting possible user edits. Later read-only polling also had a timeout,
but another fresh connection replied with EQ FX01 and MOD FX02 both active.
These transport interruptions are not evidence of a persistent pedal freeze.
Clean final duration/listening and reordered-chain checks remain pending.

Interruption snapshot: work/live-edit-after-midi-interruption.json.
Read-only log: work/fx-0.5.1-readonly-stability.jsonl.

User subsequently confirmed they had changed settings during the test, and
reported the pedal responsive with normal audio. They uploaded FX02 and reordered
the chain. A clean 60-second read-only run then found both captures already
latched dry (stage 3), with a whole-callback trip at only 93,347 cycles. This
exposed a false-positive guard: an ISR catch-up interval can be shorter than
the nominal audio deadline. The run had 13 replies with no transport errors and
unchanged edit, but is NOT counted as a successful active-capture duration test.

## 0.5.2-deadline

Both guards now use the fixed 100,000-cycle nominal audio interval verified for
the hash-guarded V1.1.1 firmware at its stock clock. Per-channel protection keeps
its 5,000-cycle reserve; whole-callback protection uses 100,000 cycles. Last ISR
entry intervals remain diagnostic telemetry only: shortened catch-up gaps must
not falsely bypass a capture, and stretched overload gaps must not enlarge its
budget. There is no change to the audio algorithm from 0.5.1.

Twelve test groups pass, including the reproduced 93,347-cycle false bypass
with a 66,000-cycle reported ISR interval, genuine overruns despite a stretched
150,000-cycle interval, and per-channel equivalents. Additional tests verify
all sixteen built-ins in both EQ/MOD after capture coefficients have occupied
their TCM allocation. All twelve firmware/container checks pass.

Build configuration: cfw-fx-fixed-deadline.toml.
Artifact: build/soran-cfw-0.5.2-deadline-on-1.1.1.bin
SHA256: ae6bc6a049653d8067104121ff2f51a13583d047c5864b2b1f2bef219d6497d9
Hardware result: transferred successfully (29,937 records, 96 seconds), booted,
and the latest FX01/FX02 data plus live edit restored and verified. Restoration
also recovered retained inactive parameter values through wider native models;
the final 98-byte edit matches the pre-flash backup exactly. No saved preset
was written.

The final unchanged-settings run completed 60.46 seconds with 13 fresh-connection
telemetry samples, no USB errors, EQ key 17/stage 1 and MOD key 18/stage 1
throughout, no unfinished passes and no guard trips. Sampled callback cost ranged
87,219–92,107 cycles; the global peak stayed 99,304 cycles, below the fixed
100,000-cycle deadline. The user's reordered chain was Gate → OD → AMP → EQ →
MOD → CAB → Delay → Reverb, with their own enabled/bypassed states and parameters.
The user confirmed responsive controls and normal audio during the preceding
0.5.1 tests; 0.5.2 changes only the guard deadline, not the audio algorithm.
This validates the tested setup, not every possible capture/effect combination.

Evidence: work/fx-0.5.2-final-stability.jsonl and work/session-restore-result.json.
Final readback archive: backups/library-1794872366445062300.zip.
All 99 saved presets, all 20 capture metadata/coefficient records, and the live
edit match backups/library-1794871812720799800.zip byte-for-byte. Verification:
work/final-library-verification.json. The 10 AMP-only / 10 EQ-MOD-only bank split
and chain-ordering features remain unchanged.

Latest complete backup, including newly uploaded FX02 and the user's unsaved
reordered live edit: backups/library-1794871812720799800.zip.
Restoration helper: tools/restore_capture_session.py (never saves presets).

For future builds use cfw-fx-fixed-deadline.toml. Earlier partition experiment
configurations share the generated patch directory and should not be rebuilt
as historical versions without restoring their matching source snapshots.

Full readback backup taken before the 0.5.0/0.5.1 updates:
backups/library-1794870599141737300.zip (all 20 capture metadata/coefficient
records, all 99 presets and the live edit). Only physical capture slot 10 was
marked used. FX01's coefficients and metadata also retain the original separate
backups. Firmware updates erase part of its storage, so restore/readback remains
part of each hardware trial.

Build commands:

```
.venv/Scripts/python patches/fx-controls/build_patch.py --diagnostic --cache-state --split-bank --display-fix --solid-fill --capture-guard --fast-fir --chain-fir --partition-fir
.venv/Scripts/python cfw.py selftest -c cfw-fx-partition-fir.toml
.venv/Scripts/python tests/test_capture_partitioned.py
```
