# Soran Dual Stomp Lite firmware: what we know

Reverse engineered from stock firmware **V1.1.1** (`JME-EN_V1.1.1_modified.bin`,
sha256 `fda9d54b…cd31a`) and the bootloader contained in it. Addresses in `m_dfu` / `master` are
runtime addresses (both are linked at 0x0).

## Hardware / platform

| | |
|---|---|
| Platform | NUX (Cherub) "JME" platform, OEM'd as Soran. Model JME-02 = Dual Stomp Lite, JME-01 = Dual Stomp, Tiny Stomp = JME=3 |
| MCU | NXP i.MX RT10xx (Cortex-M7): FlexSPI NOR, SEMC SDRAM, SAI audio, LPSPI, LPUART, ADC_ETC, XBARA, PIT, eDMA (MCUXpresso SDK, IAR toolchain, bare metal) |
| Flash | QSPI NOR (driver supports Winbond W25Qxx / Macronix MX25Lxx / Zbit ZB25Qxx), XIP at 0x60000000 |
| Code | Linked at 0x0 and run from ITCM; SP = 0x2003B000 (DTCM) |
| BLE | UART AT-command module (`AT+SETBLENAME=`, `IND=BLECONNECTED`, `OK=MIDI`): BLE MIDI |
| USB (normal) | `3962:2000` "JME STOMPBOX": UAC2 audio + USB-MIDI (the editor uses MIDI). Serial = app build time `202606041731` |
| USB (DFU) | `9527:c157` "JME STOMPBOX DFU": HID, 64-byte reports, EP 0x81 IN / 0x02 OUT, usage page 0x8C, no report IDs |

Enter DFU mode: **hold Left + Right while powering on.**

## Flash map (absolute)

| Address | Contents | Written by stock updates? |
|---|---|---|
| 0x60000000-0x6000FFFF | i.MX boot header + stage-1 loader (picks app or DFU) | **never** |
| 0x60010000 | product config sector (`BOOT JME=n`, USB/BLE names) | only by DFU cmd 2 (not used in stock files) |
| 0x6003E000 | version string written by the bootloader after an update | by bootloader |
| 0x60040000+ | the flat image below (DFU cmd 4) | yes |

Flat image (offset → address = 0x60040000 + offset):

| Offset | Size | Contents |
|---|---|---|
| 0x000000 | 0x40000 | `master` app (Dual Stomp / **Lite**): build "Jun 4 2026 17:31:40", uses 0x36D08 bytes |
| 0x040000 | 0x40000 | `jme3` app (Tiny Stomp): build "Jun 5 2026 16:34:51" |
| 0x080000 | 0x40000 | float32 DSP tables |
| 0x100000 | 0x40000 | factory presets (names + parameter blocks) |
| 0x140000 | 0x10000 | `m_dfu` DFU bootloader image, built Aug 26 2025 (CFW never modifies it) |
| 0x150000 | → 0xE9DE00 | IR / NAM / drum / coefficient data |

CFW space: `master` 0x38000-0x3F000 (28 KiB) is unused by stock code. 0x3F000-0x40000 is left
alone as a precaution.

## .bin container

See the docstring in `nuxfw/container.py`. Summary: an 0x3BC-byte header (magic `NUX DFU\x02`,
file size, DFU VID/PID, name, vendor, version, section table), then `BINA` (the DFU record stream,
sent verbatim), `TEXT` (release notes) and `EXTR` (256 zero bytes).

There is **no checksum or signature** anywhere: not in the file, not in the transfer, and the
bootloader doesn't verify the image. The only gate is the device ID `AE-100X` (stored bitwise-inverted)
in the info record.

Records: 0x1C-byte header (`[0]` progress %, `[2..3]` BE command, `[0x0C..0x0F]` BE block index)
plus 512 payload bytes. The stream is one info record (cmd 1), N data records (cmd 4, index 0..N-1),
and one final record (cmd 4, index 0xFFFFFFFF). Progress byte for data record *i* of *M*
(M counts the final record) is `ceil(99·(i+1)/M)`, and the final record is 100.

## DFU protocol (bootloader `m_dfu`)

* OUT report `[0]=0x01 [1]=frag 0..8 [2..3]=0 [4..63]=60 bytes`. Nine fragments make one
  540-byte record. Fragment 8 makes the bootloader process the record *inside the USB callback*
  (0xC340 → 0xCA50 → 0xCC3A); the OUT endpoint is re-armed only afterwards, so the host is paced
  by NAKs.
* cmd 1 (info): checks `~payload[0:7] == "AE-100X"`, stores `~payload[8:20]` as version, arms the
  session.
* cmd 4: index 0 resets the write pointer to 0x60040000. A 64 KiB erase happens whenever the
  pointer is 64 KiB-aligned, then 512 bytes are programmed. Index 0xFFFFFFFF writes the last block
  and saves the version to 0x6003E000.
* cmd 2: same as cmd 4 but targets the config sector at 0x60010000 (4 KiB erases). Never used.
* OUT `[0]=0x56` ('V'): the device replies with one 64-byte IN report containing its version.
* No ACKs, no CRC, no read-back.

`nuxfw/dfu.py` has a host implementation plus a simulator of this logic. `cfw.py selftest` pushes
the stock and custom images through the simulator and checks the resulting flash contents.

## Open questions

* The stage-1 loader at 0x60000000 is not in any update file. Its app-copy length (assumed to be
  the whole 256 KiB slot) and any integrity check are unverified. Flashing the CFW base build on
  hardware is the test: if the pedal boots normally, modified app slots work.
* `jme3` vs `master` selection is assumed from build stamps (the pedal's USB serial matches
  `master`'s build time).
* The editor protocol (USB/BLE MIDI SysEx used by Stomp Manager) hasn't been mapped yet.
