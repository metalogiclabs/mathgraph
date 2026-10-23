"""Independent semantic negative controls for source-authority promotion."""
import unittest
from audit_topspin_source_authority import assess_v1_result, MIN_LAG, MAX_LAG

def mock(best=5,status="CANDIDATE_TRAINING_DISTINCT_TEMPORAL_RECURRENCE",
         holdout_score=.91):
    return {"original_sha256":"sourcehash",
            "experiment":{
                "conventional_full_column_descriptor_training":{
                    "decision":status,"best_lag_bins":best,"second_lag_bins":best+4,
                    "margin":.2,"candidate_lags_evaluated":146},
                "event_rate_only_baseline_training":{"best_lag_bins":best},
                "conventional_full_column_descriptor_later":{
                    "heldout_rank":1,"frozen_lag_score":holdout_score}}}

class SourceWarrantControls(unittest.TestCase):
    def test_real_exposed_boundary_5_rejected_even_when_validation_rank_one(self):
        r=assess_v1_result(mock())
        self.assertEqual(r["training_only_gate_state"],
                         "UNKNOWN_MINIMUM_LAG_PERSISTENCE_CONFOUNDED")
        self.assertFalse(r["navigation_heading_correction_authorized"])
    def test_heldout_outcome_does_not_change_gate(self):
        a=assess_v1_result(mock(best=5,holdout_score=1))
        b=assess_v1_result(mock(best=5,holdout_score=-1))
        self.assertEqual(a["training_only_gate_state"],b["training_only_gate_state"])
        self.assertEqual(a["training_best_lag_bins"],b["training_best_lag_bins"])
    def test_maximum_allowed_lag_is_unknown(self):
        r=assess_v1_result(mock(best=MAX_LAG))
        self.assertEqual(r["training_only_gate_state"],
                         "UNKNOWN_MAXIMUM_LAG_GRAMMAR_BOUNDARY")
    def test_interior_only_candidate_without_navigation_permission(self):
        r=assess_v1_result(mock(best=35))
        self.assertEqual(r["training_only_gate_state"],
                         "CANDIDATE_NONBOUNDARY_TEMPORAL_RECURRENCE_ONLY")
        self.assertFalse(r["navigation_heading_correction_authorized"])
        self.assertFalse(r["source_proves_full_physical_turns"])
    def test_original_unknown_kept_unknown(self):
        r=assess_v1_result(mock(best=35,status="UNKNOWN_TEMPORAL_AMBIGUITY"))
        self.assertEqual(r["training_only_gate_state"],
                         "UNKNOWN_OR_REJECTED_BY_ORIGINAL_TRAINING_TEST")
    def test_one_column_evidence_cannot_create_external_gyro(self):
        r=assess_v1_result(mock(best=25))
        self.assertFalse(r["raw_camera_gyro_alignment"])
        self.assertFalse(r["independent_external_heading_truth"])
        self.assertEqual(r["special_mathgraph_reliability_advantage"],"UNKNOWN")
    def test_minimum_search_lag_is_5_windows(self):
        self.assertEqual(MIN_LAG,5)

if __name__=="__main__":
    unittest.main()
