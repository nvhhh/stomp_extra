# Dual Stomp Lite editor protocol (USB / BLE MIDI)

Reverse engineered from the pedal firmware (master app, V1.1.1) and from Stomp Manager 1.0.2.2
traffic. `nuxfw/jme.py` implements it; `tests/test_jme_capture.py` checks that it reproduces
Stomp Manager's messages byte for byte.

## Framing

`F0 00 21 7A <class> …` (00 21 7A = NUX/Cherub).

| class | meaning |
|---|---|
| `00` | device info. Reply `F0 00 21 7A 10 "V1.1.1"… "JME-01"…` |
| `40` | build info. Reply carries `"202606041731"` (= USB serial) |
| `70` | commands: `70 <cmd> <sub> <payload>`. sub 0 = read, 1 = write, 2 = read reply, 3 = write ack |

**Bulk payloads** (presets, NAM, IR) are `pack7(header + data)`:
- `pack7` encodes the bytes as one LSB‑first bit stream cut into 7‑bit groups.
- The 12‑byte header is `[a, b, c, 0, u32 offset, u32 total]`.
- Data goes in chunks of ≤136 bytes, and each write chunk is acknowledged by a sub‑3 reply that echoes the header.

## Commands

| cmd | read (sub 0) | write (sub 1) |
|---|---|---|
| `0B` preset | hdr `[index]` → 98‑byte record | hdr `[index]`, total 98, record |
| `0C` edit buffer | hdr zeros → 98‑byte record | – |
| `0D` chain order | no payload → eight raw slot IDs | eight raw slot IDs; reply uses **sub 2**, echoing the order |
| `12` preset name | – | raw `[index] + 16 ASCII bytes`. Stomp Manager sends it before `0B` on Save. |
| `09` IR table | raw `[slot]` → `[slot] + pack7(u32 used, name[16], 16 spare)` | same layout (sent after an IR upload) |
| `10` IR data | – | hdr `[slot]`, total 8192: 2048 float32 = gain·reverse(IR at 48 kHz) |
| `58` NAM slot | hdr `[0, slot, 4]` → 128‑byte record: name[32], used@33, float32@52 | type 3 = that record; type 1 = 8192‑byte model (two 1024‑tap float32 filters from Stomp Manager's converter) |
| `14 15 18 19` | global state. `15[0]` = current preset | not captured yet |

Live control:
- **Program Change** n selects preset n.
- **CC 0–7** set the module slots: value = model | 0x40 when bypassed.
- **CC 8–57** set parameters; **CC 58** sets preset volume.
- **CC 59** marks the focused slot.

The pedal answers a preset change or a model change with CCs for the values that changed.

## 98‑byte preset record

| offset | contents |
|---|---|
| 0–7 | slots: 0 OD/FX, 1 Amp, 2 Cab, 3 Mod, 4 Delay, 5 Reverb, 6 Gate, 7 EQ (model, bit 6 = bypass) |
| 8 / 13 / 20 / 29 / 36 / 49 / 54 / 61 | count byte of the Gate / FX / Amp / Cab / EQ / Mod / Delay / Reverb parameter block |
| count+1 … | parameters. CC = block CC base + i: Gate 8, FX 12, Amp 18, Cab 26, EQ 32, Mod 44, Delay 48, Reverb 54 |
| 66 | preset volume (CC 58) |
| 70–77 | signal‑chain order (slot numbers), default 6 0 1 2 7 3 4 5 |
| 82–97 | name (16 ASCII) |

Amp models 30–39 are the 10 NAM slots. Cab models 30–39 are the 10 IR slots.

Chain order is a permutation of slot IDs 0–7, stored at bytes 70–77. It changes
live through command `0D` and persists through the normal preset Save command.
Example Gate → Amp → EQ → OD/FX → Cab → Mod → Delay → Reverb is
`06 01 07 00 02 03 04 05`. The editor validates uniqueness and bounds before
sending because the vendor handler copies these bytes without validating them.
The stock routine at `0x130C2` rebuilds the actual DSP function sequence from
these bytes. This works with both stock V1.1.1 and FX Anywhere.

Verified through emulation of the original command handlers and DSP order builder,
and by writing/reading the example order on the connected pedal, then restoring
the original edit buffer byte-for-byte. No preset was overwritten during that test.
The cab's MIC and POSITION parameters are selectors:
- MIC: M160, E906, MD421, R121, SM57, SM58, SM7B, U47
- POSITION: EDGE, MIDDLE, CENTER

## .jmePreset (Stomp Manager export)

The file is 8359 bytes:
- byte 35: preset index
- bytes 36–133: the record
- byte 134: 0xFF (no embedded user amp/IR)
- float32 1.0 at byte 167
- zeros everywhere else

## Not yet known

The optional custom firmware's `0x30` FX Anywhere extension is documented in
[FX-ANYWHERE.md](FX-ANYWHERE.md#sysex-extension). Probe its capability signature
before using it; stock firmware does not implement it.

- Writes for global settings (`14/15/18/19`): no capture yet.
- Option order for Chorus+/Uni Vibe MODE and Harmony KEY/MODE.
- Stomp Manager's exact IR gain rule. The editor matches its level by L2; on the captured IR the result is identical to within 1e‑7.
- Clearing an IR/NAM slot.
