"""Authorized live capture diagnosis; no preset saves, stop on transport errors."""
import argparse,json,struct,sys,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nuxfw import jme

def read_capture(p,kind,size,slot=10):
    result=bytearray()
    for off in range(0,size,136):
        def predicate(msg):
            if not p._is(0x58,2)(msg):return False
            data=jme.unpack7(msg[7:-1])
            return len(data)>=12 and data[1:3]==bytes([slot,kind]) and struct.unpack_from('<I',data,4)[0]==off
        msg=p.request(jme.sysex(0x58,0,jme.pack7(jme.bulk_header(0,slot,kind,off,0 if off==0 else size))),predicate,timeout=2,retries=0)
        data=jme.unpack7(msg[7:-1]);assert struct.unpack_from('<I',data,8)[0]==size
        result.extend(data[12:12+min(136,size-off)])
    assert len(result)==size
    return bytes(result)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('phase',choices=('prepare','backup','baseline','eq','mod','both'))
    ap.add_argument('--seconds',type=float,default=5)
    ap.add_argument('--od-on',action='store_true',help='Temporarily enable the existing OD model')
    ap.add_argument('--after-reverb',action='store_true',help='EQ test only: temporarily move EQ to the end of the chain')
    ap.add_argument('--build-label',default='0.5.1-mac-diag',help='Operator label from the verified flash log, not USB readback')
    args=ap.parse_args()
    if args.after_reverb and args.phase!='eq':ap.error('--after-reverb requires the eq phase')
    p=jme.Pedal()
    path=ROOT/'work/fx01-partition-hardware.jsonl'
    with path.open('a',buffering=1) as log:
        def record(event,**data):log.write(json.dumps(dict(time=time.time(),event=event,phase=args.phase,build_label=args.build_label,od_on=args.od_on,after_reverb=args.after_reverb,**data))+'\n')
        try:
            # This stock USB query retains V1.1.1; it is not the CFW tag shown
            # on the pedal. Use only after a recorded flash/normal boot.
            info=p.info();assert info['model']=='JME-01',info
            assert p.fx_anywhere() and p.fx_version==3
            before=p.read_edit()
            baseline=p.diagnostics();nominal=baseline['period_cycles']
            assert 90000<nominal<110000,baseline
            record('before',info=info,edit=before.hex(),diagnostics=baseline,metrics=p.capture_metrics())
            if args.phase=='backup':
                target=ROOT/f'backups/library-{time.time_ns()}.zip'
                used=[]
                with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
                    z.writestr('info.json',json.dumps(info));z.writestr('live-edit.bin',before)
                    for slot in range(20):
                        meta=read_capture(p,4,128,slot);data=read_capture(p,0,8192,slot)
                        z.writestr(f'capture-{slot:02d}-metadata.bin',meta)
                        z.writestr(f'capture-{slot:02d}-coefficients.bin',data)
                        if meta[33]==1:used.append(slot)
                    for slot in range(99):z.writestr(f'preset-{slot:02d}.bin',p.read_preset(slot))
                assert p.read_edit()==before
                record('library_backup',path=str(target),used_capture_slots=used)
                print(json.dumps({'backup':str(target),'used_capture_slots':used}),flush=True)
                return
            assert before[67:69]==b'\0\0','Leave EQ/MOD on native effects before this test'
            if args.phase=='prepare':
                assert before[3]&64 and before[7]&64,'Bypass EQ/MOD before restoring capture storage'
                expected_meta=(ROOT/'backups/fx01-crash-metadata.bin').read_bytes()
                expected_data=(ROOT/'backups/fx01-crash-coefficients.bin').read_bytes()
                meta=read_capture(p,4,128);data=read_capture(p,0,8192)
                stamp=time.time_ns()
                (ROOT/f'work/fx01-partition-before-{stamp}-meta.bin').write_bytes(meta)
                (ROOT/f'work/fx01-partition-before-{stamp}-data.bin').write_bytes(data)
                if (meta,data)!=(expected_meta,expected_data):
                    for kind,blob in ((1,expected_data),(3,expected_meta)):
                        for msg in jme.bulk_messages(0x58,0,10,kind,blob):
                            p.request(msg,lambda d:p._bulk_pred(0x58,3,None)(d) and jme.unpack7(d[7:-1])[1]==10,timeout=2,retries=0)
                    assert read_capture(p,4,128)==expected_meta
                    assert read_capture(p,0,8192)==expected_data
                assert p.read_edit()==before
                record('capture_verified');print('FX01 coefficients and metadata verified; edit unchanged.',flush=True)
                return
            slots={'baseline':[],'eq':[7],'mod':[3],'both':[7,3]}[args.phase]
            assert read_capture(p,4,128)[33]==1,'FX01 is empty; prepare first'
            if args.od_on:p.cc(0,before[0]&63)
            if args.after_reverb:
                order=list(before[70:78]);order.remove(7);order.append(7)
                p.set_chain(order)
            for slot in slots:
                p.cc(slot,0 if slot==7 else 5);time.sleep(.1);p.set_fx_override(slot,16)
            record('selected',edit=p.read_edit().hex())
            samples=[];deadline=time.monotonic()+args.seconds
            while time.monotonic()<deadline:
                d=p.diagnostics();m=p.capture_metrics();samples.append(d)
                record('sample',diagnostics=d,metrics=m)
                if any(m['eq' if slot==7 else 'mod']['stage']==3 for slot in slots):
                    print('Overload guard tripped:',json.dumps(m),flush=True);break
                if slots and d['consistent'] and not d['busy'] and d['elapsed_cycles']>=nominal-5000:
                    print('Insufficient whole-callback headroom:',json.dumps(d),flush=True);break
                time.sleep(.1)
            for slot in reversed(slots):
                p.set_fx_override(slot,None);p.cc(slot,before[slot]);time.sleep(.1)
                if slot==3:
                    for i in range(before[49]):p.cc(44+i,before[50+i])
            if args.after_reverb:p.set_chain(list(before[70:78]))
            if args.od_on:p.cc(0,before[0])
            time.sleep(.15)
            after=p.read_edit();record('restored',edit=after.hex(),diagnostics=p.diagnostics())
            assert after==before,{'before':before.hex(),'after':after.hex()}
            print(json.dumps({'samples':len(samples),'edit_restored':True,
                'eq_stages':sorted(set(d['eq_stage'] for d in samples)),
                'mod_stages':sorted(set(d['mod_stage'] for d in samples)),
                'last':samples[-1] if samples else None}),flush=True)
        except Exception as e:
            record('error',error=repr(e));raise
        finally:p.close()

if __name__=='__main__':main()
