"""External oracle and C differential tests for first-turn partial map witness v5."""

import ctypes
from itertools import combinations
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

from finite_witness_jitter import HYPOTHESES, generate_jitter_trial


HERE = Path(__file__).parent


class ReferenceMap(ctypes.Structure):
    _fields_ = [("columns", ctypes.c_uint16 * 64),
                ("seen", ctypes.c_uint8 * 8),
                ("quarantined", ctypes.c_uint8 * 8),
                ("count", ctypes.c_uint8), ("frozen", ctypes.c_uint8)]


class Plan(ctypes.Structure):
    _fields_ = [("step_mask", ctypes.c_uint32),
                ("pair_checks", ctypes.c_uint16),
                ("cost", ctypes.c_uint8),
                ("first_step", ctypes.c_uint8),
                ("status", ctypes.c_uint8)]


def external_exhaustive_plan(reference, observed, hypotheses, steps,
                             noise, jitter):
    """Brute-force over all 2^n subsets; unlike the C DP, no dynamic program."""
    pairs = list(combinations(hypotheses, 2))
    if not pairs:
        return (), 0
    coverage = {}
    work = 0
    for step in steps:
        covered = set()
        for pair in pairs:
            disjoint = True
            for a in range(-jitter, jitter + 1):
                for b in range(-jitter, jitter + 1):
                    ia, ib = (pair[0] + step + a) % 64, (pair[1] + step + b) % 64
                    if ia not in observed or ib not in observed:
                        disjoint = False
                    else:
                        work += 1
                        if (reference[ia] ^ reference[ib]).bit_count() <= 2 * noise:
                            disjoint = False
            if disjoint:
                covered.add(pair)
        coverage[step] = covered
    good = []
    for count in range(1, len(steps) + 1):
        for subset in combinations(steps, count):
            if set.union(set(), *(coverage[s] for s in subset)) == set(pairs):
                good.append(subset)
        if good:
            break
    return (min(good, key=lambda subset: (len(subset), subset[-1], subset))
            if good else None), work


def external_potential_step(reference, known, support, steps, noise, jitter):
    """Directed existential discrimination, independently written in Python."""
    def separable(a,b,s):
        return any(
            (a+s+da)%64 in known and all(
                (b+s+db)%64 in known and
                (reference[(a+s+da)%64]^reference[(b+s+db)%64]).bit_count()
                    > 2*noise
                for db in range(-jitter,jitter+1))
            for da in range(-jitter,jitter+1))
    scores={step:sum(separable(a,b,step) for a in support for b in support
                     if a!=b) for step in steps}
    maximum=max(scores.values())
    return min(s for s,v in scores.items() if v==maximum) if maximum>0 else None


class PartialMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="mathgraph-partial-map-")
        library_path = Path(cls.temp.name) / "libpartial.so"
        subprocess.run(["gcc", "-std=c99", "-Wall", "-Wextra", "-Werror",
                        "-O2", "-shared", "-fPIC", str(HERE / "finite_partial_map.c"),
                        str(HERE / "finite_jitter_embedded.c"),
                        "-o", str(library_path)], check=True,
                       capture_output=True, text=True)
        cls.lib = ctypes.CDLL(str(library_path))
        cls.lib.mg_map_init.argtypes = [ctypes.POINTER(ReferenceMap)]
        cls.lib.mg_map_capture.argtypes = [ctypes.POINTER(ReferenceMap),
                                           ctypes.c_uint8, ctypes.c_uint16]
        cls.lib.mg_map_capture.restype = ctypes.c_int
        cls.lib.mg_map_freeze.argtypes = [ctypes.POINTER(ReferenceMap)]
        cls.lib.mg_map_freeze.restype = ctypes.c_int
        cls.lib.mg_map_has.argtypes = [ctypes.POINTER(ReferenceMap), ctypes.c_uint8]
        cls.lib.mg_map_has.restype = ctypes.c_uint8
        cls.lib.mg_sparse_plan.argtypes = [ctypes.POINTER(ReferenceMap),
            ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8,
            ctypes.c_uint8, ctypes.c_uint8, ctypes.POINTER(Plan)]
        cls.lib.mg_sparse_plan.restype = ctypes.c_int
        cls.lib.mg_sparse_next_probe.argtypes = [ctypes.POINTER(ReferenceMap),
            ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8,
            ctypes.c_uint8, ctypes.c_uint8, ctypes.POINTER(Plan)]
        cls.lib.mg_sparse_next_probe.restype = ctypes.c_int
        cls.lib.mg_sparse_filter.argtypes = [ctypes.POINTER(ReferenceMap),
            ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint16,
            ctypes.c_uint8, ctypes.c_uint8]
        cls.lib.mg_sparse_filter.restype = ctypes.c_uint8
        cls.lib.mg_plan.argtypes = [ctypes.POINTER(ctypes.c_uint16),
            ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8,
            ctypes.c_uint8, ctypes.c_uint8, ctypes.POINTER(Plan)]
        cls.lib.mg_plan.restype = ctypes.c_int

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def build_map(self, reference, observed=range(64)):
        result = ReferenceMap()
        self.lib.mg_map_init(ctypes.byref(result))
        for index in observed:
            self.assertEqual(self.lib.mg_map_capture(ctypes.byref(result),
                                                      index, reference[index]), 0)
        self.assertEqual(self.lib.mg_map_freeze(ctypes.byref(result)), 0)
        return result

    def plan(self, reference_map, mask=15, start=1, end=32, noise=2, jitter=1):
        result = Plan()
        self.assertEqual(self.lib.mg_sparse_plan(ctypes.byref(reference_map),
                         mask, start, end, noise, jitter, ctypes.byref(result)),0)
        return result

    def next_probe(self, reference_map, mask=15, start=1, end=32,
                   noise=2, jitter=1):
        result=Plan()
        self.assertEqual(self.lib.mg_sparse_next_probe(ctypes.byref(reference_map),
                         mask,start,end,noise,jitter,ctypes.byref(result)),0)
        return result

    def test_first_turn_is_a_frozen_map_with_explicit_coverage_and_conflicts(self):
        self.assertEqual(ctypes.sizeof(ReferenceMap), 146)
        result = ReferenceMap()
        self.lib.mg_map_init(ctypes.byref(result))
        self.assertEqual(self.lib.mg_map_capture(ctypes.byref(result),7,0x1234),0)
        self.assertEqual(self.lib.mg_map_capture(ctypes.byref(result),7,0x1235),1)
        self.assertEqual(result.count,1)
        self.assertEqual(self.lib.mg_map_has(ctypes.byref(result),7),1)
        self.assertEqual(self.lib.mg_map_capture(ctypes.byref(result),7,0x0000),-2)
        self.assertEqual(self.lib.mg_map_has(ctypes.byref(result),7),0)
        self.assertEqual(result.count,0)
        self.assertEqual(self.lib.mg_map_capture(ctypes.byref(result),7,0x1234),-2)
        self.assertEqual(self.lib.mg_map_capture(ctypes.byref(result),64,0),-1)
        self.assertEqual(self.lib.mg_map_freeze(ctypes.byref(result)),0)
        self.assertEqual(self.lib.mg_map_capture(ctypes.byref(result),8,0),-1)
        self.assertEqual(self.lib.mg_map_freeze(ctypes.byref(result)),1)

    def test_full_map_matches_frozen_v4_exactly(self):
        for seed in (5,11,19,23):
            trial=generate_jitter_trial(seed,0,"wide")
            record=self.build_map(trial.reference)
            self.assertEqual(record.count,64)
            compiled=self.plan(record)
            original=Plan()
            self.assertEqual(self.lib.mg_plan(record.columns,15,1,32,2,1,
                                              ctypes.byref(original)),0)
            self.assertEqual((compiled.status,compiled.step_mask,compiled.cost,
                              compiled.first_step,compiled.pair_checks),
                             (original.status,original.step_mask,original.cost,
                              original.first_step,original.pair_checks))

    def test_missing_first_turn_landmark_blocks_unsupported_heading(self):
        trial=generate_jitter_trial(5,0,"wide")
        all_known=self.build_map(trial.reference)
        missing_cue=self.build_map(trial.reference,
                                   [i for i in range(64) if i%16 not in (6,7,8)])
        self.assertEqual(self.plan(all_known).status,1)
        unavailable=self.plan(missing_cue)
        self.assertEqual(unavailable.status,3)
        self.assertEqual(unavailable.cost,0)
        self.assertEqual(missing_cue.count,52)
        # A missing ±1 map cell must not allow a hypothesis to be eliminated.
        retained=self.lib.mg_sparse_filter(ctypes.byref(missing_cue),15,7,0,2,1)
        self.assertNotEqual(retained & 1,0)

    def test_opportunistic_probe_does_not_claim_a_guarantee(self):
        trial=generate_jitter_trial(5,0,"wide")
        full=self.build_map(trial.reference)
        self.assertEqual(self.next_probe(full).status,1)
        incomplete=self.build_map(trial.reference,
            [i for i in range(64) if i%16 not in (6,7,8)])
        self.assertEqual(self.plan(incomplete).status,3)
        probe=self.next_probe(incomplete)
        self.assertEqual(probe.status,5)
        self.assertEqual(probe.cost,1)
        self.assertGreaterEqual(probe.first_step,1)
        self.assertEqual(probe.step_mask,1<<(probe.first_step-1))
        symmetric=self.build_map(generate_jitter_trial(5,0,"unbreakable").reference)
        self.assertEqual(self.next_probe(symmetric).status,3)

    def test_active_partial_map_preserves_true_heading_after_every_probe(self):
        total_authorized=0
        for seed in (5,11,19,23):
            for heading in HYPOTHESES:
                trial=generate_jitter_trial(seed,heading,"wide")
                rng=random.Random(99173*seed+heading*217+len("random_12"))
                missing=set(rng.sample(range(64),12))
                record=self.build_map(trial.reference,
                    [i for i in range(64) if i not in missing])
                support=15
                next_step=1
                while next_step<=32:
                    proposal=self.next_probe(record,support,next_step)
                    if proposal.status not in (1,5): break
                    step=int(proposal.first_step)
                    self.assertGreaterEqual(step,next_step)
                    support=self.lib.mg_sparse_filter(ctypes.byref(record),
                                  support,step,trial.columns[step],2,1)
                    self.assertTrue(support & (1<<(heading//16)))
                    if support.bit_count()==1:
                        total_authorized+=1
                        break
                    next_step=step+1
        self.assertGreater(total_authorized,0)

    def test_opportunistic_step_selection_matches_independent_directed_oracle(self):
        rng=random.Random(88817)
        supports=((0,16,32,48),(0,16),(0,32,48))
        for case in range(120):
            ref=tuple(rng.getrandbits(16) for _ in range(64))
            chance=(1.0,0.84,0.63)[case%3]
            known={i for i in range(64) if rng.random()<chance}
            record=self.build_map(ref, sorted(known))
            support=supports[case%len(supports)]
            mask=sum(1<<(h//16) for h in support)
            noise=case%3
            jitter=case%2
            guaranteed=self.plan(record,mask,1,14,noise,jitter)
            next_choice=self.next_probe(record,mask,1,14,noise,jitter)
            if guaranteed.status==1:
                self.assertEqual(next_choice.status,1)
                self.assertEqual(next_choice.step_mask,guaranteed.step_mask)
            else:
                expected=external_potential_step(ref,known,support,
                                                 tuple(range(1,15)),noise,jitter)
                if expected is None:
                    self.assertEqual(next_choice.status,3)
                else:
                    self.assertEqual(next_choice.status,5)
                    self.assertEqual(next_choice.first_step,expected)

    def test_sparse_planner_agrees_with_independent_exhaustive_subset_solver(self):
        rng = random.Random(8883)
        supports = ((0,16,32,48),(0,16),(0,32,48))
        for case in range(100):
            reference=tuple(rng.getrandbits(16) for _ in range(64))
            coverage=(1.0,0.95,0.68)[case%3]
            observed={idx for idx in range(64) if rng.random()<coverage}
            record=self.build_map(reference,sorted(observed))
            support=supports[case%len(supports)]
            mask=sum(1 << (x//16) for x in support)
            jitter=case%2
            noise=1+case%2
            c=self.plan(record,mask,1,12,noise,jitter)
            exact,work=external_exhaustive_plan(reference,observed,support,
                                               tuple(range(1,13)),noise,jitter)
            self.assertEqual(c.pair_checks,work)
            if exact is None:
                self.assertEqual(c.status,3)
            else:
                self.assertEqual(c.status,1)
                self.assertEqual(c.cost,len(exact))
                self.assertEqual(c.first_step,exact[0])
                self.assertEqual(c.step_mask,sum(1 << (s-1) for s in exact))

    def test_missing_map_offsets_cannot_create_false_rejection(self):
        rng=random.Random(731)
        for seed in (5,11,19,23):
            trial=generate_jitter_trial(seed,0,"wide")
            observed={i for i in range(64) if rng.random()<0.60}
            record=self.build_map(trial.reference,sorted(observed))
            for heading in HYPOTHESES:
                for step in range(1,33):
                    for slip in (-1,0,1):
                        source=trial.physical_source[(heading+step+slip)%64]
                        measured=source ^ (1<<rng.randrange(16))
                        survivors=self.lib.mg_sparse_filter(ctypes.byref(record),
                                                             15,step,measured,2,1)
                        self.assertTrue(survivors & (1<<(heading//16)))

    def test_filter_matches_independent_conservative_missingness_semantics(self):
        rng=random.Random(46129)
        for case in range(150):
            reference=tuple(rng.getrandbits(16) for _ in range(64))
            known={i for i in range(64) if rng.random()<0.78}
            record=self.build_map(reference,sorted(known))
            step=rng.randrange(1,33)
            observation=rng.getrandbits(16)
            noise=case%3
            jitter=case%2
            measured=self.lib.mg_sparse_filter(ctypes.byref(record),15,
                                                step,observation,noise,jitter)
            expected=0
            for hypothesis in range(4):
                possible=False
                for delta in range(-jitter,jitter+1):
                    index=(hypothesis*16+step+delta)%64
                    if (index not in known or
                        (observation ^ reference[index]).bit_count()<=noise):
                        possible=True
                if possible: expected|=1<<hypothesis
            self.assertEqual(measured,expected)


if __name__=="__main__":
    unittest.main()
