"""Find which part of a preset load stalls the main loop: toggle one component of the live edit at a
time (amp model, MOD capture override, cab model) and measure the longest gap between telemetry
replies. Live edits only, no preset is written; the edit is restored to the saved preset at the end
and verified byte for byte.

usage: isolate_switch_stall.py --preset 4 --rounds 3 --out work/isolate-stall.jsonl  (0-based index)
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nuxfw.jme import Pedal  # noqa: E402

BLOCKS = [(8, 8), (13, 12), (20, 18), (29, 26), (36, 32), (49, 44), (54, 48), (61, 54)]  # count byte, CC base


def measure(p, log, label, seconds, freeze=5.0):
    t0 = time.monotonic(); last = t0; worst = 0.0; peak = 0
    while time.monotonic() - t0 < seconds:
        item = {'t': time.time(), 'label': label, 'dt': round(time.monotonic() - t0, 3)}
        try:
            d = p.diagnostics(); item['diag'] = d
            now = time.monotonic(); worst = max(worst, now - last); last = now
            peak = d['peak_elapsed_cycles']
        except Exception as error:  # noqa: BLE001
            item['error'] = str(error)
            if time.monotonic() - last > freeze:
                log.write(json.dumps({**item, 'frozen': True}) + '\n')
                raise SystemExit(f'FROZEN after {label}')
        log.write(json.dumps(item) + '\n')
        time.sleep(0.02)
    print(f'{label:28} longest reply gap {worst:5.2f}s  peak {peak}', flush=True)
    return worst


def restore(p, ref):
    for _ in range(3):
        e = p.read_edit()
        if e == ref:
            return True
        for count, base in BLOCKS:
            for i in range(ref[count]):
                if e[count + 1 + i] != ref[count + 1 + i]:
                    p.cc(base + i, ref[count + 1 + i]); time.sleep(0.02)
        time.sleep(0.3)
    return p.read_edit() == ref


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--preset', type=int, default=4)
    ap.add_argument('--rounds', type=int, default=3)
    ap.add_argument('--dwell', type=float, default=2.5)
    ap.add_argument('--out', default='work/isolate-stall.jsonl')
    args = ap.parse_args()
    p = Pedal()
    p.fx_anywhere()
    ref = p.read_preset(args.preset)
    edit = p.read_edit()
    assert edit == ref, 'live edit differs from the saved preset; select it first'
    amp, cab = ref[1], ref[2]
    mod_override = ref[68]
    assert mod_override >= 0x50, 'preset has no MOD override'
    steps = [
        ('amp -> stock 5', lambda: p.cc(1, 5)), (f'amp -> NAM {amp}', lambda: p.cc(1, amp)),
        ('MOD capture off', lambda: p.set_fx_override(3, None)),
        ('MOD capture on', lambda: p.set_fx_override(3, mod_override - 0x50)),
        ('cab -> stock 5', lambda: p.cc(2, 5)), (f'cab -> IR {cab}', lambda: p.cc(2, cab)),
    ]
    out = Path(args.out)
    with out.open('a', encoding='utf-8', buffering=1) as log:
        measure(p, log, 'baseline', args.dwell)
        for rnd in range(args.rounds):
            print(f'-- round {rnd}')
            for label, action in steps:
                action()
                measure(p, log, label, args.dwell)
        print('edit restored:', restore(p, ref))
    p.close()


if __name__ == '__main__':
    main()
