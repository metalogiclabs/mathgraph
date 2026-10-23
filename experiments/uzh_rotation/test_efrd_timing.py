"""Finite, independent positive and negative temporal-correlation controls."""
import math
import unittest
import numpy as np
from scipy.spatial.transform import Rotation
from qualify_efrd_timing import (
    mocap_angular_speed, frozen_offset_split, source_time_ns,
)

class TestEFRTiming(unittest.TestCase):
    def setup_data(self, lag=0., seconds=30):
        t = np.arange(0, seconds, 0.02)
        speed = 1. + 0.6*np.sin(3.7*t)**2 + 0.2*np.sin(0.53*t)**2
        a=(t*1e9).astype(np.int64)
        b=((t+lag)*1e9).astype(np.int64)
        return a,speed,b,speed

    def test_source_header_nanosecond_validation(self):
        class Fake:
            sec=5
            nanosec=123
        self.assertEqual(source_time_ns(Fake()),5000000123)
        Fake.nanosec=1000000000
        with self.assertRaises(ValueError):
            source_time_ns(Fake())

    def test_so3_speed_independent_of_rotation_axis(self):
        t=np.arange(600,dtype=np.int64)*10000000
        q=Rotation.from_euler("x",np.arange(600)*0.01).as_quat()
        _,speed=mocap_angular_speed(t,q)
        self.assertAlmostEqual(float(np.median(speed)),1.,places=5)

    def test_positive_45ms_lag_learned_before_validation(self):
        d=frozen_offset_split(*self.setup_data(lag=.045))
        self.assertEqual(d["status"],"CANDIDATE_WITHIN_RECORDING_LAG_TRANSFER")
        self.assertAlmostEqual(d["metrics"]["selected_lag_s"],.045,delta=.01)
        self.assertGreater(d["metrics"]["validation_frozen_lag_correlation"],
                           d["metrics"]["validation_zero_lag_correlation"])
        self.assertFalse(d["metrics"]["validation_used_for_selection"])

    def test_zero_lag_controls(self):
        d=frozen_offset_split(*self.setup_data(lag=0.))
        self.assertEqual(d["status"],"NO_VALIDATED_TIMING_ADVANTAGE")
        self.assertAlmostEqual(d["metrics"]["selected_lag_s"],0.,delta=.005)

    def test_flat_reference_fails_closed(self):
        a,_,b,_=self.setup_data()
        d=frozen_offset_split(a,np.ones(len(a)),b,np.ones(len(b)))
        self.assertEqual(d["status"],"UNKNOWN_UNINFORMATIVE_TRAINING")

    def test_disjoint_clocks_return_unknown_not_fitted_lag(self):
        a,ar,b,br=self.setup_data()
        d=frozen_offset_split(a,ar,b+100_000_000_000,br)
        self.assertEqual(d["status"],"UNKNOWN_NO_SUFFICIENT_COMMON_CLOCK")

    def test_duplicate_imu_times_refused(self):
        a,ar,b,br=self.setup_data()
        b[50]=b[49]
        with self.assertRaisesRegex(ValueError,"duplicate or reversed"):
            frozen_offset_split(a,ar,b,br)

    def test_negative_rate_refused(self):
        a,ar,b,br=self.setup_data()
        br[50]=-1.
        with self.assertRaises(ValueError):
            frozen_offset_split(a,ar,b,br)

    def test_nan_rate_refused(self):
        a,ar,b,br=self.setup_data()
        br[30]=float("nan")
        with self.assertRaises(ValueError):
            frozen_offset_split(a,ar,b,br)

    def test_bad_quaternion_refused(self):
        t=np.arange(600,dtype=np.int64)*10000000
        q=Rotation.from_euler("y",np.arange(600)*0.01).as_quat()
        q[3]*=2
        with self.assertRaisesRegex(ValueError,"norm"):
            mocap_angular_speed(t,q)

if __name__ == "__main__":
    unittest.main()
