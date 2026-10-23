"""Adversarial qualifiers independent of source identities."""
import unittest
import math
import numpy as np
from scipy.spatial.transform import Rotation
from evslam_reference_turns import analyze, independent_rotvecs, longest_directional

def fake(yaw,axis="y",stride=.1):
    n=len(yaw)
    gt=np.zeros((n,11),dtype=float)
    gt[:,0]=np.arange(n)*stride
    gt[:,4:8]=Rotation.from_euler(axis,yaw).as_quat()
    return gt,gt[:,0].copy()

class TestReferenceTurns(unittest.TestCase):
    def test_three_turn_spin_y_is_candidate(self):
        a,b=fake(np.linspace(0,6*math.pi,501))
        r=analyze(a,b,"drone_rot_norm")
        self.assertTrue(r["recorded_body_y_2plus_revolutions_candidate"])
        self.assertAlmostEqual(r["axis_results"]["y"]["longest_turns"],3,places=4)
        self.assertLess(r["independent_quaternion_derivations_max_rad_difference"],1e-9)
        self.assertFalse(r["navigation_correction_permitted"])
    def test_many_partial_y_sweeps_not_qualified(self):
        a,b=fake(.6*math.pi*np.sin(np.linspace(0,20*math.pi,501)))
        r=analyze(a,b,"drone_rot_norm")
        self.assertGreater(r["total_3d_rotation_travel_turns"],10)
        self.assertFalse(r["recorded_body_y_2plus_revolutions_candidate"])
    def test_turning_on_x_does_not_authorize_y(self):
        a,b=fake(np.linspace(0,8*math.pi,501),axis="x")
        r=analyze(a,b,"drone_rot_norm")
        self.assertTrue(r["axis_results"]["x"]["qualified_2_turns_in_recorded_pose_model"])
        self.assertFalse(r["axis_results"]["y"]["qualified_2_turns_in_recorded_pose_model"])
    def test_quaternion_sign_invariance(self):
        a,b=fake(np.linspace(0,6*math.pi,501))
        a[::2,4:8]*=-1
        r=analyze(a,b,"drone_rot_norm")
        self.assertTrue(r["recorded_body_y_2plus_revolutions_candidate"])
    def test_too_large_pose_step_does_not_prove_continuity(self):
        a,b=fake(np.linspace(0,12*math.pi,21))  # 108 degrees/step, genuinely above 90
        r=analyze(a,b,"drone_rot_norm")
        self.assertFalse(r["recorded_body_y_2plus_revolutions_candidate"])
        self.assertFalse(r["source_pairwise_sampling_admissible"])
    def test_undersampled_clock_cannot_be_overlooked(self):
        a,b=fake(np.linspace(0,6*math.pi,301),stride=.5)
        r=analyze(a,b,"drone_rot_norm")
        self.assertFalse(r["source_pairwise_sampling_admissible"])
    def test_duplicate_timestamp_rejected(self):
        a,b=fake(np.linspace(0,6*math.pi,301))
        a[10,0]=a[9,0]
        with self.assertRaises(ValueError):
            analyze(a,b,"drone_rot_norm")
    def test_reference_does_not_relabel_pose(self):
        a,b=fake(np.linspace(0,6*math.pi,301))
        b=b+.05
        r=analyze(a,b,"drone_rot_norm")
        self.assertEqual(r["reference_pose_timestamps_matched_1ms"],0)
        self.assertFalse(r["navigation_correction_permitted"])
    def test_translated_camera_not_assumed_stationary(self):
        a,b=fake(np.linspace(0,6*math.pi,301))
        a[:,1]=np.linspace(0,2,301)
        r=analyze(a,b,"drone_rot_norm")
        self.assertGreater(r["translation_path_m"],1.9)
        self.assertTrue(r["recorded_body_y_2plus_revolutions_candidate"])
        self.assertFalse(r["later_turn_camera_recognition_tested"])
    def test_nonunit_quaternion_fail(self):
        a,b=fake(np.linspace(0,6*math.pi,301))
        a[50,4:8]*=2
        with self.assertRaises(ValueError):
            analyze(a,b,"drone_rot_norm")
    def test_path_gt_does_not_trigger_corrected_heading(self):
        a,b=fake(np.linspace(0,6*math.pi,301))
        r=analyze(a,b,"drone_rot_norm")
        self.assertFalse(r["first_revolution_visual_map_built"])
        self.assertFalse(r["camera_imu_temporal_alignment_verified"])
if __name__=="__main__":
    unittest.main()
