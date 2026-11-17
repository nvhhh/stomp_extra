# Simultaneous built-in effects and user capture capacity

Investigated against the shipped 0.3.1-dev image on 2026-11-16. No firmware
was rebuilt or flashed during this investigation.

## Crash: unresolved on hardware

The user reports a crash with built-in effects in OD/FX, EQ and MOD. The
editor's last cached record shows BD2 in OD/FX and Red Comp overrides in EQ
and MOD. That record also reports a failed refresh; it is not a fresh device
read or proof of the exact state at the fault. Snapshot:
`work/crash-three-effects-cached-state.json`.

The added `tests/test_fx_concurrency.py` runs the actual shipped machine code
through the original OD, EQ and MOD parent processors, not just the inserted
algorithm wrappers. Across 220 eight-sample blocks, interleaved BD2 / Red Comp /
Red Comp outputs match three independent emulators byte-for-byte and remain
finite. Both extra instances finish incremental initialization. This covers
stable native carrier selection plus simultaneous extra-instance initialization;
it does not exercise all physical wheel/model-transition paths.

Existing controls tests cover each of the 16 algorithms in the added slots,
several interleaved combinations, and repeated instances of the same algorithm.
No two-instance admission limit was found in these processing paths. This is
not evidence that every combination meets the device's real-time deadline.

`tools/investigate_fx_concurrency.py` counts executed instructions after warmup.
For the three parent processors, native BD2 / EQ6 / Flanger executes
4992 / 2350 / 2410 instructions; BD2 / Red Comp / Red Comp executes
4992 / 2981 / 2928. These are **not cycles or a CPU utilization measurement**.
They exclude the rest of the chain, interrupts, memory latency and caches.
The additional states reside in SDRAM, unlike the original OD state in OCRAM,
so equal instruction counts would not imply equal cost on hardware.

The custom B-state ranges are 0x81fa0000..0x81fb7fff. The inspected stock
looper ring based at 0x81f19800 uses offsets 0x4100 and 0x44100 with 0x10000
float entries each, ending at 0x81f9d900, below those ranges. This rules out
overlap with those particular rings, not all possible dynamic memory users.

Unicorn uses an A15 Thumb/VFP execution model because its M7 model cannot run
the stock double-precision DSP instructions. It does not reproduce target MPU,
interrupt concurrency, caches, bus faults or real-time behavior. The earlier
wheel-alignment fix does not establish the cause of this separate crash.

Conclusion: the report remains a firmware stability problem of unknown cause.
Neither a confirmed implementation defect nor a hardware processing ceiling
has been established. A defensible diagnosis requires on-device fault status
(stacked PC, CFSR/HFSR and fault addresses) and audio-handler cycle/overrun
measurements with the failing preset. Do not label the emulator pass a fix or
flash an unchanged image as a remedy.

## User NAM capacity: ten shared entries

Current stock and custom firmware expose **10 user captures total**, shared by
AMP, EQ and MOD. Adding EQ/MOD selectors did not allocate additional storage.
Presets reference the same library. Replacing one entry changes the capture
available to every preset referring to that entry.

Evidence:

- IAR-initialized runtime count at `0x20010b88 + 0x1d` is 10.
- Stock upload handler at 0xafa8..0xafae and read handler at
  0xb086..0xb08c reject indices greater than or equal to that count.
- AMP descriptors for models 30..39 point to the ten user coefficient regions.
- EQ/MOD override values 0x60..0x69 select those same regions.
- The editor's `N_USER` is 10.

For zero-based entry i (0 through 9):

- Metadata: `0x60ec0000 + i * 0x3000`, one reserved 4096-byte sector.
- Converted coefficients: `0x60ec1000 + i * 0x3000`, 8192 bytes.
- Total reservation: 12 KiB per capture, 120 KiB for the ten entries;
  exclusive end address 0x60ede000.

These are vendor-converted captures, not arbitrary original `.nam` files stored
and executed unchanged. Conversion produces 2048 float coefficients and gain
metadata. Import compatibility depends on the vendor converter; the EQ/MOD
extension does not implement a general Neural Amp Modeler neural-network runtime.

Ten is the current firmware/library limit, not a proven maximum of the flash
chip. Expanding it would require auditing neighboring flash regions and updating
protocol bounds, descriptors, selectors, editor handling and persistence. The
number stored says nothing about how many can safely run simultaneously.

## Reproduce offline checks

```powershell
.venv/Scripts/python tests/test_fx_concurrency.py
.venv/Scripts/python tests/test_fx_controls.py
.venv/Scripts/python tools/investigate_fx_concurrency.py
```
