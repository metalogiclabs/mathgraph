from pathlib import Path
import unittest


class MathlibBridgeSourceChecks(unittest.TestCase):
    def test_exact_source_import_and_no_local_proof_holes(self):
        proof = (Path(__file__).resolve().parents[1] /
                 'experiments/annals_mathlib_bridge_v0/SingletonBridge.lean').read_text()
        self.assertIn('import AnnalsChallenge.AnnalsOfMathematics.«2021-194-2-FractionalExpectationThresholds»', proof)
        self.assertIn('theorem singletonLargestMinimalSize', proof)
        self.assertNotIn('by\n  sorry', proof)


if __name__ == '__main__':
    unittest.main()
