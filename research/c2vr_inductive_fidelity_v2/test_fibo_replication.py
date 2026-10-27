"""Replicate the semantic gap on a distinct source-authored inductive case."""

import os
from pathlib import Path
import shutil
import tempfile
import unittest

from fibo_replication import audit_fibo, check_fibo
from baseline import compare_fibo
from native import run_verus


ORIGINAL = os.environ.get('C2VR_SOURCE_ROOT')
FILES = ('data/tutorial_wp/ex-N-fibo.c', 'RQ3_result/Full_Fixed/ex-N-fibo.rs')


class FiboFiniteTests(unittest.TestCase):
    def test_negative_index_countermodel_preserves_monotonic_axiom(self):
        report = audit_fibo(5)
        self.assertEqual(report['verdict'], 'FINITE_COUNTERMODEL')
        self.assertEqual(report['separating_query'], [-1, 0])
        self.assertFalse(report['source_query'])
        self.assertTrue(report['target_compatible_query'])
        self.assertTrue(report['both_satisfy_introduction_and_monotonic_axioms_bounded'])

    def test_finite_bound_refuses_trivial(self):
        with self.assertRaises(ValueError):
            audit_fibo(1)


@unittest.skipUnless(ORIGINAL and Path(ORIGINAL).is_dir(), 'pinned C2VR checkout unavailable')
class FiboSourceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for rel in FILES:
            dest = self.root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(ORIGINAL) / rel, dest)

    def test_authentic_pinned_source_and_target_countermodel(self):
        report = check_fibo(self.root)
        self.assertEqual(report['semantic_verdict'], 'FINITE_COUNTERMODEL')
        self.assertEqual(report['native_verdict'], 'UNKNOWN_NOT_EXECUTED')
        self.assertTrue(report['source_admitted_monotonic_lemma_retained_as_assumption'])

    def test_source_aware_conventional_baseline_ties(self):
        self.assertEqual(compare_fibo(self.root)['verdict'], 'BASELINE_TIE')

    def test_source_mutation_withdraws(self):
        f = self.root / FILES[0]
        f.write_bytes(f.read_bytes() + b'\n')
        self.assertEqual(check_fibo(self.root)['semantic_verdict'], 'WITHDRAWN_CHANGED_FIBO_C')

    def test_target_mutation_withdraws(self):
        f = self.root / FILES[1]
        f.write_bytes(f.read_bytes() + b'\n')
        self.assertEqual(check_fibo(self.root)['semantic_verdict'], 'WITHDRAWN_CHANGED_FIBO_VERUS')

    def test_native_receipt_not_inferred_from_dummy_executable(self):
        evidence = self.root / 'evidence'
        run_verus(self.root, Path('/usr/bin/true'), evidence, case='fibo')
        self.assertEqual(check_fibo(self.root, evidence, Path('/usr/bin/true'))['native_verdict'], 'UNKNOWN_NO_VERUS_SUCCESS_MARKER')


if __name__ == '__main__':
    unittest.main()
