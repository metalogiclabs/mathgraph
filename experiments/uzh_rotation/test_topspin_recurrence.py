"""Independent negative controls for real-column temporal recurrence method."""
import unittest
import numpy as np

from audit_topspin_recurrence import (
    TIME_BIN_US, VERTICAL_BINS, POLARITIES,
    standardized_features, lag_similarity, training_selection,
    analyze_counts,
)

class RealColumnRecurrenceTests(unittest.TestCase):
    def test_training_gate_withholds_exact_period_multiples(self):
        # Any two equal-score non-neighbor peaks defeat unique-period claims.
        scores={"10":{"score":.81},"20":{"score":.81},"30":{"score":.79}}
        d=training_selection(scores)
        self.assertEqual(d["decision"],"UNKNOWN_TEMPORAL_AMBIGUITY")
        self.assertEqual(d["best_lag_bins"],10)
    def test_sparse_map_empty_windows_not_counted_as_matches(self):
        mat=np.zeros((400,VERTICAL_BINS*POLARITIES))
        occupancy=np.zeros(400,dtype=int)
        s=lag_similarity(mat,occupancy,10,0,200)
        self.assertIsNone(s["score"])
        self.assertEqual(s["eligible_pairs"],0)
    def test_shifted_repeated_realistic_pattern_has_finite_score(self):
        rng=np.random.default_rng(27)
        a=rng.poisson(1.2,size=(600,VERTICAL_BINS*POLARITIES))
        features=standardized_features(a,300)
        s=lag_similarity(features,a.sum(axis=1),20,0,300)
        self.assertTrue(-1<=s["score"]<=1)
        self.assertGreater(s["eligible_pairs"],40)
    def test_validation_changes_cannot_change_first_half_selection(self):
        rng=np.random.default_rng(14)
        a=rng.poisson(1.0,size=(600,VERTICAL_BINS*POLARITIES))
        b=a.copy()
        b[300:]=rng.poisson(15,size=b[300:].shape)
        left=analyze_counts(a)
        right=analyze_counts(b)
        self.assertEqual(left["conventional_full_column_descriptor_training"],
                         right["conventional_full_column_descriptor_training"])
        self.assertEqual(left["event_rate_only_baseline_training"],
                         right["event_rate_only_baseline_training"])
    def test_uninformative_reference_cannot_fabricate_heading(self):
        a=np.zeros((600,VERTICAL_BINS*POLARITIES),dtype=int)
        r=analyze_counts(a)
        self.assertEqual(r["evidence_gate_decision"],
                         "UNKNOWN_NO_TRAINING_RECURRENT_CUE")
        self.assertFalse(r["navigation_correction_authorized"])
    def test_min_support_prevents_accidental_one_pair(self):
        a=np.zeros((600,VERTICAL_BINS*POLARITIES),dtype=int)
        a[0,0]=10;a[8,0]=10
        d=analyze_counts(a)
        self.assertEqual(d["conventional_full_column_descriptor_training"]["decision"],
                         "UNKNOWN_NO_TRAINING_RECURRENT_CUE")
    def test_negative_descriptor_values_rejected(self):
        a=np.ones((600,VERTICAL_BINS*POLARITIES))
        a[1,1]=-1
        with self.assertRaisesRegex(ValueError,"invalid"):
            standardized_features(a,300)
    def test_expected_finite_frequency_grammar(self):
        self.assertEqual(TIME_BIN_US,100000)
        self.assertEqual((VERTICAL_BINS,POLARITIES),(24,2))

if __name__=="__main__":
    unittest.main()
