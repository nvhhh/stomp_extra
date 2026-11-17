# Capture expansion feasibility

Static investigation, 2026-11-16. The installed cache diagnostic firmware still
has ten shared capture slots. No capture expansion has been flashed.

## Result

Both 15 and 20 slots fit the existing addressing and preset encodings. Twenty
is the preferred implementation target, subject to checking the physical flash
and the proposed extension region. This is feasibility evidence, not a verified
free-space allocation.

Each vendor-converted capture reserves 12 KiB: a 4 KiB metadata sector and
8 KiB of coefficients. Metadata starts at `0x60ec0000 + slot * 0x3000`;
coefficients start at `0x60ec1000 + slot * 0x3000` (zero-based slot).

| Captures | Total reserved | Extra space | End, exclusive |
|---|---:|---:|---|
| 10 | 120 KiB | 0 | 0x60ede000 |
| 15 | 180 KiB | 60 KiB | 0x60eed000 |
| 20 | 240 KiB | 120 KiB | 0x60efc000 |

If the flash is 16 MiB, the 20-slot bank ends 1040 KiB before its end.
The stock image ends at `0x60edde00`; it cannot reveal the contents beyond
that address. No stock master-code literal reference above the current capture
bank was found in the disassembly audit. This does not exclude computed
addresses, bootloader use, or data left by another firmware version.

The stock flash driver matches JEDEC bytes at `0x2001677c..0x2001677e`
against its chip descriptors and stores capacity at `0x20016780`.
Its fallback capacity is 16 MiB; that fallback is not a hardware measurement.
Current timing telemetry does not expose these values or the flash tail.

## Changes required together

- Raise the runtime NAM count at `0x20010ba5`, used by the upload/read bounds.
- Extend and relocate the stock AMP descriptor table at `0x258ec` from its
  40 entries, auditing all references, clamps, display/name lookup and model
  selection paths. Twenty captures would use AMP models 30 through 49, below
  the preset's bypass bit `0x40`. A count-only patch would access beyond the
  existing table.
- Expand EQ/MOD selection, wheel, processing and display bounds from ten
  captures to twenty. The markers become `0x60..0x73`, still SysEx-safe.
- Update the custom editor's list generation, validation and catalogue.
  Split NAM and IR counts: `N_USER` currently controls both; IR must stay ten.
  Host virtual capture IDs would be 48 through 67 and require a full audit
  anywhere host IDs are translated to the native preset representation.
- Audit erase/reset/upload paths and initialize only new capture entries.
  The stock slot reset at `0xb252` uses a slot argument and a three-sector
  stride; its decimal naming arithmetic supports two-digit slot numbers.
  Do not confuse division by ten in that routine with a slot-count bound.
- Preserve existing capture coefficients and metadata, and all saved presets.
  Existing preset ZIP backups do not include the complete capture bank.

## Validation before release

1. Prepare a separate read-only storage diagnostic build to report detected
   JEDEC ID, matched chip capacity and bounded reads of the proposed extension
   region. Preserve the tested DSP cache fix. Test the full USB reply path,
   rejection of writes and out-of-range requests before installing it.
2. On hardware, back up the ten existing captures and read the complete
   extension region `0x60ede000..0x60efbfff`. Check chip capacity and investigate
   any non-erased contents before allocating space. Empty bytes alone do not
   prove that another subsystem never owns the region.
3. Build an isolated 20-slot variant. Exercise slots 1, 10, 11, 15 and 20,
   reject slot 21, test wheel wrapping and both selection directions, and
   compare existing slots against stock processing in emulation.
4. Test upload/readback, rename, reset and reboot persistence on hardware;
   verify adjacent flash and the original ten captures remain unchanged.
   Check AMP/EQ/MOD selection and preset save/reload for slots 11 through 20.

Adding stored entries does not allocate more simultaneous DSP instances.
It should not increase steady-state audio processing cost; this still needs
regression testing. These slots contain the vendor-converted coefficient format,
not arbitrary native NAM neural-network files.

Reproduce the address and encoding calculations with
`.venv/Scripts/python tools/audit_capture_capacity.py`.
