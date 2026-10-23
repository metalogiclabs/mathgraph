"""Source-fidelity controls for lab2 before opening second-scene mocap."""
import math
import unittest
import numpy as np
from scipy.spatial.transform import Rotation

from qualify_efrd_mocap_pose import quantify
from qualify_efrd_lab2_pose import LAB2_SHA256, LAB2_BYTES

def track(angle,axis="z"):
    angle=np.asarray(angle)
    ts=np.arange(len(angle),dtype=np.int64)*1000000
    q=Rotation.from_euler(axis,angle).as_quat()
    xyz=np.zeros((len(angle),3))
    return ts,q,xyz

class FrozenLab2Controls(unittest.TestCase):
    def test_source_pin_fixed(self):
        self.assertEqual(LAB2_SHA256,"69fd0fb8fafcf01cde467904d54baa90b98d5c85cb22bd15034770be3f8ed7c1")
        self.assertEqual(LAB2_BYTES,1394913640)
    def test_positive_two_turn_controls(self):
        d=quantify(*track(np.linspace(0,6*math.pi,3001)))
        self.assertTrue(d["world_z_two_turn_pose_qualification"])
    def test_oscillation_rejected_despite_large_total_3d_rotation(self):
        d=quantify(*track(np.sin(np.linspace(0,20*math.pi,6001))*math.pi*.8))
        self.assertFalse(d["world_z_two_turn_pose_qualification"])
        self.assertGreater(d["total_3d_rotation_travel_turns"],8)
    def test_wrong_axis_rejected(self):
        d=quantify(*track(np.linspace(0,6*math.pi,3001),"x"))
        self.assertFalse(d["world_z_two_turn_pose_qualification"])
    def test_one_turn_rejected(self):
        d=quantify(*track(np.linspace(0,2*math.pi,2001)))
        self.assertFalse(d["world_z_two_turn_pose_qualification"])

if __name__=="__main__":
    unittest.main()
