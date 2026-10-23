"""Source metadata positive and negative controls independent of Drive."""
import unittest
from qualify_efrd_sources import evaluate_file_manifest,sequence_for_path

class EFRDSourceTests(unittest.TestCase):
    def test_genuinely_separate_mocap_candidate(self):
        d=evaluate_file_manifest([{"id":"1","path":"GT-Mocap/mahjong-1.bag"}])
        self.assertEqual(d["mocap_file_candidates"],1)
        self.assertFalse(d["qualified_multirevolution_dataset"])
        self.assertFalse(d["file_records"][0]["heading_correction_authorized"])
        self.assertFalse(d["file_records"][0]["independent_heading_verified"])
    def test_imu_derived_pose_is_never_external_truth(self):
        d=evaluate_file_manifest([{"id":"b","path":"GT-IMU/building.bag"}])
        self.assertEqual(d["mocap_file_candidates"],0)
        self.assertFalse(d["file_records"][0]["external_mocap_advertised_by_authors"])
    def test_false_prefix_does_not_impersonate_mocap_source(self):
        for bad in ("mahjong-10.bag","pseumahjong-1.bag","mahjong-11.zip"):
            self.assertIsNone(sequence_for_path(bad))
    def test_second_mocap_candidate(self):
        self.assertEqual(sequence_for_path("mahjong_2/measurements.bag"),"mahjong-2")
    def test_unexpected_dataset_name_is_unknown(self):
        d=evaluate_file_manifest([{"id":"xyz","path":"Unknown_720spin.bag"}])
        self.assertEqual(d["mocap_file_candidates"],0)
        self.assertIsNone(d["file_records"][0]["sequence"])
    def test_cannot_reuse_drive_id_as_new_source(self):
        with self.assertRaisesRegex(ValueError,"duplicate"):
            evaluate_file_manifest([{"id":"A","path":"building.bag"},{"id":"A","path":"mahjong-1.bag"}])
    def test_path_traversal_fails(self):
        with self.assertRaisesRegex(ValueError,"unsafe"):
            evaluate_file_manifest([{"id":"x","path":"../mahjong-2.bag"}])
    def test_bad_source_input_fails(self):
        with self.assertRaises(ValueError):
            evaluate_file_manifest([{"path":"mahjong-1.bag"}])
if __name__=="__main__":
    unittest.main()
