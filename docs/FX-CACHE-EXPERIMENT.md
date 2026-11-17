# Extra DSP state cache experiment, 0.3.4-cache-diag

## Hardware result

Installed successfully (29,937 records, 97 seconds), booted, and diagnostic
telemetry verified. The previously reproduced freeze did not recur after the
cache change. The user confirmed: "Responsive, audio sounds normal".

With identical 98-byte preset records for BD2 + EQ Red Comp, median steady-state
audio-pass cost fell from 91,559 cycles (36 samples) to 81,611 cycles (32 samples),
against a nominal approximately 100,000-cycle interval. The BD2-only control
stayed effectively unchanged: 79,793 versus 79,845 cycles. This isolates a large
penalty associated with the extra effect's uncached working memory.

BD2 + Red Comp in EQ + Red Comp in MOD completed a 20-second test with 77 valid
telemetry samples and a median of 83,155 cycles. The exact earlier freeze setup
(BD2, EQ Red Comp, MOD Boost, Digital Delay, amp bypassed) then completed a
60-second replay with 234 valid samples, median 79,882 cycles, maximum 81,905
cycles, and no unfinished-pass reports. Its final record differed from the old
pre-enable record only in the expected MOD enable bit and Boost selection marker.
The old run lost USB response during initialization and never yielded a stable
three-effect sample, so no numerical steady-state before/after comparison for
that configuration is claimed.

These results identify a firmware performance bug and resolve the tested freeze.
They strongly support processing-budget exhaustion caused by uncached SDRAM
overhead; a hard-fault register dump was not obtained, so the exact final failure
mechanism of the old build remains unobserved. This is not a certification of all
effect/NAM combinations, looper operation or long-duration use.

All 99 saved presets were exported again and matched the pre-test backup byte
for byte. Original saved preset 11 (zero-based 10) was restored after the tests.
No test edits were saved. The installed build remains 0.3.4-cache-diag, with
diagnostics retained. No capture-library expansion was made.

Results: `work/fx-hardware-cached.jsonl`, `work/fx-cache-results.html`, and
`build/fx-cache-diagnostics-validation.json`.

## Hardware observations before this change

0.3.3 diagnostic USB telemetry was verified on the connected pedal. Raw logs:
`work/fx-hardware-stages.jsonl` and `work/fx-hardware-low-load.jsonl`.
The user confirmed playing during the tests after the initial baseline.

In preset 11 (zero-based 10, JP Leadasd), the nominal interval between audio
passes was approximately 100,000 DWT cycles. The initial stock-effect baseline
used approximately 78,800 cycles. BD2 in OD/FX used approximately 79,700 cycles.
Adding Red Comp in EQ raised steady processing to approximately 91,000 cycles.
These measure the instrumented processing section, not all interrupt/system work.

Bypassing reverb or amp did not materially free processing time in these tests.
Digital Delay in place of Tape Delay freed only a small amount. With amp bypassed
and Digital Delay selected, adding Boost in MOD produced a telemetry sample at
94,805 cycles while MOD was still in initialization stage 2, then USB telemetry
stopped responding. Subsequent queries also timed out. The last sample does not
prove the cost or fault mechanism of the subsequent unobserved pass.

A normal power cycle recovered the device. No test edits were saved over presets.
Later tests selected other presets and remain recorded in the second log.
No physical hard-fault register dump was obtained. Therefore CPU starvation
versus a fault is not yet conclusively distinguished.

## Concrete performance issue under test

Stock MPU region 9 covers 0x81e00000..0x81ffffff as normal non-cacheable memory
(RASR 0x03080029). All three custom B-state buffers are inside that region:
0x81fa0000..0x81fb7fff. The original OD B-state resides in cacheable OCRAM.
This placement can impose a substantial SDRAM-access penalty on extra instances.

The experiment adds MPU region 10 over just the 96 KiB custom-state allocation.
RBAR = 0x81fa001a; RASR = 0x1303c021. The 128 KiB aligned region has its last two
16 KiB subregions disabled. Attributes match the stock cached OCRAM policy
(normal, non-shareable, cacheable write-back, no write allocate); execution is
disabled for this data region. The inspected looper rings end at 0x81f9d900,
below the region. There is no change to region 9's other memory or its DMA buffers.

The hook runs at stock MPU setup address 0xc3d6 while the stock startup has MPU
and caches disabled, before its existing barriers, cache invalidation and enable
sequence. It preserves the registers it uses. It checks MPU_TYPE and leaves
configuration unchanged if fewer than eleven regions are supported. The existing
allocation is retained; this does not prove that all dynamic stock memory users
have been identified.

Arm documents higher-numbered region precedence and MPU cache attributes in
the [Cortex-M7 generic user guide](https://documentation-service.arm.com/static/61efd6602dd99944d051417b)
and [RASR reference](https://support.arm.com/documentation/dui0646/c/Cortex-M7-Peripherals/Optional-Memory-Protection-Unit/MPU-Region-Attribute-and-Size-Register).

## Build and validation

Image: `build/soran-cfw-0.3.4-cache-diag-on-1.1.1.bin`

SHA256: `9e57716eb656f03666715423f0d085e40be443d13377513c3b2cf93d0f19249c`

```
.venv/Scripts/python patches/fx-controls/build_patch.py --diagnostic --cache-state
.venv/Scripts/python cfw.py selftest -c cfw-fx-cache-diagnostics.toml
.venv/Scripts/python tests/test_fx_cache.py
```

All 12 firmware selftest checks passed. Both cache tests passed, including
the exact address/subregion footprint, unsupported-region-count fallback,
register preservation, and all five diagnostic/DSP regression methods.
Emulation validates instructions and configuration, not cache timing/coherency.
The hardware comparison above supplies evidence for the tested configurations;
emulation alone does not establish cache performance or audio stability.

The configuration and generated patch are separate from 0.3.3, allowing the two
images to be compared without rebuilding the baseline diagnostic image.
