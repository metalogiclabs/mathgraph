import math
import unittest
import numpy as np
from scipy.spatial.transform import Rotation
from qualify_efrd_mocap_pose import quantify

def frames(angles,axis="z"):
    n=len(angles)
    q=Rotation.from_euler(axis,angles).as_quat()
    t=np.arange(n,dtype=np.int64)*1000000
    p=np.zeros((n,3))
    return t,q,p

class MocapQualificationTests(unittest.TestCase):
    def test_three_uninterrupted_world_z_revolutions_admit_pose_only(self):
        a=frames(np.linspace(0,6*math.pi,3001))
        d=quantify(*a)
        self.assertTrue(d["world_z_two_turn_pose_qualification"])
        self.assertFalse(d["heading_correction_permitted"])
        self.assertFalse(d["estimator_saw_source_truth"])
    def test_repeated_back_and_forth_not_full_turn(self):
        angles=.8*math.pi*np.sin(np.linspace(0,16*math.pi,4001))
        d=quantify(*frames(angles))
        self.assertGreater(d["total_3d_rotation_travel_turns"],6)
        self.assertLess(d["world_z_longest_directional_yaw_turns"],1)
        self.assertFalse(d["world_z_two_turn_pose_qualification"])
    def test_wrong_axis_even_with_3d_rotation_not_admitted(self):
        d=quantify(*frames(np.linspace(0,8*math.pi,2001),"x"))
        self.assertFalse(d["world_z_two_turn_pose_qualification"])
    def test_one_revolution_does_not_admit(self):
        d=quantify(*frames(np.linspace(0,2*math.pi,2001)))
        self.assertFalse(d["world_z_two_turn_pose_qualification"])
    def test_sparse_108_degree_sample_rejects_alias(self):
        d=quantify(*frames(np.linspace(0,6*math.pi,11)))
        self.assertTrue(d["interpose_rotation_sampling_alias"])
        self.assertFalse(d["world_z_two_turn_pose_qualification"])
    def test_duplicate_header_rejected(self):
        t,q,p=frames(np.linspace(0,1,100))
        t[12]=t[11]
        with self.assertRaises(ValueError):
            quantify(t,q,p)
    def test_bad_norm_rejected(self):
        t,q,p=frames(np.linspace(0,1,100))
        q[10]*=2
        with self.assertRaisesRegex(ValueError,"norm"):
            quantify(t,q,p)
    def test_nan_position_rejected(self):
        t,q,p=frames(np.linspace(0,1,100))
        p[4,0]=float("nan")
        with self.assertRaisesRegex(ValueError,"nonfinite"):
            quantify(t,q,p)
    def test_translation_detected_without_changing_rotation_admission(self):
        t,q,p=frames(np.linspace(0,6*math.pi,3001))
        p[:,0]=np.linspace(0,1,len(p))
        d=quantify(t,q,p)
        self.assertAlmostEqual(d["max_translation_relative_start_m"],1)
        self.assertTrue(d["world_z_two_turn_pose_qualification"])
    def test_reversed_source_clock_rejected(self):
        t,q,p=frames(np.linspace(0,1,100))
        t[15]=t[14]-1
        with self.assertRaisesRegex(ValueError,"timestamps"):
            quantify(t,q,p)
if __name__=="__main__":unittest.main()
