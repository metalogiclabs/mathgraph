"""Independent source-faithful positive/negative real IMU-mocap timing controls."""
import math
import unittest
import numpy as np
from scipy.spatial.transform import Rotation
from qualify_uzh_gyro_clock import evaluate,pearson,IMU_SHA,GT_SHA

def example(duration=50,lag=.014,noise=0.):
    # Ground truth and gyro are separately sampled and timestamped; positive
    # finite control exercises frozen lag fit versus causal heldout data.
    tg=np.arange(0,duration,.005)
    ti=np.arange(lag,duration+lag,.001)
    def omega(t):
        return 1+0.7*np.sin(2.7*t)+0.4*np.sin(8*t)
    angular= tg - 0.7/2.7*np.cos(2.7*tg) -0.4/8*np.cos(8*tg)
    gt=np.zeros((len(tg),8),dtype=float)
    gt[:,0]=tg
    gt[:,4:8]=Rotation.from_euler("y",angular).as_quat()
    imu=np.zeros((len(ti),7),dtype=float)
    imu[:,0]=ti
    imu[:,5]=omega(ti-lag)
    if noise:
        rng=np.random.default_rng(12)
        imu[:,5]+=rng.normal(0,noise,size=len(ti))
    return imu,gt

class RealClockControls(unittest.TestCase):
    def test_synthetic_shift_training_then_frozen_validation(self):
        imu,gt=example(lag=.014)
        r=evaluate(imu,gt)
        self.assertAlmostEqual(r["frozen_training_selected_lag_ms"],14,delta=3)
        self.assertGreater(r["validation_selected_lag_correlation"],.95)
        self.assertFalse(r["heading_correction_authorized"])
        self.assertFalse(r["timing_bound_independently_certified"])
    def test_unshifted_prefers_zero_clock_offset(self):
        imu,gt=example(lag=0)
        r=evaluate(imu,gt)
        self.assertAlmostEqual(r["frozen_training_selected_lag_ms"],0,delta=3)
    def test_flat_source_is_not_an_authenticated_clock(self):
        imu,gt=example()
        imu[:,4:7]=0
        r=evaluate(imu,gt)
        self.assertEqual(r["status"],"UNKNOWN_NO_IDENTIFIABLE_CLOCK")
    def test_reversed_clock_is_rejected(self):
        imu,gt=example()
        imu[10,0]=imu[9,0]-.01
        with self.assertRaisesRegex(ValueError,"monotone"):
            evaluate(imu,gt)
    def test_duplicate_mocap_timestamp_is_rejected(self):
        imu,gt=example()
        gt[60,0]=gt[59,0]
        with self.assertRaisesRegex(ValueError,"monotone"):
            evaluate(imu,gt)
    def test_fake_quaternion_magnitude_rejected(self):
        imu,gt=example()
        gt[30,4:8]*=2
        with self.assertRaisesRegex(ValueError,"norm"):
            evaluate(imu,gt)
    def test_wrong_units_do_not_create_absolute_error_certificate(self):
        imu,gt=example()
        imu[:,4:7]*=10
        r=evaluate(imu,gt)
        self.assertFalse(r["gyro_orientation_phase_bound_certified"])
        self.assertGreater(r["validation_selected_lag_magnitude_error_rad_s"]["median"],.1)
    def test_source_sha_identifiers_prior_frozen(self):
        self.assertEqual(IMU_SHA,"d209e3e203970f64efdb0ed28de900e4554a0ae0aedb9f7bb388cd528849bbd5")
        self.assertEqual(GT_SHA,"bb62c320a51c1be412e17065eb86cfffa9041841290d439c23e447f1991aabdb")
if __name__=="__main__":
    unittest.main()
