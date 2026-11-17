"""Host-side capability gating, carrier selection, and preservation of preset bytes."""
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nuxfw import jme
from editor.server import App, CATALOG, cc_offset

class FakePedal:
    def __init__(self):
        self.rec=bytearray(98)
        self.rec[3]=0x40
        self.calls=[]
    def read_edit(self): return bytes(self.rec)
    def cc(self,n,v):
        self.calls.append(('cc',n,v))
        off=cc_offset(n)
        if off is not None: self.rec[off]=v
    def set_fx_override(self,slot,model):
        self.calls.append(('override',slot,model))
        self.rec[jme.FX_SLOTS[slot][0]]=0 if model is None else 0x50+model
    def write_preset(self,index,rec,name): self.saved=(index,rec,name)

class EditorTests(unittest.TestCase):
    def test_failed_midi_send_removes_waiter_without_retrying_write(self):
        p=jme.Pedal.__new__(jme.Pedal)
        p._lock=threading.Lock()
        p._waiters=[]
        with patch.object(p,'send',side_effect=RuntimeError('MIDI output disconnected')) as send:
            with self.assertRaisesRegex(RuntimeError,'disconnected'):
                p.request(b'write',lambda d: True)
        self.assertEqual(send.call_count,1)
        self.assertEqual(p._waiters,[])

    def test_split_bank_upload_refresh_and_bounds(self):
        for physical in (0,9,10,19):
            a=self.app()
            a.s.update(split_captures=True,capture_slots=True,nam=[None]*20)
            local=physical%10
            a.pedal.rec[7]=0
            a.pedal.rec[67]=0x60+local
            a.pedal.upload_nam=lambda *args: a.pedal.calls.append(('upload',args[0]))
            a.pedal.nam_name=lambda slot: 'test'
            a._task=lambda label,run: run(lambda *args: None)
            with patch('editor.server.namconv.convert',return_value=(bytes(8192),1.0)):
                a.upload_nam(physical,'test',b'file')
            self.assertIn(('upload',physical),a.pedal.calls)
            refreshed=('override',7,16+local) in a.pedal.calls
            self.assertEqual(refreshed,physical>=10)
        for slot in (-1,20):
            with self.assertRaises(ValueError): a.upload_nam(slot,'test',b'file')

    def test_capture_selection_requires_new_firmware(self):
        with patch('editor.server.time.sleep'):
            a=self.app()
            with self.assertRaises(ValueError): a.model(7,48)
            self.assertFalse(a.pedal.calls)
            a.s['capture_slots']=True
            for slot in (7,3):
                for model in range(48,58):
                    a.model(slot,model)
                    self.assertEqual(a.pedal.rec[jme.FX_SLOTS[slot][0]],0x60+model-48)
            with self.assertRaises(ValueError): a.model(4,48)

    def app(self,capable=True):
        a=App.__new__(App)
        a.cond=threading.Condition()
        a._model_lock=threading.Lock()
        a.version=0
        a.s={'fx_anywhere':capable,'presets':[None]*99}
        a.pedal=FakePedal()
        return a
    def test_select_all_extra_models_and_save(self):
        with patch('editor.server.time.sleep'):
            for slot in jme.FX_SLOTS:
                for model in range(16):
                    a=self.app()
                    a.model(slot,32+model)
                    spare,carrier=jme.FX_SLOTS[slot]
                    self.assertEqual(a.pedal.rec[spare],0x50+model)
                    self.assertEqual(a.pedal.rec[slot],carrier|(0x40 if slot==3 else 0))
                    self.assertEqual(a.pedal.calls[-1],('override',slot,model))
                    a.save(10,'FX test')
                    self.assertEqual(a.pedal.saved[1][spare],0x50+model)
    def test_native_selection_clears_override(self):
        a=self.app()
        with patch('editor.server.time.sleep'):
            a.model(7,38)
            a.model(7,0)
        self.assertEqual(a.pedal.rec[67],0)
        self.assertEqual(a.pedal.rec[7],0)
    def test_stock_device_rejects_extended_models(self):
        a=self.app(False)
        with self.assertRaises(ValueError): a.model(7,38)
        self.assertFalse(a.pedal.calls)
        with patch('editor.server.time.sleep'): a.model(7,0)
        self.assertFalse(any(c[0]=='override' for c in a.pedal.calls))
    def test_capability_and_write_messages(self):
        p=jme.Pedal.__new__(jme.Pedal)
        p._io=threading.Lock()
        calls=[]
        def request(msg,pred,**kwargs):
            calls.append(msg)
            markers=bytearray(3)
            if msg[6]==1:
                markers[(7,3,4).index(msg[7])]=0 if msg[8]==0 else msg[8]+0x4f
            reply=jme.sysex(0x30,2 if msg[6]==0 else 3,b'FXA\x01'+markers)
            self.assertTrue(pred(reply))
            return reply
        p.request=request
        self.assertTrue(p.fx_anywhere())
        p.set_fx_override(7,6)
        self.assertEqual(calls,[jme.sysex(0x30,0),jme.sysex(0x30,1,b'\x07\x07')])
        with patch.object(p,'request',side_effect=TimeoutError): self.assertFalse(p.fx_anywhere())
        with self.assertRaises(ValueError): p.set_fx_override(1,0)

if __name__=='__main__': unittest.main(verbosity=2)
