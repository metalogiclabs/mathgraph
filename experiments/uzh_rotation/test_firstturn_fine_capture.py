"""Independent exact 16-bit finite oracle for C99 high-resolution capture."""
import ctypes
from pathlib import Path
import subprocess
import tempfile
import unittest

from audit_finite_partial_map import Map

HERE=Path(__file__).parent
FINE_TURN=65536
FINE_PER_BIN=1024

class FineCaptureControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix="mathgraph-fine-interval-")
        so=Path(cls.tmp.name)/"libfineinterval.so"
        subprocess.run([
            "gcc","-std=c99","-Wall","-Wextra","-Werror","-O2",
            "-shared","-fPIC",
            str(HERE/"firstturn_fine_capture.c"),
            str(HERE/"firstturn_interval_capture.c"),
            str(HERE/"finite_partial_map.c"),
            str(HERE/"finite_jitter_embedded.c"),"-o",str(so)
        ],check=True,capture_output=True,text=True)
        cls.native=ctypes.CDLL(str(so))
        cls.native.mg_map_init.argtypes=[ctypes.POINTER(Map)]
        cls.native.mg_map_freeze.argtypes=[ctypes.POINTER(Map)]
        cls.native.mg_firstturn_capture_fine_interval.argtypes=[
            ctypes.POINTER(Map),ctypes.c_uint16,ctypes.c_uint16,ctypes.c_uint16]
        cls.native.mg_firstturn_capture_fine_interval.restype=ctypes.c_int

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def capture(self,phase,radius,column=0x1234):
        map=Map()
        self.native.mg_map_init(ctypes.byref(map))
        state=self.native.mg_firstturn_capture_fine_interval(
            ctypes.byref(map),phase,radius,column)
        return state,map

    def test_exhaustive_all_phases_multiple_radii_independent_subbin_oracle(self):
        radii=(0,1,2,3,8,32,128,256,511,512,1023)
        counts={}
        for r in radii:
            accepted=0
            for phase in range(FINE_TURN):
                # Distinct oracle: exact interval is a single bin iff the
                # within-bin offset >=radius and <=1023-radius.
                offset=phase%FINE_PER_BIN
                expected=(r<=511 and offset>=r and offset+r<FINE_PER_BIN)
                state,m=self.capture(phase,r)
                self.assertEqual(state,0 if expected else 2,(phase,r))
                if expected:
                    accepted+=1
                    self.assertEqual(m.count,1)
                    index=phase//FINE_PER_BIN
                    self.assertEqual(m.columns[index],0x1234)
                else:
                    self.assertEqual(m.count,0)
            counts[r]=accepted
        self.assertEqual(counts[0],65536)
        self.assertEqual(counts[511],128)
        self.assertEqual(counts[512],0)

    def test_independent_explicit_sample_shift_oracle_at_wrap(self):
        for phase in [0,1,1022,1023,1024,1025,65534,65535,8000,32000]:
            for radius in [0,1,2,16,256,511,512]:
                state,_=self.capture(phase,radius)
                possible={((phase+k)%FINE_TURN)//FINE_PER_BIN
                          for k in range(-radius,radius+1)}
                self.assertEqual(state,0 if len(possible)==1 else 2)

    def test_zero_error_on_bin_start_is_allowed(self):
        state,m=self.capture(1024,0)
        self.assertEqual(state,0)
        self.assertEqual(m.count,1)
        self.assertEqual(m.columns[1],0x1234)

    def test_frozen_reference_refuses_mutation(self):
        record=Map()
        self.native.mg_map_init(ctypes.byref(record))
        self.assertEqual(self.native.mg_map_freeze(ctypes.byref(record)),0)
        self.assertEqual(self.native.mg_firstturn_capture_fine_interval(
            ctypes.byref(record),512,1,0xABCD),-1)
        self.assertEqual(record.count,0)

    def test_false_source_error_bound_is_not_self_calibrating(self):
        # A physically shifted +1024-tick reading can still be admitted
        # when the caller lies about an error radius of only 2 ticks.
        state,m=self.capture(512,2)
        self.assertEqual(state,0)
        self.assertEqual(m.count,1)
        self.assertNotEqual(512//1024,(512+1024)//1024)

if __name__=="__main__":
    unittest.main()
