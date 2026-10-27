"""Real-log negative controls, run after TLC evidence has been produced."""
from __future__ import annotations

import os
from pathlib import Path
import unittest

from challenge_native import challenge_all


class NativeEvidenceChallenges(unittest.TestCase):
    def test_real_native_evidence_fail_closed_matrix(self):
        source = os.environ.get("MATHGRAPH_TLA_SOURCE_DIR")
        cases = os.environ.get("MATHGRAPH_TLA_RESULT_DIR")
        if not source or not cases or not (Path(cases) / "author" / "tlc.log").is_file():
            self.skipTest("requires native source and actual completed TLC results")
        out = challenge_all(Path(source), Path(cases))
        self.assertEqual(len(out), 7)
        self.assertEqual(out["original"], "WARRANTED_BOUNDED_AUTHOR_MODEL")
        self.assertEqual(out["stale_source"], "WITHDRAWN")
        self.assertEqual(out["changed_jar"], "REJECTED_EVIDENCE")
        self.assertEqual(out["missing_author_log"], "WITHDRAWN")
        self.assertEqual(out["removed_original_mutex_gate"], "REJECTED_EVIDENCE")
        self.assertEqual(out["forged_mutant_green"], "REJECTED_EVIDENCE")
        self.assertEqual(out["replaced_mutant_source"], "REJECTED_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
