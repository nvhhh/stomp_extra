# FX01 activation crash investigation

The user reports normal operation until FX01 is selected, then the pedal and
USB become unresponsive. A subsequent Windows MIDI send/open failure is not
evidence of a host-only problem. After a normal reboot, fresh USB reads work.

Read-only acquisition found FX01 named APP-SD1-Drive-I, used flag 1, gain 1.0,
2048 finite nonzero coefficients, maximum absolute coefficient 14.91207695.
Metadata and coefficients are backed up in backups/fx01-crash-metadata.bin and
backups/fx01-crash-coefficients.bin. Coefficient SHA256:
99495ac0607128ac644a67d7ae5dc2b0f3374b0de78bb1bd4a7e91b996ff7b9b.
These facts do not prove a complete upload; no original converted file was
available for comparison.

The exact acquired data runs in the emulator with finite output and no memory
fault. The stereo capture wrapper executes 62865 instructions per eight-sample
block: 31329 in each channel's capture core and 207 in the wrapper. Instruction
counts are NOT target cycle measurements. Baseline hardware telemetry with
native EQ/MOD showed 79351 elapsed cycles against a 100002-cycle period, with
peak 88631 and zero unfinished passes. Processing overload is a hypothesis,
not a confirmed hardware cause. No FX activation was repeated on hardware.

## 0.4.3-guard-diag

An isolated diagnostic build adds a DWT deadline check before capture processing
and after each channel. If elapsed time in the current audio callback reaches
the previous measured audio period minus 5000 cycles, it latches stage 3 and
returns dry audio. Subsequent calls remain dry until the model/override is reset.
Existing DGT1 telemetry exposes EQ/MOD stage 3. Per-instance metadata +20/+24
stores elapsed time before/after processing; +28 records checkpoint 0/1/2.
Those extra words currently require a debugger to read; they are not in DGT1.

This is not an optimization or proof that the selected chain fits. One channel
can exceed the deadline before its following check; the latch prevents repeated
capture work afterward. It cannot recover a memory fault inside a core or a
separate fault in flash/display code. If the guard trips, the capture is bypassed,
not successfully running within budget.

Synthetic timing tests cover each checkpoint, uint32 cycle-counter wrap, dry
output and persistent latch behavior. Rendering, storage bounds/bank separation,
cache, DSP and USB regression tests pass. Container selftest passes.

Build config: cfw-fx-capture-guard.toml; builder flags:
--diagnostic --cache-state --split-bank --display-fix --solid-fill --capture-guard.
Tests: tests/test_capture_guard.py.

## Hardware result after 0.4.3 installation

Transfer completed (29937 records, 96 seconds), followed by normal boot and
working telemetry. FX01 was erased by the firmware update (used flag 255).
Restored coefficients first, metadata last, without selecting the capture;
both read back byte-identical to the backup. No saved preset was changed.

One controlled activation of FX01 in EQ produced stage 3 (deadline guard
latched). Peak callback time increased from 88665 to **145812 cycles**, against
a roughly **100000-cycle** audio period. Thirty telemetry samples over about
three seconds succeeded; stage 3 persisted, confirming the capture had been
bypassed. Restored the original live-edit record byte-identically by clearing
the EQ override. Normal callback time returned to around 78000–80000 cycles.

This confirms a processing-budget violation with this capture in this preset.
It supports overload as the cause of the previous unguarded lockup; no fault
registers were acquired from that lockup. The exact checkpoint that tripped is
not exposed through DGT1, so do not infer whether one or both channels ran.
The peak includes the rest of the audio callback, not just capture processing.

The guard is containment, not a usable capture performance fix. Successful USB
polling after activation does not mean the capture kept processing: it was dry.
Further work needs DSP optimization and/or lower chain cost. MOD activation and
multiple simultaneous user captures have not yet been validated on hardware.

Evidence: work/fx01-before-guard-test.json, work/fx01-guard-hardware.jsonl.
Installed SHA256:
2993b25ae91a6e641bd4bd506a9d5a14305ab11569fc6455ca91abfee1eeceb3.
