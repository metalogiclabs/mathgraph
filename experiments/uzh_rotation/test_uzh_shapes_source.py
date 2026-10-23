"""Independent dataset motion admission controls for original UZH source."""
import math
import unittest
import numpy as np
from scipy.spatial.transform import Rotation
from qualify_uzh_shapes_source import qualify,streak

def make(yaw,axis="y",n=None,dt=.005):
    angle=np.asarray(yaw,dtype=float)
    gt=np.zeros((len(angle),8),dtype=float)
    gt[:,0]=np.arange(len(angle))*dt
    gt[:,4:8]=Rotation.from_euler(axis,angle).as_quat()
    return gt

class UZHSourceControls(unittest.TestCase):
    def test_real_synthetic_three_turn_source_admitted(self):
        gt=make(np.linspace(0,6*math.pi,4001))
        x=qualify(gt)
        self.assertTrue(x["any_predeclared_axis_qualifies_2_turns"])
        self.assertTrue(x["per_body_axis"]["y"]["qualifies_2_turns_90pct_axis"])
        self.assertFalse(x["sensor_event_values_read"])
    def test_repeated_partial_sweeps_not_continuous_two_turns(self):
        gt=make(.65*math.pi*np.sin(np.linspace(0,20*math.pi,4001)))
        d=qualify(gt)
        self.assertGreater(d["total_3d_rotation_turns"],5)
        self.assertFalse(d["any_predeclared_axis_qualifies_2_turns"])
    def test_all_axes_reported_before_selection(self):
        gt=make(np.linspace(0,8*math.pi,4001),axis="x")
        result=qualify(gt)
        self.assertEqual(set(result["per_body_axis"]),{"x","y","z"})
        self.assertFalse(result["per_body_axis"]["y"]["qualifies_2_turns_90pct_axis"])
    def test_source_quaternion_sign_invariance(self):
        gt=make(np.linspace(0,6*math.pi,4001))
        a=qualify(gt)
        gt[::2,4:8]*=-1
        b=qualify(gt)
        self.assertAlmostEqual(a["per_body_axis"]["y"]["longest_uninterrupted_projected_turns"],
                               b["per_body_axis"]["y"]["longest_uninterrupted_projected_turns"],places=8)
    def test_nonunit_quaternion_refused(self):
        gt=make(np.linspace(0,1,1000))
        gt[7,4:8]*=2
        with self.assertRaisesRegex(ValueError,"quaternion"):
            qualify(gt)
    def test_repeated_original_timestamp_refused(self):
        gt=make(np.linspace(0,1,1000))
        gt[3,0]=gt[2,0]
        with self.assertRaisesRegex(ValueError,"monotonicity"):
            qualify(gt)
    def test_gaps_fail_closed_even_if_angular_streak_looks_good(self):
        gt=make(np.linspace(0,6*math.pi,4001))
        gt[1000:,0]+=1.0
        d=qualify(gt)
        self.assertTrue(d["source_alias_or_gap_obstruction"])
        self.assertFalse(d["any_predeclared_axis_qualifies_2_turns"])
    def test_streak_small_jitter_tolerance(self):
        arr=np.array([.1,.1,-.0001,.1])
        x,flips=streak(arr)
        self.assertAlmostEqual(x,.3/(2*math.pi))
        self.assertEqual(flips,0)

if __name__=="__main__":
    unittest.main()
