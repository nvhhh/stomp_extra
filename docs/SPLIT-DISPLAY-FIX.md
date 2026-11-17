# 0.4.1-display

**Superseded by 0.4.2-display.** Hardware testing exposed an error in this
implementation: type 5 is a bitmap copy, not a color fill. The description below
records the original mistaken interpretation. Do not flash 0.4.1 again.

## 0.4.2 correction

The 0.4.1 path called 0x12188 with a null source pointer, copying ITCM contents
into the framebuffer. Comparing clean versus dirty frames passed because both
received the same incorrect bitmap; that test was insufficient.

0.4.2 uses command type 3, invoking 0x12128 with x=0, y=0, height=240,
width=320 and RGB565 color=0. Its framebuffer is rotated in memory, hence the
height/width argument ordering. No bitmap source pointer is used.

`tests/test_capture_solid_fill.py` reproduces the null bitmap call in 0.4.1,
asserts the precise fill call and absence of bitmap-copy calls in 0.4.2, checks
black background pixels, and exercises all ten FX entries in EQ and MOD with
both display-list buffer selectors. Inherited bank, cache, DSP and USB tests
also pass. The rendered framebuffer was visually inspected.

Build config: cfw-fx-split-solid-fill.toml. Builder flags:
`--diagnostic --cache-state --split-bank --display-fix --solid-fill`.

Artifact: build/soran-cfw-0.4.2-display-on-1.1.1.bin
SHA256: 8fc4f6ed45b5ea2f420a08577566dd1a74a656ddb36225e960ee3970cd7e67db

0.4.2 is built and offline-tested; installation and physical display validation
remain outstanding.

## Historical 0.4.1 investigation

Fixes the split-bank capture page's missing background and incorrect slot number.
No changes to storage allocation, DSP routing or capture bank separation.

The capture path in 0.4.0 used sprite ID 0xffff for command zero. The stock
renderer skips that invalid sprite rather than clearing the framebuffer. Text
and artwork from the previous page therefore remain under the capture UI.
The old emulator tests checked strings without loading real glyph metrics or
rendering pixels, so they missed the defect.

The fixed path uses the stock full-screen color-fill command (type 5, black)
before drawing capture controls. It also uses number sprite 0x396 + local slot,
rather than 0x398 + extended selection, which displayed 19 for FX 01.

`tests/test_capture_display.py` initializes the real stock sprite/glyph tables
with 0x11b78 and executes the framebuffer renderer at 0x1fa94. The old image
produces different results on clean and dirty framebuffers; the fixed image
produces identical results for FX 01 and FX 10 on both EQ and MOD. It also reruns
all seven split-bank tests, including DSP/cache and USB diagnostics regressions.
The new container passes the full build selftest.

Build:
```
.venv/Scripts/python patches/fx-controls/build_patch.py --diagnostic --cache-state --split-bank --display-fix
.venv/Scripts/python cfw.py selftest -c cfw-fx-split-display-fix.toml
.venv/Scripts/python tests/test_capture_display.py
```

Artifact: build/soran-cfw-0.4.1-display-on-1.1.1.bin
SHA256: 90cd656e549ce13302ea5d8db7f2252c5a8bf7c5374ef4285f45ca619a5d9b33

Not flashed yet. Physical display confirmation remains required.

The separate editor issue was a stale running server that recognized only
FXA capability versions 1 and 2, causing version 3 firmware to lose all extended
choices. Updated server started at http://127.0.0.1:8766 and read-only state
verification reports connected=true, fx_anywhere=true, capture_slots=true,
split_captures=true, 20 NAM entries and no error. The old server at port 8765
remains running; use port 8766. Automatic approval review rejected stopping the
old process, so the new instance was started without terminating it.
