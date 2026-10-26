"""Independent negative controls for synthetic joint bias/clock model."""
import dataclasses
import math
import unittest
import numpy as np

from physical_joint_bias_clock_model import (
    make_capture, run_estimators, score, benchmark, SUBBIN,
)

class JointBiasClockTests(unittest.TestCase):
    def test_hidden_truth_must_not_enter_estimator(self):
        c=make_capture(0,"varying")
        original=run_estimators(c)
        altered=dataclasses.replace(c,hidden_true_bias=999.,
            hidden_theta_at_camera_times=np.ones_like(c.hidden_theta_at_camera_times)*999.)
        self.assertEqual(original,run_estimators(altered))
        self.assertNotEqual(score(c,original)["rmse_unwrapped_deg"],
                            score(altered,original)["rmse_unwrapped_deg"])

    def test_optical_signal_subbin_quantized(self):
        c=make_capture(1,"varying")
        for bearing in c.camera_bearing:
            if math.isfinite(bearing):
                self.assertAlmostEqual(bearing/SUBBIN,
                    round(bearing/SUBBIN),places=8)

    def test_steady_speed_clock_is_unidentifiable(self):
        r=run_estimators(make_capture(0,"steady"))
        self.assertEqual(r["records"][-1]["clock_span_seconds_if_model"],.08)
        self.assertFalse(any(e["state"]=="MODEL_JOINT_BOUNDED" for e in r["records"]))
        self.assertFalse(r["physical_authority"])

    def test_variable_rate_reduces_clock_interval_not_universally(self):
        c=make_capture(0,"varying_clock_shift")
        r=run_estimators(c)
        self.assertLess(r["records"][-1]["clock_span_seconds_if_model"],.025)
        self.assertEqual(r["records"][-1]["state"],"MODEL_JOINT_BOUNDED")
        self.assertTrue(score(c,r)["claimed_bias_interval_contains_truth_on_bounded_steps"])

    def test_camera_outlier_withdraws_bounded_model(self):
        c=make_capture(0,"varying")
        normal=run_estimators(c)
        changed=c.camera_bearing.copy()
        changed[48]=((changed[48]+1.6+math.pi)%(2*math.pi))-math.pi
        corrupted=run_estimators(dataclasses.replace(c,camera_bearing=changed))
        self.assertNotEqual(normal["final_state"],corrupted["final_state"])
        self.assertGreater(
            sum(e["state"]=="UNKNOWN_CONFLICT" for e in corrupted["records"]),100)

    def test_timevarying_bias_invalidates_fixed_parameter_warrant(self):
        c=make_capture(0,"varying_drift")
        r=run_estimators(c)
        result=score(c,r)
        self.assertFalse(result["claimed_bias_interval_contains_truth_on_bounded_steps"])
        self.assertFalse(result["physical_result"])
        self.assertTrue(any(e["state"]=="UNKNOWN_CONFLICT" for e in r["records"]))

    def test_equal_input_lesser_ls_win_and_stronger_huber_negative(self):
        r=benchmark(seeds=8)
        self.assertTrue(r["same_camera_and_gyro_for_all_compared_estimators"])
        self.assertTrue(r["same_fixed_acquisition_schedule_for_all_estimators"])
        self.assertFalse(r["physical_heading_authorized"])
        cases={x["condition"]:x for x in r["conditions"]}
        v=cases["varying"]["mean_unwrapped_rmse_deg"]
        self.assertLess(v["mathgraph"],v["conventional_ls"])
        self.assertGreater(
            cases["steady"]["mean_unwrapped_rmse_deg"]["mathgraph"],
            cases["steady"]["mean_unwrapped_rmse_deg"]["conventional_huber"])
        adversarial=cases["varying_outliers"]["mean_unwrapped_rmse_deg"]
        self.assertLess(adversarial["conventional_huber"],adversarial["mathgraph"])
        self.assertGreater(cases["varying_outliers"]["mean_conflict_fraction"],.6)
        self.assertFalse(cases["varying_drift"]["all_bounded_bias_intervals_contain_hidden_true_bias"])

if __name__=="__main__":unittest.main()
