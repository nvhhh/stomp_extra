"""Alternate two saved presets over USB while polling read-only telemetry; stop at the first freeze.

Selecting a preset discards unsaved live edits but never writes presets. Each sample is written
to the JSONL log immediately, so the last lines before a freeze survive.

usage: repro_preset_switch.py --a 4 --b 3 --trials 25 --dwell 2 --out work/preset-switch.jsonl
(indices are 0-based; the pedal display is 1-based)
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nuxfw.jme import Pedal  # noqa: E402


def sample(p):
    item = {}
    try:
        item['diag'] = p.diagnostics()
        item['metrics'] = p.capture_metrics()
    except Exception as error:  # noqa: BLE001
        item['error'] = f'{type(error).__name__}: {error}'
    return item


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--a', type=int, default=4)
    ap.add_argument('--b', type=int, default=3)
    ap.add_argument('--trials', type=int, default=25)
    ap.add_argument('--dwell', type=float, default=2.0)
    ap.add_argument('--freeze', type=float, default=4.0, help='seconds without a reply = frozen')
    ap.add_argument('--out', default='work/preset-switch.jsonl')
    args = ap.parse_args()
    p = Pedal()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    last_ok = time.monotonic()
    with out.open('a', encoding='utf-8', buffering=1) as log:
        for trial in range(args.trials):
            for index in (args.a, args.b):
                p.select(index)
                t0 = time.monotonic()
                log.write(json.dumps({'t': time.time(), 'trial': trial, 'select': index}) + '\n')
                while time.monotonic() - t0 < args.dwell:
                    item = sample(p)
                    item.update(t=time.time(), trial=trial, preset=index, since_select=round(time.monotonic() - t0, 3))
                    while not p.events.empty():
                        item.setdefault('events', []).append(p.events.get().data.hex())
                    log.write(json.dumps(item) + '\n')
                    if 'error' not in item:
                        last_ok = time.monotonic()
                        d = item['diag']
                        print(f"{trial:2} p{index} +{item['since_select']:5.2f}s el={d['elapsed_cycles']:6} pk={d['peak_elapsed_cycles']:6} "
                              f"unf={d['unfinished_passes']} eq={d['eq_key']}/{d['eq_stage']} mod={d['mod_key']}/{d['mod_stage']}", flush=True)
                    elif time.monotonic() - last_ok > args.freeze:
                        print(f'FROZEN: trial {trial}, preset {index}, {item["error"]}', flush=True)
                        log.write(json.dumps({'t': time.time(), 'frozen': True, 'trial': trial, 'preset': index}) + '\n')
                        return 2
                    time.sleep(0.02)
    p.close()
    print('no freeze')
    return 0


if __name__ == '__main__':
    sys.exit(main())
