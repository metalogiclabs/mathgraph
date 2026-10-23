"""Independent firstturn freeze and insufficient-later-turn source controls."""
import unittest
import numpy as np
from darkgs_postfirstturn_revisit import classify_revisit,expected_bin
from darkgs_column_v2 import BINS

def desc(i):
    v=np.zeros(24)
    v[i%24]=1.
    return {"bits":1<<(i%16),"absolute":1<<(i%16),
            "contrast":40.,"usable":True,"vec":v,
            "geometry":(24,24,12)}

def sample(rate=1., span=18., image_dt=.025):
    t=np.arange(0,span,.005)
    imu_t=(t*1e9).astype(np.int64)
    w=np.full(len(t),rate,dtype=float)
    images=[]
    for tt in np.arange(.025,span-.03,image_dt):
        phase=tt*rate
        idx=int((abs(phase)%(2*np.pi))/(2*np.pi)*BINS)
        images.append((int(tt*1e9),desc(idx)))
    return imu_t,w,images

class OriginalSourceRevisitTests(unittest.TestCase):
    def test_complete_first_but_not_second_revolution(self):
        t,w,images=sample(rate=1.,span=7.3)
        r=classify_revisit(t,w,images)
        self.assertGreater(r["postfirstturn_original_frames"],0)
        self.assertEqual(r["state"],"NO_SECOND_COMPLETE_GYRO_TURN")
        self.assertFalse(r["fully_separate_later_gyro_revolution_observed"])
        self.assertFalse(r["navigation_correction_authorized"])
    def test_more_than_two_turns_does_not_fake_physical_heading_truth(self):
        t,w,images=sample(rate=1.,span=16.)
        r=classify_revisit(t,w,images)
        self.assertTrue(r["fully_separate_later_gyro_revolution_observed"])
        self.assertEqual(r["physical_true_camera_gyro_time_error_bound"],"UNKNOWN")
        self.assertFalse(r["navigation_correction_authorized"])
    def test_firstturn_map_cannot_be_changed_by_postturn_frame_data(self):
        t,w,images=sample(span=7.3)
        a=classify_revisit(t,w,images)
        changed=[]
        boundary=a["first_turn_completion_source_timestamp_ns"]
        for tt,d in images:
            changed.append((tt,desc(15) if tt>=boundary else d))
        b=classify_revisit(t,w,changed)
        self.assertEqual(a["frozen_reference_bins"],b["frozen_reference_bins"])
        self.assertEqual(a["first_turn_frames_used_for_reference"],b["first_turn_frames_used_for_reference"])
        self.assertEqual(a["postfirstturn_original_frames"],b["postfirstturn_original_frames"])
    def test_zero_gyro_never_stages_postturn_matching(self):
        t,w,images=sample(rate=0.,span=18.)
        r=classify_revisit(t,w,images)
        self.assertEqual(r["postfirstturn_original_frames"],0)
        self.assertEqual(r["state"],"NO_FIRST_COMPLETE_GYRO_TURN")
    def test_bad_gyro_chronology_denied(self):
        t,w,images=sample()
        t[10]=t[9]
        with self.assertRaisesRegex(ValueError,"strictly monotone"):
            classify_revisit(t,w,images)
    def test_camera_timestamp_outside_imu_and_gap_preserved(self):
        t,w,images=sample(span=7.3)
        extra=[(-100_000_000_000,desc(0))]
        r=classify_revisit(t,w,extra+images)
        self.assertEqual(r["image_frames_outside_causal_gyro_source"],1)
        self.assertGreater(r["max_original_camera_header_gap_sec"],100)
        self.assertFalse(r["gyro_image_clock_integrity_certified"])
    def test_nominal_periodic_bin_wrap(self):
        self.assertEqual(expected_bin(2*np.pi+0.01,0),0)
        self.assertEqual(expected_bin(np.pi,0),32)
        # Must preserve frozen v2 signed-phase modulo on counter-rotation.
        self.assertEqual(expected_bin(-np.pi/2,0),48)
        self.assertEqual(expected_bin(-2*np.pi-0.01,0),63)
    def test_counter_rotating_gyro_uses_frozen_signed_phase_bins(self):
        t,w,images=sample(rate=-1.,span=7.3)
        result=classify_revisit(t,w,images)
        self.assertEqual(result["state"],"NO_SECOND_COMPLETE_GYRO_TURN")
        self.assertGreater(result["postfirstturn_original_frames"],0)
        self.assertFalse(result["navigation_correction_authorized"])
    def test_no_unseen_reference_pixels_created(self):
        t,w,images=sample(span=7.3)
        r=classify_revisit(t,w,images)
        self.assertLessEqual(r["frozen_reference_bins"],64)
        self.assertTrue(r["no_heldout_appearance_leaked_to_firstturn_reference"])
    def test_out_of_order_images_are_rejected(self):
        t,w,images=sample(span=7.3)
        images[11],images[12]=images[12],images[11]
        with self.assertRaisesRegex(ValueError,"monotone"):
            classify_revisit(t,w,images)

if __name__=="__main__":
    unittest.main()
