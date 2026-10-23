"""Independent finite C99 witness/obligation oracle, not sensor certification."""
import ctypes
from pathlib import Path
import subprocess
import tempfile
import unittest

from audit_finite_partial_map import Map

HERE=Path(__file__).parent
class Evidence(ctypes.Structure):
    _fields_=[
      ("reported_phase_65536",ctypes.c_uint16),
      ("externally_bounded_error_ticks",ctypes.c_uint16),
      ("clock_error_bound_authenticated_externally",ctypes.c_uint8),
      ("gyro_error_bound_authenticated_externally",ctypes.c_uint8),
      ("source_epoch_authenticated_externally",ctypes.c_uint8),
      ("within_first_revolution",ctypes.c_uint8),
    ]

SOURCE_EPOCH=22
CLOCK=20
GYRO=21
FIRST_TURN=23
AMBIGUOUS=24
ALREADY=25
QUARANTINED=26
ACQUIRE=27

class SourceObligationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix="mathgraph-source-obligation-")
        so=Path(cls.temp.name)/"libsource.so"
        subprocess.run(["gcc","-std=c99","-O2","-Wall","-Wextra",
                        "-Werror","-shared","-fPIC",
                        str(HERE/"firstturn_source_obligation.c"),
                        str(HERE/"firstturn_fine_capture.c"),
                        str(HERE/"firstturn_interval_capture.c"),
                        str(HERE/"finite_partial_map.c"),
                        str(HERE/"finite_jitter_embedded.c"),
                        "-o",str(so)],capture_output=True,text=True,check=True)
        cls.lib=ctypes.CDLL(str(so))
        cls.lib.mg_map_init.argtypes=[ctypes.POINTER(Map)]
        cls.lib.mg_map_capture.argtypes=[ctypes.POINTER(Map),ctypes.c_uint8,ctypes.c_uint16]
        cls.lib.mg_map_capture.restype=ctypes.c_int
        cls.lib.mg_map_freeze.argtypes=[ctypes.POINTER(Map)]
        cls.lib.mg_map_freeze.restype=ctypes.c_int
        cls.lib.mg_source_firstturn_obligation.argtypes=[
            ctypes.POINTER(Map),ctypes.POINTER(Evidence),ctypes.POINTER(ctypes.c_uint8)]
        cls.lib.mg_source_firstturn_obligation.restype=ctypes.c_int
        cls.lib.mg_source_capture_with_evidence.argtypes=[
            ctypes.POINTER(Map),ctypes.POINTER(Evidence),ctypes.c_uint16]
        cls.lib.mg_source_capture_with_evidence.restype=ctypes.c_int
    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()
    def fresh(self):
        m=Map()
        self.lib.mg_map_init(ctypes.byref(m))
        return m
    @staticmethod
    def ev(phase=512,radius=2,clock=1,gyro=1,epoch=1,turn=1):
        return Evidence(phase,radius,clock,gyro,epoch,turn)
    def req(self,map,evidence):
        binid=ctypes.c_uint8(0)
        code=self.lib.mg_source_firstturn_obligation(
            ctypes.byref(map),ctypes.byref(evidence),ctypes.byref(binid))
        return code,binid.value

    def test_source_warrant_must_be_present_before_any_column_request(self):
        m=self.fresh()
        conditions=[
            (self.ev(epoch=0),SOURCE_EPOCH),
            (self.ev(turn=0),FIRST_TURN),
            (self.ev(clock=0),CLOCK),
            (self.ev(gyro=0),GYRO),
            (self.ev(clock=2),CLOCK),
            (self.ev(epoch=255),SOURCE_EPOCH),
            (self.ev(radius=512),AMBIGUOUS),
            (self.ev(phase=1024,radius=1),AMBIGUOUS),
            (self.ev(phase=0,radius=1),AMBIGUOUS)
        ]
        for e,expected in conditions:
            status,index=self.req(m,e)
            self.assertEqual((status,index),(expected,255))
            self.assertEqual(m.count,0)
            self.assertEqual(self.lib.mg_source_capture_with_evidence(
                ctypes.byref(m),ctypes.byref(e),0x1111),expected)
            self.assertEqual(m.count,0)

    def test_acquisition_request_never_fabricates_or_mutates_column(self):
        m=self.fresh(); e=self.ev(512,1)
        code,index=self.req(m,e)
        self.assertEqual((code,index),(ACQUIRE,0))
        self.assertEqual(m.count,0)
        self.assertEqual(list(m.seen),[0]*8)
        self.assertEqual(self.lib.mg_source_capture_with_evidence(
            ctypes.byref(m),ctypes.byref(e),0xBA12),0)
        self.assertEqual(m.count,1)
        self.assertEqual(m.columns[0],0xBA12)
        self.assertEqual(self.req(m,e),(ALREADY,255))
        self.assertEqual(self.lib.mg_source_capture_with_evidence(
            ctypes.byref(m),ctypes.byref(e),0xBAD0),ALREADY)
        self.assertEqual(m.columns[0],0xBA12)

    def test_quarantined_bin_never_reopened_by_active_acquisition(self):
        m=self.fresh()
        self.assertEqual(self.lib.mg_map_capture(ctypes.byref(m),0,0),0)
        self.assertEqual(self.lib.mg_map_capture(ctypes.byref(m),0,0xFFFF),-2)
        self.assertEqual(self.req(m,self.ev()),(QUARANTINED,255))
        self.assertEqual(m.count,0)

    def test_firstturn_freeze_closes_source_evidence_requests(self):
        m=self.fresh()
        self.assertEqual(self.lib.mg_map_freeze(ctypes.byref(m)),0)
        self.assertEqual(self.req(m,self.ev()),(-1,255))
        self.assertEqual(self.lib.mg_source_capture_with_evidence(
            ctypes.byref(m),ctypes.byref(self.ev()),0xFA11),-1)
        self.assertEqual(m.count,0)

    def test_exhaustive_phase_acceptance_matches_independent_integer_oracle(self):
        m=self.fresh()
        count=0
        for radius in (0,1,7,127,511,512,1023):
            for phase in range(65536):
                e=self.ev(phase,radius)
                state,index=self.req(m,e)
                offset=phase%1024
                expected=(radius<=511 and
                          offset>=radius and offset+radius<1024)
                self.assertEqual(state,ACQUIRE if expected else AMBIGUOUS,
                                 (phase,radius))
                self.assertEqual(index,phase//1024 if expected else 255,
                                 (phase,radius))
                count+=1
        self.assertEqual(count,7*65536)
        self.assertEqual(m.count,0)

    def test_lying_external_warrant_still_can_corrupt_map(self):
        m=self.fresh()
        e=self.ev(512,0,1,1,1,1)
        self.assertEqual(self.lib.mg_source_capture_with_evidence(
            ctypes.byref(m),ctypes.byref(e),0xCAFE),0)
        self.assertEqual(m.count,1)
        # The finite check cannot discover a physical angle secretly 1 bin
        # away. Its source flags are a caller assertion, not a measured bound.
        physical_bin=(512+1024)//1024
        self.assertNotEqual(physical_bin,0)

    def test_zeroed_evidence_fails_closed(self):
        m=self.fresh()
        e=Evidence()
        self.assertEqual(self.req(m,e),(SOURCE_EPOCH,255))
        self.assertEqual(m.count,0)

if __name__=="__main__":
    unittest.main()
