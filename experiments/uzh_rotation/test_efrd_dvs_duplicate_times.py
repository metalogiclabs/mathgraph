"""Independent source identity and collision-preservation controls."""
import unittest
from audit_efrd_dvs_duplicate_times import classify_timed_imu

def obs(t,rate=1,raw=b"a",receipt=None):
    return (int(t),int(t if receipt is None else receipt),raw,(rate,0,0))

class DuplicateSourceControls(unittest.TestCase):
    def test_exact_repeat_only_when_raw_and_receipt_identical(self):
        data=classify_timed_imu([obs(1),obs(2),obs(2),obs(3)])
        self.assertEqual(data["state"],"EXACT_RETRANSMISSIONS_ONLY")
        self.assertEqual(data["byte_identical_same_receipt_extras"],1)
        self.assertEqual(data["conflicting_same_time_extras"],0)
        self.assertEqual(data["unique_timestamps"],3)
    def test_different_raw_same_time_must_remain_explicit_conflict(self):
        data=classify_timed_imu([obs(1),obs(2,1,b"a"),obs(2,3,b"b"),obs(3)])
        self.assertEqual(data["state"],"CONFLICTING_OR_UNVERIFIED_TIMESTAMP_COLLISIONS")
        self.assertEqual(data["conflicting_same_time_extras"],1)
        self.assertEqual(data["duplicate_groups"][0]["speed_spread_rad_s"],2)
        self.assertEqual(data["min_speed"][1],1)
        self.assertEqual(data["max_speed"][1],3)
        self.assertFalse(data["navigation_correction_authorized"])
    def test_same_raw_but_different_receipt_is_conflicting(self):
        data=classify_timed_imu([obs(1),obs(2),obs(2,receipt=5),obs(3)])
        self.assertEqual(data["conflicting_same_time_extras"],1)
    def test_no_duplicates_has_identical_min_max_curves(self):
        data=classify_timed_imu([obs(1,1),obs(2,2),obs(3,3)])
        self.assertEqual(data["same_time_extra_observations"],0)
        self.assertTrue((data["min_speed"]==data["max_speed"]).all())
    def test_reverse_times_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"reverse"):
            classify_timed_imu([obs(2),obs(1)])
    def test_nan_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"invalid"):
            classify_timed_imu([obs(1),obs(2,float("nan"))])
    def test_zero_source_fails(self):
        with self.assertRaisesRegex(ValueError,"insufficient"):
            classify_timed_imu([obs(1)])
    def test_duplicate_triple_retains_all_records(self):
        data=classify_timed_imu([obs(1),obs(2,1,b"a"),obs(2,2,b"b"),
                                 obs(2,3,b"c"),obs(3)])
        self.assertEqual(data["same_time_extra_observations"],2)
        self.assertEqual(data["original_messages"],5)
        self.assertEqual(data["duplicate_group_details"][0]["observations"],3)
if __name__=="__main__":
    unittest.main()
