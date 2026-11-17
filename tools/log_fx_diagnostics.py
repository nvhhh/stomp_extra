"""Poll read-only editor telemetry, saving each reply/error immediately as JSONL."""
import argparse
import datetime
import json
import time
import urllib.request
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds',type=float,default=120)
    parser.add_argument('--url',default='http://127.0.0.1:8765')
    parser.add_argument('--out',default='work/fx-hardware-diagnostics.jsonl')
    args=parser.parse_args()
    path=Path(args.out)
    path.parent.mkdir(parents=True,exist_ok=True)
    deadline=time.monotonic()+args.seconds
    with path.open('a',encoding='utf-8',buffering=1) as log:
        while time.monotonic()<deadline:
            item={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
            try:
                with urllib.request.urlopen(args.url+'/api/diagnostics',timeout=2) as r:
                    item['telemetry']=json.load(r)
            except Exception as error:
                item['error']=str(error)
            log.write(json.dumps(item)+'\n')
            print(json.dumps(item),flush=True)
            time.sleep(0.5)

if __name__=='__main__': main()
