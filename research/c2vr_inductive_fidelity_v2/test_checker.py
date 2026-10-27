import os
from pathlib import Path
import shutil
import tempfile
import unittest

from baseline import compare
from checker import check
from native import run_verus


ORIGINAL = os.environ.get('C2VR_SOURCE_ROOT')
FILES = ('data/tutorial_wp/ex-2-gcd.c', 'RQ3_result/Full_Fixed/ex-2-gcd.rs')


@unittest.skipUnless(ORIGINAL and Path(ORIGINAL).is_dir(), 'pinned upstream checkout unavailable')
class AuthenticSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for relative in FILES:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(ORIGINAL) / relative, target)

    def test_source_finite_fidelity_countermodel_and_native_unknown(self):
        report = check(self.root)
        self.assertEqual(report['semantic_verdict'], 'FINITE_COUNTERMODEL')
        self.assertEqual(report['native_verdict'], 'UNKNOWN_NOT_EXECUTED')
        self.assertEqual(report['trust_boundary'], 'VERUS_EXTERNAL_BODY_ASSUMPTION')

    def test_source_rewrite_withdraws_claim(self):
        f = self.root / FILES[0]
        f.write_bytes(f.read_bytes() + b'\n')
        self.assertEqual(check(self.root)['semantic_verdict'], 'WITHDRAWN_CHANGED_C')

    def test_rust_rewrite_withdraws_claim(self):
        f = self.root / FILES[1]
        f.write_bytes(f.read_bytes() + b'\n')
        self.assertEqual(check(self.root)['semantic_verdict'], 'WITHDRAWN_CHANGED_VERUS')

    def test_missing_external_source_withdraws_claim(self):
        (self.root / FILES[0]).unlink()
        self.assertEqual(check(self.root)['semantic_verdict'], 'WITHDRAWN_MISSING_SOURCE')

    def test_source_aware_conventional_baseline_ties(self):
        report = compare(self.root)
        self.assertEqual(report['verdict'], 'BASELINE_TIE')
        self.assertEqual(report['query'], [2, 0, 1])

    def test_native_receipt_absence_is_not_silent_success(self):
        evidence = self.root / 'evidence'
        evidence.mkdir()
        self.assertEqual(check(self.root, evidence)['native_verdict'], 'WITHDRAWN_NATIVE_RECEIPT')

    def test_forged_native_log_is_rejected(self):
        evidence = self.root / 'evidence'
        run_verus(self.root, Path('/usr/bin/true'), evidence)
        original = (evidence / 'verus.log').read_text()
        (evidence / 'verus.log').write_text(original + 'forged proof marker\n')
        self.assertEqual(check(self.root, evidence, Path('/usr/bin/true'))['native_verdict'], 'REJECTED_EVIDENCE')

    def test_substituted_native_executable_is_rejected(self):
        evidence = self.root / 'evidence'
        run_verus(self.root, Path('/usr/bin/true'), evidence)
        self.assertEqual(check(self.root, evidence, Path('/usr/bin/false'))['native_verdict'], 'REJECTED_EVIDENCE')

    def test_valid_receipt_without_tool_bytes_remains_unknown(self):
        evidence = self.root / 'evidence'
        run_verus(self.root, Path('/usr/bin/true'), evidence)
        self.assertEqual(check(self.root, evidence)['native_verdict'], 'UNKNOWN_TOOL_BYTES')


if __name__ == '__main__':
    unittest.main()
