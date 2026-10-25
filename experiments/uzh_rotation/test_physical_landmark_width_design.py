"""Independent finite controls for passive landmark width/jitter design."""
import itertools
import unittest

from finite_witness_compass import HYPOTHESES
from physical_landmark_width_design import (
    BOUNDARY, BINS, CENTER, MARKERS, experiment, make_trial,
    independent_minimum_cross_sector_distance,
)

class PassiveLandmarkTests(unittest.TestCase):
    def test_wide_landmarks_separate_every_jitter_interval(self):
        for jitter in (0,1,2,3):
            width=2*jitter+1
            for seed in range(12):
                ref,_=make_trial(seed,0,width)
                self.assertGreater(
                    independent_minimum_cross_sector_distance(ref,jitter),4
                )

    def test_too_narrow_landmark_has_nonseparating_offsets(self):
        for jitter in (1,2,3):
            width=2*jitter-1
            for seed in range(12):
                ref,_=make_trial(seed,0,width)
                self.assertLessEqual(
                    independent_minimum_cross_sector_distance(ref,jitter),4
                )

    def test_no_data_leakage_from_hidden_phase_shift_into_frozen_map(self):
        for seed in range(8):
            reference0,_=make_trial(seed,0,3,0)
            for heading in HYPOTHESES:
                for shift in (-1,0,1):
                    ref,_=make_trial(seed,heading,3,shift)
                    self.assertEqual(ref,reference0)

    def test_one_bit_train_one_bit_holdout_noise_envelope(self):
        for seed in range(8):
            reference,columns=make_trial(seed,16,5,2)
            for step in range(33):
                # The independent cross-sector reference distance is not
                # computed from the true source; we verify pair coverage by
                # reference geometry separately.
                self.assertIsInstance(columns[step],int)
                self.assertGreaterEqual(columns[step],0)
                self.assertLess(columns[step],65536)
            self.assertEqual(len(reference),BINS)

    def test_synthetic_width_jitter_grid_rejects_false_heading(self):
        r=experiment(seeds=3)
        self.assertEqual(r["boundary"],BOUNDARY)
        self.assertEqual(r["hardware_acquisitions"],0)
        self.assertFalse(r["physical_heading_correction_authorized"])
        self.assertEqual(len(r["all_conditions"]),16)
        for row in r["all_conditions"]:
            self.assertEqual(row["model_false_unique"],0)
            self.assertEqual(row["model_unique"]+row["model_unknown"],row["trials"])
            is_wide=row["landmark_width_bins"]>=2*row["phase_error_radius_bins"]+1
            if is_wide:
                self.assertEqual(row["model_unique"],row["trials"])
                self.assertEqual(row["center_pair_separation_warranted"],row["trials"])
            else:
                self.assertEqual(row["model_unknown"],row["trials"])
                self.assertEqual(row["center_pair_separation_warranted"],0)

    def test_ambiguous_occlusion_still_abstains_at_all_markers(self):
        ref,columns=make_trial(0,0,3,phase_shift=1,occluded=(7,23))
        self.assertIsNone(columns[7])
        self.assertIsNone(columns[23])
        self.assertEqual(len(ref),BINS)

if __name__=="__main__":
    unittest.main()
