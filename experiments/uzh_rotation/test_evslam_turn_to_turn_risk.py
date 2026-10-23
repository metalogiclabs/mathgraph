"""Independent finite GT-only parallax and view-drift controls."""
import unittest
import numpy as np
from scipy.spatial.transform import Rotation
from evslam_turn_to_turn_risk import measure_pose_revisit,pose_at_phase,TWO_PI

def source(n=721,turns=4,drift_m=0,axis="y"):
    gt=np.zeros((n,11),dtype=float)
    theta=np.linspace(0,turns*TWO_PI,n)
    gt[:,0]=np.linspace(0,30,n)
    gt[:,4:8]=Rotation.from_euler(axis,theta).as_quat()
    gt[:,1]=np.linspace(0,drift_m,n)
    return gt

class RevisitAuthorityTests(unittest.TestCase):
    def test_stationary_exactly_repeatable_four_turns_has_zero_pose_difference(self):
        r=measure_pose_revisit(source())
        self.assertGreaterEqual(r["later_full_turns_measured"],2)
        for x in r["per_turn_later"]:
            self.assertLess(x["distance_max_m"],1e-9)
            self.assertLess(x["orientation_difference_max_deg"],1e-6)
        self.assertFalse(r["visual_scene_stationarity_verified"])
    def test_translating_multiturn_is_not_same_location(self):
        r=measure_pose_revisit(source(drift_m=3))
        self.assertGreater(r["per_turn_later"][0]["distance_median_m"],.5)
        self.assertFalse(r["navigation_correction_authorized"])
    def test_short_turn_not_fabricated_by_total_time(self):
        r=measure_pose_revisit(source(turns=.7))
        self.assertEqual(r["later_full_turns_measured"],0)
    def test_non_unit_quaternion_refused(self):
        gt=source()
        gt[50,4:8]*=2
        with self.assertRaisesRegex(ValueError,"norm"):
            measure_pose_revisit(gt)
    def test_wrong_axis_no_y_return(self):
        r=measure_pose_revisit(source(axis="x"))
        self.assertEqual(r["later_full_turns_measured"],0)
    def test_non_monotone_source_time_refused(self):
        gt=source()
        gt[10,0]=gt[9,0]
        with self.assertRaisesRegex(ValueError,"non-increasing"):
            measure_pose_revisit(gt)
    def test_first_increasing_crossing_does_not_clip_reversals(self):
        phase=np.array([0.,.75, .5,1.0])
        positions=np.array([[0.,0,0],[1.,0,0],[2.,0,0],[3.,0,0]])
        q=np.tile(np.array([0.,0.,0.,1.]),(4,1))
        a=pose_at_phase(phase,positions,q,.625)
        self.assertAlmostEqual(a[0][0],.625)
        self.assertIsNone(pose_at_phase(phase,positions,q,1.5))
if __name__=="__main__":
    unittest.main()
