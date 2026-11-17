# 0.4.5-chain-diag

Another performance experiment, not a confirmed hardware fix.

The previous 0.4.4 optimization reduced capture instruction count but still
exceeded the hardware deadline. This variant schedules independent VMUL results
before VADD accumulation, replacing VMLA while retaining separate multiplication
and addition rounding and the tap accumulation order. It saves/restores the
additional callee-saved floating-point registers it uses.

The eight-output kernel additionally supports the stock CAB's 384-tap filter
with its 512-sample ring. The original stock FIR remains intact as fallback.
Four guarded call-site patches route the stock AMP capture stages (0x17c3a,
0x17c84) and CAB stages (0x14d22,0x14e5e) through this kernel. Thus the experiment
also targets the baseline chain cost rather than only the extra FX processors.

No filter coefficients, stereo channels, model selections or sample rates are
removed. No extra block buffering or algorithmic latency is introduced.

## Validation

tests/test_chain_fir.py passes:
- Native AMP and CAB parent processor parity for models 0, 14 and 29, 100 blocks
  each, with byte-identical stereo output against 0.4.4.
- 384-tap output parity across ring wraps and floating-point register preservation.
- Inherited 512-tap randomized parity, in-place output, 250-block actual FX01
  stereo parity with varying parameters, deadline-guard and display regressions.
- New full USB command-dispatch tests for all reply transports and rejection of
  writes/malformed queries.

Container selftest passes. Scheduled instructions are more numerous than the
0.4.4 kernel; no instruction-count speed claim is made. Actual pipeline timing
and the wider-chain savings must be measured on the pedal. The overload guard
remains enabled.

## Capture checkpoints

Read-only SysEx command 0x32 returns CGC1 plus ten uint32 values encoded as five
seven-bit bytes each. Each of EQ/MOD reports key, stage, elapsed cycles before
capture, elapsed cycles after a channel, and tripped checkpoint (0 before,
1 after left, 2 after right). Interpret trip_checkpoint only with stage 3 and
an active capture key. Data may be stale after clearing selection. These are
callback-relative elapsed times, not isolated per-core durations; an active
query may race an update. A latched stage 3 stops subsequent updates.
Host method: Pedal.capture_metrics(). Existing DGT1 format is unchanged.

Build: cfw-fx-chain-fir.toml. Builder flags:
--diagnostic --cache-state --split-bank --display-fix --solid-fill --capture-guard --fast-fir --chain-fir

Artifact: build/soran-cfw-0.4.5-chain-diag-on-1.1.1.bin
Flashed successfully (29,937 records); user confirmed normal boot. Artifact
SHA256: c7b05bf1ebb8fa9132a182180742433c103bdafb26f782136f3c8fa0e3e2942a.

## Hardware result

FX01 was erased by the firmware update. Restored its backed-up coefficients
first, metadata last, and verified both byte-for-byte before selection.
The controlled EQ FX01 test completed 50 telemetry samples without losing USB.
It did NOT sustain capture processing: the guard latched stage 3 (dry bypass).
The latched checkpoints were 43,898 cycles before the capture and 104,342 after
the left channel, trip checkpoint 1. The measured callback period was about
100,000 cycles, with guard threshold period minus 5,000. The left-channel
interval alone was 60,444 cycles, including checkpoint overhead. The right
channel was not processed in the tripping callback. Whole-callback peak was
127,692 cycles. No unfinished passes were reported in the final sample.

The original live edit was restored exactly, without saving test selections.
Evidence: work/fx01-chain-hardware.jsonl, including the restored_eq record.
Initial state: work/fx01-before-chain-test.json. MOD capture processing and
simultaneous EQ/MOD captures have not been verified on this build.

This remains an unsuccessful performance experiment, not a working capture
fix. The measurements identify processing time as the immediate guard trigger;
they do not establish that the hardware cannot support a different algorithm.
