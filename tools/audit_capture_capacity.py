"""Offline capture-bank arithmetic; does not establish physical flash capacity."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nuxfw.container import Firmware
stock = (ROOT / 'firmware/stock/JME-EN_V1.1.1_modified.bin').read_bytes()
assert hashlib.sha256(stock).hexdigest() == 'fda9d54bd168554bf69b2a7b5a02830dc69b0ac4993e7daababc5d7dfbdcd31a'
image = Firmware.parse(stock).image
base, stride = 0x60ec0000, 0x3000
rows = []
for count in (10, 15, 20):
    end = base + count * stride
    rows.append(dict(captures=count, reserved_KiB=count*12,
                     additional_KiB=(count-10)*12, end_exclusive=hex(end),
                     remaining_if_16MiB_KiB=(0x61000000-end)//1024,
                     last_amp_model=30+count-1,
                     last_eq_mod_marker=hex(0x60+count-1)))
    assert 30+count-1 < 0x40
    assert 0x60+count-1 < 0x80
result = dict(stock_image_end_exclusive=hex(0x60040000+len(image)),
              physical_capacity_verified=False, tail_contents_verified=False,
              candidates=rows)
print(json.dumps(result, indent=2))
