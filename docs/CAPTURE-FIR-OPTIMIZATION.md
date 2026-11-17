# 0.4.4-fast-diag: eight-output FIR

The custom capture core invokes two 512-tap FIR stages for each stereo channel.
The stock FIR at 0x13f84 processes four outputs per coefficient traversal.
The new capture-only specialization processes eight outputs per traversal,
loading each coefficient once, rotating the eight sample registers without
register-copy instructions, and advancing a wrapping history pointer.

All 512 coefficients, their accumulation order, non-fused VMLA rounding and
independent stereo histories are preserved. No mono conversion, coefficient
truncation, resampling, preset changes or disabling of other effects is used.
The first eight old ring samples are retained before inserting new input, so
the output and final history match the stock four-output implementation even
across wrap boundaries. Non-512-tap/non-eight-sample calls fall back to stock.
The original global stock FIR is unchanged; only custom capture calls use this
specialization. Existing deadline protection remains active.

## Offline evidence

tests/test_capture_fast.py compares output and history byte-for-byte against
stock FIR with randomized input/history/coefficients, eight different ring
positions (including unaligned and wrapping positions), and in-place output.
The complete FX01 stereo capture is compared for 250 blocks with independent
random left/right inputs and changing gain/level. All outputs match exactly.
Inherited deadline, display, capture-bank, cache, DSP and USB tests also pass.
Container selftest passes.

Measured emulated instructions per stereo wrapper call: 62900 before, 26432
after (approximately 58% fewer). These are NOT hardware cycles or proof of
meeting the audio deadline. Hardware timing, guard status and audio confirmation
remain necessary. No fix for all chains or simultaneous captures is claimed.

Build config: cfw-fx-capture-fast.toml
Builder: patches/fx-controls/build_patch.py with flags
--diagnostic --cache-state --split-bank --display-fix --solid-fill --capture-guard --fast-fir
Artifact: build/soran-cfw-0.4.4-fast-diag-on-1.1.1.bin
SHA256: 7550c55ff6caa6be35f1657dc4ecc0ea3a13b5bfe45a0d84ca8d026a5a15ad86

## Hardware result

Installed successfully, normal boot and diagnostics verified. Restored FX01
coefficients and metadata from backup; readback was byte-identical. Controlled
EQ activation still latched stage 3. Peak callback time reached 132546 cycles
against approximately 100000 cycles available. Fifty polls over about five
seconds succeeded, but the capture was bypassed, not actively processing.
The original live-edit record was restored byte-identically. No preset saved.

The earlier 0.4.3 guarded trial reached 145812 cycles. This comparison is of
recorded callback peaks, not a precise capture-only cost measurement. Guard
checkpoint is not exposed, so do not infer which channel triggered either peak.

Additional hardware chain-cost probes tested AMP models 0/1/2/14/28/29 and all
six reverb models. AMP median callback times remained around 79700 cycles.
Reverb alternatives ranged from 77591 (Damp) to 84723 (Shimmer), versus 78880
for the original Plate. These alternatives do not release the required margin.
All temporary changes were restored byte-identically.

Evidence: work/fx01-before-fast-test.json, work/fx01-fast-hardware.jsonl,
work/fx01-fast-chain-cost.jsonl. The optimization is functionally validated but
does not make this stereo capture fit this chain on hardware. Further filtering
optimization or an explicitly chosen processing/latency tradeoff is required.
