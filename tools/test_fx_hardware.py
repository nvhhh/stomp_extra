"""Controlled live-edit tests; never save presets. Stop on a failed command.

Use only during an authorized hardware diagnosis. The effects are audible.
The JSONL file records action boundaries, replies, snapshots and timeouts.
"""
import argparse
import datetime
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase',choices=['baseline','one','two','three','headroom','restore_reverb','digital_delay','tape_delay','amp_off','amp_on','light_three','cab_off','cab_on','mod_off'])
    p.add_argument('--seconds',type=float,default=10)
    p.add_argument('--preset',type=int,help='Select this zero-based preset before sampling')
    p.add_argument('--od-model',type=int,default=7)
    p.add_argument('--log',default='work/fx-hardware-stages.jsonl')
    a=p.parse_args()
    path=Path(a.log); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a',encoding='utf-8',buffering=1) as log:
        def record(kind,**values):
            entry=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       phase=a.phase,kind=kind,**values)
            log.write(json.dumps(entry)+'\n')
            if kind!='sample': print(json.dumps(entry),flush=True)
        def request(endpoint,data=None):
            req=urllib.request.Request('http://127.0.0.1:8765/api/'+endpoint,
                data=None if data is None else json.dumps(data).encode(),
                headers={'Content-Type':'application/json'})
            try:
                with urllib.request.urlopen(req,timeout=10) as r: return json.load(r)
            except urllib.error.HTTPError as e:
                raise RuntimeError(e.read().decode()) from e
        def action(endpoint,data):
            record('before_action',endpoint=endpoint,data=data,telemetry=request('diagnostics'))
            reply=request(endpoint,data)
            record('after_action',endpoint=endpoint,reply=reply)
        try:
            record('start',state=request('state'),telemetry=request('diagnostics'))
            if a.preset is not None:
                action('select',{'index':a.preset})
            if a.phase=='one':
                action('model',{'slot':7,'model':0})
                action('model',{'slot':3,'model':5})
                action('model',{'slot':0,'model':a.od_model})
                action('cc',{'cc':0,'value':a.od_model})
            elif a.phase=='two':
                action('model',{'slot':7,'model':32})
                action('cc',{'cc':7,'value':0})
            elif a.phase=='three':
                action('model',{'slot':3,'model':32})
                action('cc',{'cc':3,'value':5})
            elif a.phase=='light_three':
                action('model',{'slot':3,'model':45})
                action('cc',{'cc':3,'value':5})
            elif a.phase=='mod_off':
                rec=bytes.fromhex(request('state')['edit'])
                action('cc',{'cc':3,'value':rec[3]|64})
            elif a.phase=='headroom':
                rec=bytes.fromhex(request('state')['edit'])
                action('cc',{'cc':5,'value':rec[5]|64})
            elif a.phase=='restore_reverb':
                rec=bytes.fromhex(request('state')['edit'])
                action('cc',{'cc':5,'value':rec[5]&63})
            elif a.phase=='digital_delay':
                action('cc',{'cc':5,'value':2})
                action('model',{'slot':4,'model':1})
            elif a.phase=='tape_delay':
                action('model',{'slot':4,'model':3})
            elif a.phase in ('amp_off','amp_on'):
                rec=bytes.fromhex(request('state')['edit'])
                action('cc',{'cc':1,'value':(rec[1]|64) if a.phase=='amp_off' else (rec[1]&63)})
            elif a.phase in ('cab_off','cab_on'):
                rec=bytes.fromhex(request('state')['edit'])
                action('cc',{'cc':2,'value':(rec[2]|64) if a.phase=='cab_off' else (rec[2]&63)})
            deadline=time.monotonic()+a.seconds
            samples=[]
            while time.monotonic()<deadline:
                d=request('diagnostics')
                record('sample',telemetry=d)
                samples.append(d)
                time.sleep(0.25)
            valid=[d for d in samples if d['consistent'] and not d['busy'] and d['period_cycles']]
            record('complete',state=request('state'),samples=len(samples),valid=len(valid),
                elapsed_min=min((d['elapsed_cycles'] for d in valid),default=None),
                elapsed_max=max((d['elapsed_cycles'] for d in valid),default=None),
                period_min=min((d['period_cycles'] for d in valid),default=None),
                period_max=max((d['period_cycles'] for d in valid),default=None))
        except Exception as error:
            record('error',error=str(error))
            raise

if __name__=='__main__': main()
