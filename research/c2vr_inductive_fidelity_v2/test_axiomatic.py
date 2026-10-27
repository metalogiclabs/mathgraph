import os
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from axiomatic_control import check_axiomatic
from baseline import compare_axiomatic
from native import run_verus


ORIGINAL = os.environ.get('C2VR_SOURCE_ROOT')
FILES = ('data/tutorial_wp/max_subarray-1.c', 'RQ3_result/Full_Fixed/max_subarray-1.rs')


@unittest.skipUnless(ORIGINAL and Path(ORIGINAL).is_dir(), 'pinned C2VR checkout unavailable')
class AxiomaticSourceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for rel in FILES:
            dest = self.root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(ORIGINAL) / rel, dest)

    def test_authentic_axiomatic_trust_kind_is_matched_not_full_equivalence(self):
        result = check_axiomatic(self.root)
        self.assertEqual(result['trust_kind_verdict'], 'MATCHED_AXIOMATIC_TRUST_KIND_BOUNDED')
        self.assertEqual(result['native_verdict'], 'UNKNOWN_NOT_EXECUTED')
        self.assertFalse(result['full_specification_equivalence_warranted'])

    def test_equally_informed_conventional_reviewer_sees_original_axiomatic_contract(self):
        result = compare_axiomatic(self.root)
        self.assertEqual(result['verdict'], 'BASELINE_TIE')
        self.assertEqual(result['source_kind'], 'AXIOMATIC')

    def test_changed_source_withdraws(self):
        f = self.root / FILES[0]
        f.write_bytes(f.read_bytes() + b'\n')
        self.assertEqual(check_axiomatic(self.root)['trust_kind_verdict'], 'WITHDRAWN_CHANGED_AXIOMATIC_C')

    def test_changed_target_withdraws(self):
        f = self.root / FILES[1]
        f.write_bytes(f.read_bytes() + b'\n')
        self.assertEqual(check_axiomatic(self.root)['trust_kind_verdict'], 'WITHDRAWN_CHANGED_AXIOMATIC_VERUS')

    def test_missing_source_withdraws(self):
        (self.root / FILES[0]).unlink()
        self.assertEqual(check_axiomatic(self.root)['trust_kind_verdict'], 'WITHDRAWN_MISSING_AXIOMATIC_CASE')

    def test_missing_native_evidence_is_not_green(self):
        evidence = self.root / 'evidence'
        evidence.mkdir()
        self.assertEqual(check_axiomatic(self.root, evidence)['native_verdict'], 'WITHDRAWN_NATIVE_RECEIPT')

    def test_named_native_receipt_is_bound_to_axiomatic_pair(self):
        evidence = self.root / 'axiomatic-evidence'
        receipt = run_verus(self.root, Path('/usr/bin/true'), evidence, case='max_subarray')
        self.assertEqual(receipt['source_sha256'], 'ff66b503c6074877c5a764e521d7fbfa15901abfe6e1a70d71d7176a9e4a7e63')
        self.assertEqual(receipt['target_sha256'], '0f62e42e58ba8a0c1c95c4825cad3859123436fd0f99466a5d1eabb45eeec468')
        self.assertEqual(check_axiomatic(self.root, evidence, Path('/usr/bin/true'))['native_verdict'], 'UNKNOWN_NO_VERUS_SUCCESS_MARKER')

    def test_forged_axiomatic_target_receipt_is_rejected(self):
        evidence = self.root / 'axiomatic-evidence'
        run_verus(self.root, Path('/usr/bin/true'), evidence, case='max_subarray')
        receipt_file = evidence / 'native-receipt.json'
        receipt = json.loads(receipt_file.read_text())
        receipt['target_sha256'] = '0' * 64
        receipt_file.write_text(json.dumps(receipt))
        self.assertEqual(check_axiomatic(self.root, evidence, Path('/usr/bin/true'))['native_verdict'], 'REJECTED_EVIDENCE')


if __name__ == '__main__':
    unittest.main()
