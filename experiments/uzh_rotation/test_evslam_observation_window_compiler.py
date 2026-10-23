"""Exact finite window compilation adversaries; no GT oracle leaks into estimator."""
import math
import unittest

import numpy as np
from scipy.spatial.transform import Rotation

from evslam_observation_window_compiler import (
    TWO_PI, BINS, BIN_RAD, bin_occupancy_windows,
    first_complete_projected_turn, compile_observation_windows, evaluate_original,
)


def ideal_phase(turn_duration=2.56, steps=201, number_turns=2):
    t = np.linspace(0, turn_duration * number_turns, steps)
    p = t * TWO_PI / turn_duration
    return t, p


def GT_y(t, p):
    z=np.zeros((len(t),11),dtype=float)
    z[:,0]=t
    z[:,4:8]=Rotation.from_euler("y",p.reshape(-1,1)).as_quat()
    return z


class ClockNecessityTests(unittest.TestCase):
    def test_exact_uniform_spinning_angular_bin_dwell_and_clock_erosion(self):
        t,p=ideal_phase()
        delta=.0025
        a=compile_observation_windows(t,p,delta)
        self.assertTrue(a['all_bins_has_capture_window'])
        self.assertEqual(a['bins_with_positive_clock_robust_window'],64)
        expected=.04-2*delta
        self.assertAlmostEqual(a['shortest_required_window_s'],expected,places=8)
        self.assertAlmostEqual(a['hypothetical_source_window_clock_halfwidth_ceiling_s'],.02,places=8)
        self.assertEqual(a['minimum_bins_guaranteed_at_uniform_rate_hz']['400'],64)
        self.assertEqual(a['cadence_hz_strictly_above_required_for_all_phase_offsets'],29)
        self.assertFalse(a['navigation_authorized'])
        self.assertFalse(a['source_timing_bound_authenticated'])

    def test_timing_uncertainty_can_make_64_bins_impossible_even_at_400hz(self):
        t,p=ideal_phase()
        a=compile_observation_windows(t,p,.021)
        self.assertEqual(a['state'],'BOUNDED_MISSING_SOURCE_PHASE_WINDOWS')
        self.assertEqual(a['bins_with_positive_clock_robust_window'],0)
        self.assertEqual(a['minimum_bins_guaranteed_at_uniform_rate_hz']['400'],0)
        self.assertEqual(len(a['bins_without_clock_robust_window']),64)

    def test_complete_2pi_turn_is_required_before_source_admission(self):
        t=np.linspace(0,3,61)
        p=np.linspace(0,1.5*math.pi,61)
        a=compile_observation_windows(t,p,.001)
        self.assertEqual(a['state'],'BOUNDED_NO_FIRST_COMPLETE_TURN')
        self.assertFalse(a['all_bins_has_capture_window'])

    def test_exact_first_turn_stop_ignores_future_forged_motion(self):
        t,p=ideal_phase(number_turns=3)
        d=compile_observation_windows(t,p,.002)
        self.assertAlmostEqual(d['first_complete_turn_timestamp_s'],2.56,places=8)
        self.assertLess(d['source_first_turn_duration_s'],2.57)
        self.assertTrue(d['all_bins_has_capture_window'])

    def test_false_authentication_does_not_suddenly_authorize_navigation(self):
        t,p=ideal_phase()
        for delta in (0.,.001,.005,.01,.02):
            x=compile_observation_windows(t,p,delta)
            self.assertFalse(x['source_timing_bound_authenticated'])
            self.assertFalse(x['navigation_authorized'])
            self.assertTrue(x['no_camera_or_IMU_readings_acquired'])

    def test_increasing_halfwidth_never_increases_certifiable_bin_count(self):
        t,p=ideal_phase()
        counts=[compile_observation_windows(t,p,d)['bins_with_positive_clock_robust_window']
                for d in (0.,.001,.005,.01,.02,.03)]
        self.assertEqual(counts,sorted(counts,reverse=True))

    def test_repeated_backward_trajectory_not_made_monotone(self):
        t=np.array([0.,1.,2.,3.,4.,5.])
        p=np.array([0., 2*BIN_RAD, .5*BIN_RAD, 3*BIN_RAD, 32*BIN_RAD, TWO_PI])
        obj=bin_occupancy_windows(t,p)
        self.assertGreaterEqual(len(obj[1]),2)
        compilation=compile_observation_windows(t,p,0)
        self.assertEqual(compilation['first_complete_turn_timestamp_s'],5.)

    def test_many_sampling_phases_observe_every_bin_when_rate_exceeds_window(self):
        t,p=ideal_phase()
        delta=.0025
        d=compile_observation_windows(t,p,delta)
        freq=d['cadence_hz_strictly_above_required_for_all_phase_offsets']
        for shift in np.linspace(0,1/freq,11,endpoint=False):
            proposed=shift+np.arange(int(t[-1]*freq)+2)/freq
            seen={int(b) for b,slot in d['longest_available_window_per_bin'].items()
                  if np.any((proposed>slot['first_observable_s']) &
                            (proposed<slot['last_observable_s']))}
            self.assertEqual(len(seen),64)

    def test_piecewise_exact_boundary_intersection_matches_independent_grid(self):
        t=np.array([0., .8, 1.7, 2.4, 3.2, 4.5, 5.2, 6.0])
        p=np.array([0., 1.2, 2.1, 1.5, 3.0, 4.9, 5.5, TWO_PI+.3])
        delta=.017
        d=compile_observation_windows(t,p,delta)
        self.assertTrue(d['first_complete_turn_timestamp_s']<t[-1])
        windows=d['longest_available_window_per_bin']
        for name, slot in windows.items():
            b=int(name)
            mid=slot['offline_GT_oracle_midpoint_s']
            left,right=mid-delta,mid+delta
            inside=np.r_[np.interp(left,t,p), np.interp(right,t,p),
                         p[(t>left)&(t<right)]]
            self.assertGreaterEqual(np.min(inside), b*BIN_RAD-1e-10)
            self.assertLessEqual(np.max(inside), (b+1)*BIN_RAD+1e-10)

    def test_real_GT_oracle_not_camera_samples(self):
        t,p=ideal_phase()
        a=evaluate_original(GT_y(t,p),.002)
        self.assertTrue(a['all_bins_has_capture_window'])
        self.assertTrue(a['timestamp_locations_chosen_with_offline_GT_not_online_sensor'])
        self.assertFalse(a['visual_recognition_verified'])

    def test_source_timestamps_nonmonotone_refused(self):
        t,p=ideal_phase()
        t[17]=t[16]
        with self.assertRaises(ValueError):
            compile_observation_windows(t,p,.001)

    def test_invalid_error_width_refused(self):
        t,p=ideal_phase()
        for val in (float('nan'),-1.0,float('inf')):
            with self.assertRaises(ValueError):
                compile_observation_windows(t,p,val)


if __name__=='__main__':
    unittest.main()
