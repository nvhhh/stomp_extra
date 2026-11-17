# 0.3.3-diag: simultaneous-effects investigation

This build adds instrumentation to 0.3.1. It is not a crash fix, and does not
expand the capture library.

Built image: `build/soran-cfw-0.3.3-diag-on-1.1.1.bin`

SHA256: `a8d95e48d17abea73cdebc3b61d32eddd58dcc6aa628944f7e04649a53408cdc`

0.3.2 booted and answered normal editor commands, but its diagnostic reply
omitted the fifth argument to the stock packet sender (transport ID). The
signature word was interpreted as that argument, so no USB reply arrived.
0.3.3 preserves the incoming transport and puts it on the call stack. A complete
command-dispatch-to-send regression reproduces the old failure and verifies
the corrected path. This was an instrumentation bug, not an explanation of the
original three-effect crash.

Pre-install backup: `backups/presets-before-diagnostics-20261116-220018.zip`.
The archive contains all 99 presets, the live edit record and editor state;
101 entries passed ZIP CRC verification. User capture/IR coefficient blobs are
not included in this preset backup.

## Measurements

The original timer call sites in the audio processing pass (0x1228c and
0x125ea) also sample DWT CYCCNT. The hooks leave the original timer routines
and floating-point return value intact. They track pass count, start-to-start
interval, elapsed cycles, peak elapsed cycles, busy status and unfinished passes.
Timing excludes ISR work outside the two hook sites; added instrumentation has
overhead. Do not interpret the ratio as an exact whole-system CPU percentage.

Read-only SysEx command 0x31 returns `DGT1` followed by sixteen uint32 fields,
each encoded as five low-to-high seven-bit bytes. `Pedal.diagnostics()` decodes
this. The editor exposes GET `/api/diagnostics` without changing the preset.
Records with different beginning/end pass counts are marked inconsistent.
Discard inconsistent/busy samples for interval-versus-elapsed comparisons.
Verify that DWT is enabled and counts advance before interpreting timing.

Extra EQ/MOD/DEL initialization keys and stages accompany the timing counters.
The stock raw timer count is also included. Peak counts accumulate since boot;
they may include startup or model-change costs.

HardFault, MemManage, BusFault and UsageFault vectors save a small RAM record
at ITCM 0x3e180, then halt as the original handlers did. The record contains:
magic FTL1, EXC_RETURN, IPSR, MSP, PSP, CFSR, HFSR, MMFAR and BFAR. It never
dereferences a potentially invalid fault stack. A debugger can use the saved
stack pointer and EXC_RETURN to find the exception frame and stacked PC.
**There is no USB recovery or persistent fault log.** If USB freezes, obtaining
this RAM record requires a connected debugger before power cycling. Address
register validity must be checked against CFSR. Power cycling loses the record.

## Hardware procedure

After normal boot, reconnect the updated local editor and verify a diagnostic
reply before testing. Start `tools/log_fx_diagnostics.py`; it flushes each reply
or timeout to JSONL. Capture a baseline, then one, two and three built-in effects
using the same preset and parameters. Include both live enable/model changes
and playing. Keep selection changes separate from telemetry reads. Restore the
pre-test live record afterward if necessary; do not save test edits over presets.

Low measured load before a freeze does not by itself prove a memory fault;
short spikes between host polls may be missed. High load indicates a timing
problem worth isolating, not automatically the sole crash cause. The existing
functional emulator does not model MCU bus timing, caches, MPU or interrupt
concurrency.

## Validation

- Firmware selftest: 12 checks pass, including protected DFU region and simulated
  full-image transfer.
- Diagnostic tests: five pass (counter wraparound/peak and original timer return,
  read-only packet encoding, full command dispatch/transport regression,
  Cortex-M7 fault breadcrumbs, three-effect regression).
- Editor regression tests: five pass.
- Before instrumentation, the full cached eight-block chain executed 150 blocks
  in functional emulation without a fault (`work/probe_full_chain.py`).

Rebuild with `patches/fx-controls/build_patch.py --diagnostic`, followed by
`cfw.py selftest -c cfw-fx-diagnostics.toml`. Selftest regenerates the timestamped
image, so recompute its hash afterward. The normal fx-controls generated files
and 0.3.1 image remain separate from the diagnostic output.
