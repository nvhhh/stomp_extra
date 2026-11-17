"""Functional instruction counts, NOT target cycles or audio headroom."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
import test_fx_concurrency as t

b = t.b
results = {}
for custom in (False, True):
    u = t.setup()
    if not custom:
        u.mem_write(b.EDIT+67, bytes(2))
        b.call(u, 0x1525c)
        b.call(u, 0x144c4, (5, 0))
    counts = [0, 0, 0]
    def count(uc, pc, size, context):
        if block == 149:
            counts[i] += 1
    # Invalidate translated blocks when adding instrumentation after setup.
    hook = u.hook_add(b.UC_HOOK_CODE, count)
    u.ctl_remove_cache(0, 0x40000)
    for block in range(150):
        for i, (parent, _, _, _) in enumerate(t.BLOCKS):
            b.call(u, parent, (b.IN,b.OUT,b.LEFT,b.RIGHT))
    u.hook_del(hook)
    results['custom' if custom else 'native_carriers'] = counts
results['warning'] = 'Instruction counts only; no CPU cycles, interrupts, cache or SDRAM latency modeled.'
results['nam_runtime_count_after_iar_init'] = b.RAM[0x10b88+0x1d]
print(json.dumps(results, indent=2))
