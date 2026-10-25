"""Independent native C99 versus MathGraph Python finite-witness qualification."""
import ctypes as C
import pathlib
import random
import subprocess
import tempfile
import unittest

from finite_witness_compass import (
    HYPOTHESES, NOISE_BUDGET, compile_minimum_witnesses,
    filter_hypotheses, generate_finite_trial,
)
from physical_active_acquisition import active_policy
from audit_physical_active_acquisition import exact_minimum_basis_size

MAP_BINS = 64
OK = 1
OBSTRUCTED = 2
ALREADY_UNIQUE = 3

class Plan(C.Structure):
    _fields_ = [("status", C.c_uint8),
                ("next_step", C.c_uint8),
                ("minimum_total_reads", C.c_uint8),
                ("candidate_pairs", C.c_uint8),
                ("selected_steps_bits", C.c_uint32)]

class EmbeddedWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        folder = pathlib.Path(__file__).parent
        output = pathlib.Path(cls.temp.name) / "witness.so"
        subprocess.run(
            ["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-pedantic",
             "-O2", "-fPIC", "-shared", str(folder / "finite_witness_embedded.c"),
             "-o", str(output)],
            check=True, capture_output=True, text=True)
        cls.lib = C.CDLL(str(output))
        cls.lib.mgw_plan.argtypes = [
            C.POINTER(C.c_uint16), C.POINTER(C.c_uint8),
            C.POINTER(C.c_uint8), C.c_uint8, C.c_uint8,
            C.c_uint8, C.c_uint8, C.POINTER(Plan)]
        cls.lib.mgw_plan.restype = C.c_int
        cls.lib.mgw_filter.argtypes = [
            C.POINTER(C.c_uint16), C.POINTER(C.c_uint8),
            C.POINTER(C.c_uint8), C.c_uint8, C.c_uint8,
            C.c_uint16, C.c_uint8, C.POINTER(C.c_uint8),
            C.POINTER(C.c_uint8)]
        cls.lib.mgw_filter.restype = C.c_int

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def arrays(self, reference, hypotheses, *, missing=()):
        sig = (C.c_uint16 * 64)(*reference)
        present = (C.c_uint8 * 64)(*[0 if i in missing else 1 for i in range(64)])
        h = (C.c_uint8 * 4)(*(tuple(hypotheses) + (0,) * (4-len(hypotheses))))
        return sig, present, h

    def plan(self, reference, hypotheses=HYPOTHESES, first=1, horizon=32, missing=()):
        sig, present, h = self.arrays(reference, hypotheses, missing=missing)
        p = Plan()
        rc = self.lib.mgw_plan(sig, present, h, len(hypotheses),
                               first, horizon, NOISE_BUDGET, C.byref(p))
        self.assertEqual(rc, 0)
        steps = tuple(i for i in range(1, 33)
                      if p.selected_steps_bits & (1 << (i-1)))
        return p, steps

    def filter(self, reference, hypotheses, step, observed, *, missing=()):
        sig, present, h = self.arrays(reference, hypotheses, missing=missing)
        out = (C.c_uint8 * 4)()
        n = C.c_uint8(0)
        rc = self.lib.mgw_filter(sig, present, h, len(hypotheses),
                                 step, observed, NOISE_BUDGET, out, C.byref(n))
        self.assertEqual(rc, 0)
        return tuple(out[:n.value])

    def test_fixed_embedded_interface_is_bounded(self):
        self.assertEqual(C.sizeof(Plan), 8)
        self.assertEqual(MAP_BINS, 64)

    def test_exact_minimum_witness_matches_frozen_python_dp(self):
        for seed in range(64):
            t = generate_finite_trial(seed, true_bin=0, kind="breakable")
            native, steps = self.plan(t.reference)
            python = compile_minimum_witnesses(
                t.reference, HYPOTHESES, tuple(range(1, 33)), NOISE_BUDGET)
            self.assertEqual(native.status, OK)
            self.assertEqual(steps, python.steps)
            self.assertEqual(native.minimum_total_reads, python.cost)
            self.assertEqual(native.minimum_total_reads,
                exact_minimum_basis_size(t.reference, list(HYPOTHESES), 1, 32, 2))
            self.assertEqual(native.next_step, python.steps[0])

    def test_all_four_headings_and_missing_first_witness_replan(self):
        for seed in range(12):
            for true in HYPOTHESES:
                for absent in ((), (7,), (13,), (7, 13), (7, 13, 23, 29)):
                    t = generate_finite_trial(seed, true_bin=true,
                                              kind="breakable", occluded_steps=absent)
                    target = active_policy(t.reference, HYPOTHESES, 32,
                                           lambda step: t.columns[step])
                    remaining = HYPOTHESES
                    cursor = 1
                    requests = []
                    status = None
                    while len(remaining) > 1 and cursor <= 32:
                        native, planned = self.plan(t.reference, remaining, cursor)
                        if native.status != OK:
                            self.assertEqual(native.status, OBSTRUCTED)
                            status = "UNKNOWN_OBSTRUCTION"
                            break
                        step = native.next_step
                        requests.append(step)
                        if t.columns[step] is not None:
                            remaining = self.filter(t.reference, remaining, step,
                                                    t.columns[step])
                        if not remaining:
                            status = "CONFLICT"
                            break
                        cursor = step+1
                    if len(remaining) == 1:
                        status = "MODEL_UNIQUE"
                    self.assertEqual(status, target["status"])
                    self.assertEqual(tuple(remaining), tuple(target["candidates"]))
                    self.assertEqual(requests, [x["step"] for x in target["requests"]])
                    if status == "MODEL_UNIQUE":
                        self.assertEqual(remaining[0], true)

    def test_indistinguishable_map_produces_bounded_obstruction(self):
        for seed in range(24):
            t = generate_finite_trial(seed, true_bin=0, kind="unbreakable")
            native, steps = self.plan(t.reference)
            self.assertEqual(native.status, OBSTRUCTED)
            self.assertEqual(steps, ())
            self.assertEqual(native.next_step, 0)

    def test_observation_filter_matches_legacy_python_for_all_seeds(self):
        for seed in range(32):
            for true in HYPOTHESES:
                t = generate_finite_trial(seed, true_bin=true, kind="breakable")
                for step in (1, 7, 13, 23, 29):
                    self.assertEqual(
                        self.filter(t.reference, HYPOTHESES, step, t.columns[step]),
                        filter_hypotheses(t.reference, HYPOTHESES, step,
                                          t.columns[step], NOISE_BUDGET))

    def test_prior_singleton_is_not_a_camera_warrant(self):
        t = generate_finite_trial(4, true_bin=0, kind="breakable")
        native, steps = self.plan(t.reference, (0,))
        self.assertEqual(native.status, ALREADY_UNIQUE)
        self.assertEqual(native.next_step, 0)
        self.assertEqual(native.minimum_total_reads, 0)
        self.assertEqual(steps, ())
        # No acquired column or independently validated gyro prior:
        # singleton status cannot become a consequential heading correction.

    def test_holes_do_not_become_negative_evidence(self):
        t = generate_finite_trial(1, true_bin=0, kind="breakable")
        missing = (7, 23)
        result = self.filter(t.reference, HYPOTHESES, 7, 65535, missing=missing)
        # h=0 points to absent bin7; h=16 points to absent bin23.
        self.assertIn(0, result)
        self.assertIn(16, result)
        native, steps = self.plan(t.reference, missing=missing)
        self.assertIn(native.status, (OK, OBSTRUCTED))
        if native.status == OK:
            self.assertTrue(all(1 <= s <= 32 for s in steps))

    def test_invalid_inputs_rejected(self):
        t = generate_finite_trial(1, true_bin=0, kind="breakable")
        sig, present, h = self.arrays(t.reference, (0, 16))
        p = Plan()
        self.assertEqual(self.lib.mgw_plan(sig, present, h, 2, 1, 33, 2,
                                           C.byref(p)), -1)
        self.assertEqual(self.lib.mgw_plan(sig, present, h, 2, 0, 32, 2,
                                           C.byref(p)), -1)
        self.assertEqual(self.lib.mgw_plan(sig, present, h, 2, 1, 32, 3,
                                           C.byref(p)), -1)
        bad = (C.c_uint8 * 4)(0, 0, 32, 48)
        self.assertEqual(self.lib.mgw_plan(sig, present, bad, 4, 1, 32, 2,
                                           C.byref(p)), -1)

    def test_random_maps_match_frozen_exact_python_compiler(self):
        rng = random.Random(268011)
        for _ in range(100):
            ref = tuple(rng.randrange(0, 65536) for __ in range(64))
            native, steps = self.plan(ref, horizon=16)
            python = compile_minimum_witnesses(
                ref, HYPOTHESES, tuple(range(1, 17)), NOISE_BUDGET)
            if python.status == "SEPARATING_SET":
                self.assertEqual(native.status, OK)
                self.assertEqual(steps, python.steps)
                self.assertEqual(native.minimum_total_reads, python.cost)
            else:
                self.assertEqual(native.status, OBSTRUCTED)

if __name__ == "__main__":
    unittest.main()
