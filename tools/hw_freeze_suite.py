"""Hardware freeze/stall suite for 0.6.3 (profiler build). Live changes and preset selects only:
never saves presets or uploads data. Restores the starting edit (a saved preset) at the end.

Each step runs an action, then polls telemetry every ~25 ms for `dwell` seconds:
  gap      longest wait between telemetry replies (main loop unresponsive), > 0.15 s = stall
  frozen   no reply for --freeze seconds (stop)
  stages   EQ/MOD capture key/stage at the end of the dwell (3 = latched dry)
and reads the profiler header (longest main-loop stall, settles, debt) after each test group.

usage: hw_freeze_suite.py [--groups a,b,...] [--out work/hw-suite-0.6.3.jsonl] [--home 4]
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nuxfw.jme import Pedal, sysex  # noqa: E402

HEADER = ('heartbeat', 'heartbeat_seen', 'stall_callbacks', 'stall_samples', 'longest_stall',
          'longest_samples', 'stalls', 'gap_since_sample', 'longest_start_pass', 'current_start_pass',
          'last_stall', 'longest_gap', 'settle_left', 'settle_quiet', 'settle_redraw_seen', 'recalls',
          'debt', 'max_debt', 'debt_latches', 'settles_by_quiet', 'settles_by_limit')


class Frozen(Exception):
    pass


class Suite:
    def __init__(self, out, freeze):
        self.p = Pedal()
        self.p.fx_anywhere()
        self.log = open(out, 'a', encoding='utf-8', buffering=1)
        self.freeze = freeze
        self.results = []

    def header(self):
        words = []
        for page in (0, 1):
            r = self.p.request(sysex(0x33, 0, bytes([page])), self.p._is(0x33, 2), timeout=0.5, retries=1)
            pl = r[7:-1]
            words += [sum(v << (7*i) for i, v in enumerate(pl[q:q+5])) for q in range(4, 84, 5)]
        return dict(zip(HEADER, words))

    def watch(self, group, label, dwell):
        t0 = time.monotonic(); last = t0; worst = 0.0; peak = 0; d = None
        while time.monotonic() - t0 < dwell:
            try:
                d = self.p.diagnostics()
                now = time.monotonic(); worst = max(worst, now - last); last = now
                peak = max(peak, d['peak_elapsed_cycles'])
            except Exception as error:  # noqa: BLE001
                if time.monotonic() - last > self.freeze:
                    self.write(group=group, label=label, frozen=True, error=str(error))
                    raise Frozen(f'{group}: {label}')
            time.sleep(0.02)
        row = dict(group=group, label=label, gap=round(worst, 3), peak=peak,
                   eq=(d['eq_key'], d['eq_stage']) if d else None, mod=(d['mod_key'], d['mod_stage']) if d else None,
                   unfinished=d['unfinished_passes'] if d else None)
        self.write(**row)
        self.results.append(row)
        flag = ' STALL' if worst > 0.15 else ''
        latched = ' LATCHED' if d and 3 in (d['eq_stage'], d['mod_stage']) else ''
        print(f"{group:10} {label:34} gap {worst:5.2f}s peak {peak:6} eq {row['eq']} mod {row['mod']}{flag}{latched}", flush=True)
        return row

    def step(self, group, label, action, dwell=1.5):
        action()
        return self.watch(group, label, dwell)

    def summary(self, group):
        h = self.header()
        self.write(group=group, profiler=h)
        print(f"{group:10} profiler: longest stall {h['longest_stall']} cb, stalls {h['stalls']}, recalls {h['recalls']}, "
              f"settles quiet/limit {h['settles_by_quiet']}/{h['settles_by_limit']}, max debt {h['max_debt']}, "
              f"debt latches {h['debt_latches']}", flush=True)
        return h

    def write(self, **row):
        row['t'] = time.time()
        self.log.write(json.dumps(row) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--groups', default='pairs,rapid,sweep,live,dual,steady')
    ap.add_argument('--out', default='work/hw-suite-0.6.3.jsonl')
    ap.add_argument('--home', type=int, default=4, help='saved preset to start from and return to (0-based)')
    ap.add_argument('--freeze', type=float, default=5.0)
    args = ap.parse_args()
    s = Suite(args.out, args.freeze)
    p = s.p
    groups = args.groups.split(',')
    sel = lambda i: (lambda: p.select(i))
    try:
        s.step('start', f'select home {args.home + 1}', sel(args.home), 2.5)
        home = p.read_preset(args.home)
        assert p.read_edit() == home, 'home preset did not load'
        s.summary('start')
        if 'pairs' in groups:
            # Display numbers: 5 JCM2550 (NAM+MOD capture+IR), 4 Mes.BADLND (NAM+EQ capture+IR),
            # 2 Roland (NAM+MOD capture FX02+IR), 8 Funky (no capture), 1 Orange (NAM, no capture)
            for a, b in ((4, 3), (4, 7), (3, 1), (1, 4), (3, 7), (0, 4)):
                for r in range(5):
                    s.step('pairs', f'{a+1} -> {b+1} (round {r})', sel(b))
                    s.step('pairs', f'{b+1} -> {a+1} (round {r})', sel(a))
            s.summary('pairs')
        if 'rapid' in groups:
            order = [4, 3, 1, 7, 0, 4, 1, 3]
            for r in range(6):
                for i in order:
                    s.step('rapid', f'select {i+1} (0.15 s)', sel(i), 0.15)
            s.step('rapid', 'settle after rapid', lambda: None, 2.0)
            s.summary('rapid')
        if 'sweep' in groups:
            for i in range(99):
                s.step('sweep', f'select {i+1}', sel(i), 0.8)
            s.summary('sweep')
        if 'live' in groups:
            s.step('live', 'select home', sel(args.home), 2.0)
            mod = home[68]
            for r in range(5):
                s.step('live', 'MOD capture off', lambda: p.set_fx_override(3, None), 1.0)
                s.step('live', 'MOD capture on', lambda: p.set_fx_override(3, mod - 0x50), 1.5)
            for fx in (16, 17, 18, 16):
                s.step('live', f'MOD capture FX{fx-15:02d}', lambda fx=fx: p.set_fx_override(3, fx), 1.5)
            for r in range(3):
                s.step('live', 'amp -> stock', lambda: p.cc(1, 5), 1.0)
                s.step('live', 'amp -> NAM', lambda: p.cc(1, home[1]), 1.5)
                s.step('live', 'MOD bypass', lambda: p.cc(3, home[3] | 0x40), 1.0)
                s.step('live', 'MOD on', lambda: p.cc(3, home[3] & 0x3f), 1.5)
            s.summary('live')
        if 'dual' in groups:
            # EQ + MOD captures with a NAM amp: the combination that hung 0.6.0. Guards must hold.
            s.step('dual', 'select home', sel(args.home), 2.0)
            s.step('dual', 'EQ capture FX02 on (dual)', lambda: p.set_fx_override(7, 17), 3.0)
            s.step('dual', 'dual steady', lambda: None, 5.0)
            for r in range(3):
                s.step('dual', 'EQ capture off', lambda: p.set_fx_override(7, None), 1.0)
                s.step('dual', 'EQ capture on', lambda: p.set_fx_override(7, 17), 2.0)
            s.step('dual', 'switch away (to 8)', sel(7), 1.5)
            s.step('dual', 'back to home', sel(args.home), 1.5)
            s.step('dual', 'EQ capture on, then switch to 4', lambda: (p.set_fx_override(7, 17), time.sleep(0.5), p.select(3)), 2.0)
            s.summary('dual')
        if 'steady' in groups:
            s.step('steady', 'select home', sel(args.home), 2.0)
            s.step('steady', '30 s steady', lambda: None, 30.0)
            s.summary('steady')
    except Frozen as error:
        print('FROZEN:', error, flush=True)
        return 2
    s.step('end', 'select home (restore edit)', sel(args.home), 2.5)
    print('edit restored:', p.read_edit() == home)
    stalls = [r for r in s.results if r['gap'] > 0.15]
    latched = [r for r in s.results if r['eq'] and 3 in (r['eq'][1], r['mod'][1])]
    print(f'steps {len(s.results)}, stalls {len(stalls)}, latched {len(latched)}, no freeze')
    p.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
