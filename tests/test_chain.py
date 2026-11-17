"""Exercise the vendor's chain command and live DSP dispatch ordering."""
import itertools
import struct
import threading
import unittest
from unittest.mock import Mock
from test_fx_anywhere import make, call, word, EDIT, PARAM, UC_HOOK_CODE, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_PC, UC_ARM_REG_LR
import test_fx_editor
from nuxfw import jme

EXAMPLE=[6,1,7,0,2,3,4,5]

class ChainTests(unittest.TestCase):
    def test_validation(self):
        for order in itertools.permutations(range(8)):
            self.assertEqual(jme.validate_chain(order),bytes(order))
        for bad in [[],[0]*8,list(range(9)),[-1,1,2,3,4,5,6,7],[8,1,2,3,4,5,6,7],
                    [False,1,2,3,4,5,6,7],[0.,1,2,3,4,5,6,7],'60127345',None]:
            with self.assertRaises(ValueError): jme.validate_chain(bad)

    def test_actual_vendor_handlers_and_dispatch(self):
        for patched in [False,True]:
            u=make(patched)
            # main's preset setup binds the active record after IAR startup.
            u.mem_write(0x200101f4,struct.pack('<I',EDIT))
            replies=[]
            def reply(uc,addr,size,user):
                replies.append(bytes(uc.mem_read(uc.reg_read(UC_ARM_REG_R0),uc.reg_read(UC_ARM_REG_R1))))
                self.assertEqual(uc.reg_read(UC_ARM_REG_R2),1)
                uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
            u.hook_add(UC_HOOK_CODE,reply,begin=0xa2ee,end=0xa2ee)
            before=bytes(u.mem_read(EDIT,98))
            for order in [EXAMPLE,list(reversed(EXAMPLE)),list(jme.DEFAULT_CHAIN)]:
                msg=jme.sysex(jme.CMD_CHAIN,1,bytes(order))
                u.mem_write(PARAM,msg)
                call(u,0x9fc0,(PARAM,len(msg),1))
                self.assertEqual(replies.pop(),jme.sysex(jme.CMD_CHAIN,2,bytes(order)))
                rec=bytes(u.mem_read(EDIT,98))
                self.assertEqual(rec[70:78],bytes(order))
                self.assertEqual(rec[:70]+rec[78:],before[:70]+before[78:])
                call(u,0x130c2)
                self.assertEqual([word(u,0x200027c8+24*i) for i in range(8)],
                                 [word(u,0x20002898+4*slot) for slot in order])
                msg=jme.sysex(jme.CMD_CHAIN,0)
                u.mem_write(PARAM,msg)
                call(u,0x9fc0,(PARAM,len(msg),1))
                self.assertEqual(replies.pop(),jme.sysex(jme.CMD_CHAIN,2,bytes(order)))

    def test_host_protocol(self):
        p=jme.Pedal.__new__(jme.Pedal)
        p._io=threading.Lock()
        p.request=Mock(return_value=jme.sysex(13,2,bytes(EXAMPLE)))
        p.set_chain(EXAMPLE)
        self.assertEqual(p.request.call_args.args[0],jme.sysex(13,1,bytes(EXAMPLE)))
        self.assertEqual(p.read_chain(),EXAMPLE)
        p.request.return_value=jme.sysex(13,2,bytes(jme.DEFAULT_CHAIN))
        with self.assertRaises(RuntimeError): p.set_chain(EXAMPLE)
        p.request.reset_mock()
        with self.assertRaises(ValueError): p.set_chain([0]*8)
        p.request.assert_not_called()

    def test_editor_save_and_readback(self):
        a=test_fx_editor.EditorTests().app()
        a.pedal.rec[67:70]=bytes([0x56,0x58,0x5f])
        def set_chain(order): a.pedal.rec[70:78]=bytes(order)
        a.pedal.set_chain=set_chain
        a.chain(EXAMPLE)
        self.assertTrue(a.s['dirty'])
        self.assertEqual(bytes.fromhex(a.s['edit'])[70:78],bytes(EXAMPLE))
        a.save(11,'Reordered')
        self.assertEqual(a.pedal.saved[1][67:78],bytes([0x56,0x58,0x5f])+bytes(EXAMPLE))
        a.pedal.set_chain=lambda order: None
        with self.assertRaises(RuntimeError): a.chain(list(jme.DEFAULT_CHAIN))

if __name__=='__main__': unittest.main(verbosity=2)
