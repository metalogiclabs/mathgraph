"""Clock-sensitive first-turn test controls, no raw camera sensor claims."""
import math
import unittest
import numpy as np
from scipy.spatial.transform import Rotation
from evslam_source_phase_clock import body_y_phase,interval_membership,tick_guard,sensitivity,TWO_PI

def make(angular_rate=1,interval=.1,samples=201,axis="y"):
    t=np.arange(samples)*interval
    gt=np.zeros((samples,11),dtype=float)
    gt[:,0]=t
    gt[:,4:8]=Rotation.from_euler(axis,angular_rate*t).as_quat()
    return gt

class PhaseClockTests(unittest.TestCase):
    def test_zero_shift_no_crossings_with_gt_samples_except_edges(self):
        gt=make()
        r=sensitivity(gt,0)
        self.assertEqual(r["first_turn_two_sided_time_interval_crosses_angular_bin"],0)
        self.assertEqual(r["first_turn_positive_time_offset_bin_mismatches"],0)
        self.assertFalse(r["navigation_correction_authorized"])
    def test_nonzero_shift_can_cross_bin_boundary(self):
        gt=make(angular_rate=1.9)
        r=sensitivity(gt,.0026)
        self.assertGreater(r["first_turn_source_pose_samples_with_two_sided_support"],1)
        self.assertGreaterEqual(r["C99_compatible_conservative_tick_guard_refusals"],
                                r["first_turn_two_sided_time_interval_crosses_angular_bin"])
    def test_increasing_speed_increases_hypothetical_phase_shift(self):
        fast=sensitivity(make(angular_rate=2),.0026)
        slow=sensitivity(make(angular_rate=1),.0026)
        self.assertGreater(fast["hypothetical_clock_offset_shift_deg"]["max"],
                           slow["hypothetical_clock_offset_shift_deg"]["max"])
    def test_quaternion_sign_flips_do_not_change_phase_magnitudes(self):
        gt=make()
        a=sensitivity(gt,.0026)
        gt[::2,4:8]*=-1
        b=sensitivity(gt,.0026)
        self.assertAlmostEqual(a["hypothetical_clock_offset_shift_deg"]["max"],
                               b["hypothetical_clock_offset_shift_deg"]["max"],places=9)
    def test_nonmonotone_source_times_rejected(self):
        gt=make()
        gt[10,0]=gt[9,0]
        with self.assertRaisesRegex(ValueError,"chronology"):
            body_y_phase(gt)
    def test_wrong_body_axis_does_not_fabricate_y_spin(self):
        r=sensitivity(make(axis="x"),.0026)
        self.assertLess(r["body_y_projected_signed_turns"],.001)
    def test_analytical_small_window(self):
        t=np.array([0.,1.,2.])
        p=np.array([0.,1.,2.])
        a,b=interval_membership(t,p,1.,.2)
        self.assertAlmostEqual(a,.8)
        self.assertAlmostEqual(b,1.2)
    def test_C_guard_rejects_closed_subtick_crossing(self):
        self.assertTrue(tick_guard(8/1024*TWO_PI,7))
        self.assertFalse(tick_guard(16/1024*TWO_PI,1))
    def test_offset_is_not_safety_certification(self):
        r=sensitivity(make(),.0026)
        self.assertTrue(r["not_a_calibrated_angle_error_bound"])
        self.assertTrue(r["not_actual_camera_event_samples"])
    def test_invalid_shift_rejected(self):
        with self.assertRaises(ValueError):
            sensitivity(make(),float("nan"))
if __name__=="__main__":
    unittest.main()
