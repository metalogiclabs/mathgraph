"""Compiled C99/ctypes differential audit of finite jitter-aware compass core."""

import ctypes
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

from finite_witness_jitter import (
    HYPOTHESES, compile_jitter_witnesses, filter_jitter_hypotheses,
    generate_jitter_trial, run_jitter_acquired,
)


PATH = Path(__file__).parent


class Plan(ctypes.Structure):
    _fields_ = [("step_mask", ctypes.c_uint32),
                ("pair_checks", ctypes.c_uint16),
                ("cost", ctypes.c_uint8),
                ("first_step", ctypes.c_uint8),
                ("status", ctypes.c_uint8)]


class EmbeddedC99Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(prefix="mathgraph-jitter-core-")
        target = Path(cls.folder.name) / "libfinite_jitter.so"
        command = ["gcc", "-std=c99", "-Wall", "-Wextra", "-Werror",
                   "-O2", "-fPIC", "-shared", "-o", str(target),
                   str(PATH / "finite_jitter_embedded.c")]
        subprocess.run(command, check=True, capture_output=True, text=True)
        cls.lib = ctypes.CDLL(str(target))
        cls.lib.mg_plan.argtypes = [ctypes.POINTER(ctypes.c_uint16),
            ctypes.c_uint8,ctypes.c_uint8,ctypes.c_uint8,
            ctypes.c_uint8,ctypes.c_uint8,ctypes.POINTER(Plan)]
        cls.lib.mg_plan.restype = ctypes.c_int
        cls.lib.mg_filter.argtypes = [ctypes.POINTER(ctypes.c_uint16),
            ctypes.c_uint8,ctypes.c_uint8,ctypes.c_uint16,
            ctypes.c_uint8,ctypes.c_uint8]
        cls.lib.mg_filter.restype = ctypes.c_uint8
        cls.lib.mg_reference_bytes.restype = ctypes.c_uint16

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    @staticmethod
    def buffer(reference):
        return (ctypes.c_uint16 * 64)(*reference)

    def plan_from_c(self, reference, hypotheses, start=1, end=32, error=2, jitter=1):
        bits = sum(1 << (h//16) for h in hypotheses)
        result = Plan()
        status = self.lib.mg_plan(self.buffer(reference),bits,start,end,
                                  error,jitter,ctypes.byref(result))
        self.assertEqual(status,0)
        return result

    def test_agrees_with_frozen_jitter_python_for_all_64_development_cases(self):
        for seed in (5,11,19,23):
            for actual in HYPOTHESES:
                for kind,missing in (("wide",()),("wide",(7,)),
                                     ("narrow",()),("unbreakable",())):
                    trial=generate_jitter_trial(seed,actual,kind,missing)
                    expected=run_jitter_acquired(trial.reference,HYPOTHESES,trial.columns)
                    reference=self.buffer(trial.reference)
                    mask=15
                    step=1
                    checked=0
                    attempts=[]
                    acquired=[]
                    while step<len(trial.columns):
                        compiled=Plan()
                        self.assertEqual(self.lib.mg_plan(reference,mask,step,
                            len(trial.columns)-1,2,1,ctypes.byref(compiled)),0)
                        checked+=compiled.pair_checks
                        if compiled.status!=1:
                            status="UNKNOWN_OBSTRUCTION"
                            break
                        t=compiled.first_step
                        attempts.append(t)
                        if trial.columns[t] is not None:
                            acquired.append(t)
                            mask=self.lib.mg_filter(reference,mask,t,trial.columns[t],2,1)
                            if mask==0:
                                status="CONFLICT"
                                break
                            if mask.bit_count()==1:
                                status="AUTHORIZED"
                                break
                        step=t+1
                    else:
                        status="UNKNOWN_OBSTRUCTION"
                    self.assertEqual(status,expected.status)
                    self.assertEqual(tuple(attempts),expected.attempted_steps)
                    self.assertEqual(tuple(acquired),expected.acquired_steps)
                    self.assertEqual(checked,expected.pair_checks)
                    if status=="AUTHORIZED":
                        self.assertEqual((mask.bit_length()-1)*16,expected.accepted_bin)

    def test_random_reference_maps_match_python_across_supports_and_bounds(self):
        rng = random.Random(7019)
        supports=((0,16,32,48),(0,16),(0,32,48),(0,))
        for _ in range(120):
            ref=tuple(rng.getrandbits(16) for _ in range(64))
            for support in supports:
                for jitter in (0,1):
                    for error in (1,2):
                        c=self.plan_from_c(ref,support,1,16,error,jitter)
                        py=compile_jitter_witnesses(ref,support,
                                                     tuple(range(1,17)),error,jitter)
                        c_status={1:"SEPARATING_SET",2:"ALREADY_UNIQUE",
                                  3:"BOUNDED_NO_GUARANTEED_SEPARATION",4:"NO_CANDIDATES"}[c.status]
                        self.assertEqual(c_status,py.status)
                        self.assertEqual(c.cost,py.cost)
                        self.assertEqual(c.pair_checks,py.pair_checks)
                        if py.status=="SEPARATING_SET":
                            self.assertEqual(c.step_mask,sum(1 << (s-1) for s in py.steps))
                            self.assertEqual(c.first_step,py.steps[0])
                        obs=rng.getrandbits(16)
                        mask=sum(1 << (h//16) for h in support)
                        filtered=self.lib.mg_filter(self.buffer(ref),mask,7,obs,error,jitter)
                        python_filtered=filter_jitter_hypotheses(ref,support,7,obs,error,jitter)
                        self.assertEqual(filtered,sum(1 << (h//16) for h in python_filtered))

    def test_static_map_exactly_128_bytes_and_bad_step_rejected(self):
        self.assertEqual(self.lib.mg_reference_bytes(),128)
        ref=self.buffer(generate_jitter_trial(5).reference)
        result=Plan()
        self.assertNotEqual(self.lib.mg_plan(ref,15,0,32,2,1,ctypes.byref(result)),0)
        self.assertEqual(result.status,0)

    def test_true_heading_survives_all_declared_one_bit_errors_and_slips(self):
        # Unlike differential tests, this checks a physical invariance against
        # the synthetic source, which the flight algorithm cannot inspect.
        for seed in (5,11,19,23):
            trial=generate_jitter_trial(seed,0,"wide")
            ref=self.buffer(trial.reference)
            for heading in HYPOTHESES:
                for step in range(1,33):
                    for slip in (-1,0,1):
                        source=trial.physical_source[(heading+step+slip)%64]
                        for flip in range(16):
                            measured=source ^ (1<<flip)
                            remaining=self.lib.mg_filter(ref,15,step,measured,2,1)
                            self.assertNotEqual(remaining & (1<<(heading//16)),0)

    def test_input_bounds_and_unbreakable_symmetry_fail_closed(self):
        reference=self.buffer(generate_jitter_trial(11,0,"unbreakable").reference)
        result=Plan()
        self.assertEqual(self.lib.mg_plan(reference,15,1,32,2,1,ctypes.byref(result)),0)
        self.assertEqual(result.status,3)
        self.assertEqual(result.step_mask,0)
        for support,first,last,error,jitter in ((16,1,32,2,1),
                                                  (15,1,33,2,1),
                                                  (15,2,1,2,1),
                                                  (15,1,32,17,1),
                                                  (15,1,32,2,4)):
            self.assertNotEqual(self.lib.mg_plan(reference,support,first,last,
                                 error,jitter,ctypes.byref(result)),0)
            self.assertEqual(result.status,0)


if __name__=="__main__":
    unittest.main()
