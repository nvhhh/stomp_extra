# Patches

Each `*.toml` file here describes one feature or fix. List it in `cfw.toml` → `[build].patches`
to include it. The format and safety rules are documented in `nuxfw/patcher.py`. In short:

* every change to existing bytes carries an `expect` with the stock bytes, so a patch can never
  silently apply to the wrong firmware version
* new code and data go into the free CFW area in `master`: **0x38100-0x3F000**
  (0x38000-0x380FF holds the build tag)
* the DFU bootloader region and the top 4 KiB of each app slot are refused unless a patch sets
  `allow_protected = true` (don't)

Since the apps are linked at address 0, a `master` slot offset is also the runtime address. So a
function placed at `master+0x38100` is called as `0x38101` (Thumb bit set).

## Example: call new code from an existing call site

```toml
name = "my-feature"
description = "Hook X to run my code first"

[[op]]                         # 1. drop compiled Thumb-2 code into free space
kind = "blob"
slot = "master"
offset = 0x38100
file = "../features/build/my_feature.bin"

[[op]]                         # 2. redirect an existing `bl original` to the new code
kind = "bl"
slot = "master"
offset = 0x1D3A4               # address of the original BL instruction
expect = "fef7 12fa"           # its stock bytes (from the disassembly)
target = 0x38101               # my code, which must tail-call the original function
```

Disassemble with `tools/disasm.py` (`work/master.asm` is a full linear-sweep listing of the
master app) to find call sites. Patches that change behavior should be tested one at a time on
hardware, with the stock `.bin` ready for recovery.
