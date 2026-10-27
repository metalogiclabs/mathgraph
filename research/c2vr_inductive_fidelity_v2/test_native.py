import json
import os
from pathlib import Path
import tempfile
import unittest

from checker import native_verdict
from native import run_verus


SOURCE = os.environ.get('C2VR_SOURCE_ROOT')


@unittest.skipUnless(SOURCE and Path(SOURCE).is_dir(), 'pinned upstream checkout unavailable')
class NativeEvidenceTests(unittest.TestCase):
    def test_real_executable_without_verus_proof_is_not_native_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            record = run_verus(Path(SOURCE), Path('/usr/bin/true'), folder)
            self.assertEqual(record['exit'], 0)
            self.assertEqual(record['tool_sha256'], __import__('hashlib').sha256(Path('/usr/bin/true').read_bytes()).hexdigest())
            self.assertEqual(json.loads((folder / 'native-receipt.json').read_text())['log_sha256'], record['log_sha256'])
            self.assertEqual(native_verdict(folder, Path('/usr/bin/true')), 'UNKNOWN_NO_VERUS_SUCCESS_MARKER')


if __name__ == '__main__':
    unittest.main()
