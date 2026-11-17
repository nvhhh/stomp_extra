"""Restore capture data and an unsaved live edit from a verified local backup.

Does not write saved presets. Run only after an authorized firmware update.
"""
import argparse,json,sys,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nuxfw import jme
from test_partition_capture_hardware import read_capture

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('archive')
    args=ap.parse_args()
    with zipfile.ZipFile(args.archive) as z:
        assert z.testzip() is None
        target=z.read('live-edit.bin');assert len(target)==98
        captures=[(slot,z.read(f'capture-{slot:02d}-metadata.bin'),z.read(f'capture-{slot:02d}-coefficients.bin')) for slot in range(20)]
    catalog=json.loads((ROOT/'editor/catalog.json').read_text())
    p=jme.Pedal()
    try:
        assert p.fx_anywhere() and p.fx_version==3
        before=p.read_edit()
        (ROOT/'work/edit-before-session-restore.bin').write_bytes(before)
        for slot in (7,3,4):p.set_fx_override(slot,None)
        assert p.read_edit()[67:70]==b'\0\0\0'
        restored=[]
        for slot,meta,data in captures:
            if meta[33]!=1:continue
            if read_capture(p,4,128,slot)!=meta or read_capture(p,0,8192,slot)!=data:
                for kind,blob in ((1,data),(3,meta)):
                    for msg in jme.bulk_messages(0x58,0,slot,kind,blob):
                        p.request(msg,lambda d:p._bulk_pred(0x58,3,None)(d) and jme.unpack7(d[7:-1])[1]==slot,timeout=2,retries=0)
                assert read_capture(p,4,128,slot)==meta
                assert read_capture(p,0,8192,slot)==data
                restored.append(slot)
        def cc(number,value):p.cc(number,value);time.sleep(.003)
        # Inactive parameter bytes are retained by model changes, but sending
        # CCs outside the current model's parameter count writes zero. Prime a
        # wider native model first when a retained nonzero value needs it.
        for m in catalog['modules']:
            count=target[m['count_offset']]
            values=target[m['count_offset']+1:m['count_offset']+1+m['capacity']]
            if any(values[count:]):
                native=[v for v in m['models'] if not v.get('user')]
                widest=max(native,key=lambda v:len(v['params']))
                assert all(not value or i<len(widest['params']) for i,value in enumerate(values))
                cc(m['slot'],widest['index']|64)
                for i in range(len(widest['params'])):cc(m['cc_base']+i,values[i])
        for m in catalog['modules']:cc(m['slot'],target[m['slot']]|64)
        for m in catalog['modules']:
            for i in range(target[m['count_offset']]):cc(m['cc_base']+i,target[m['count_offset']+1+i])
        cc(catalog['volume']['cc'],target[catalog['volume']['offset']])
        p.set_chain(list(target[70:78]))
        for slot,offset in ((7,67),(3,68),(4,69)):
            if target[offset]:p.set_fx_override(slot,target[offset]-0x50)
        for m in catalog['modules']:cc(m['slot'],target[m['slot']])
        time.sleep(.2)
        after=p.read_edit()
        (ROOT/'work/edit-after-session-restore.bin').write_bytes(after)
        differences=[(i,a,b) for i,(a,b) in enumerate(zip(target,after)) if a!=b]
        result={'archive':args.archive,'restored_capture_slots':restored,'edit_matches':not differences,'differences':differences,'diagnostics':p.diagnostics()}
        (ROOT/'work/session-restore-result.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result),flush=True)
        assert not differences,result
    finally:p.close()

if __name__=='__main__':main()
