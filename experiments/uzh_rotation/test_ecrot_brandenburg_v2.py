"""Independent small-control audit for exact retransmission vs clock collision."""
import math
import unittest
from audit_ecrot_brandenburg_v2 import qualify_imu


def record(stamp, gyro=1., payload=b"one", bag=None):
    return (stamp, stamp if bag is None else bag, payload, (0.,gyro,0.))

class ExactChronologyTests(unittest.TestCase):
    def test_exact_duplicate_same_raw_message_is_only_allowed_collapse(self):
        rows=[record(0),record(1000000000),record(1000000000),record(2000000000)]
        got=qualify_imu(rows)
        self.assertEqual(got["exact_retransmissions"],1)
        self.assertEqual(got["clock_collisions"],0)
        self.assertEqual(got["unique_imu_samples"],3)
        self.assertEqual(got["status"],"INSUFFICIENT_FIRST_REVOLUTION")
        self.assertAlmostEqual(got["gyro_y_turns"],2/(2*math.pi))
        self.assertFalse(got["heading_correction_authorized"])
    def test_different_payload_with_same_time_must_not_be_dropped(self):
        got=qualify_imu([record(0),record(0,payload=b"different"),record(1)])
        self.assertEqual(got["status"],"AMBIGUOUS_IMU_TIMESTAMP")
        self.assertEqual(got["clock_collisions"],1)
        self.assertIsNone(got["gyro_y_turns"])
    def test_bag_time_change_blocks_timestamp_dedup(self):
        got=qualify_imu([record(0),record(0,bag=1),record(1)])
        self.assertEqual(got["status"],"AMBIGUOUS_IMU_TIMESTAMP")
    def test_backward_time_is_not_sorted_or_integrated(self):
        got=qualify_imu([record(1),record(0),record(2)])
        self.assertEqual(got["status"],"INVALID_IMU_CHRONOLOGY")
        self.assertIsNone(got["gyro_y_turns"])
    def test_nan_rate_is_rejected(self):
        got=qualify_imu([record(0,gyro=float("nan")),record(1)])
        self.assertEqual(got["status"],"INVALID_SOURCE_RECORD")
    def test_full_gyro_turn_never_authorizes_heading(self):
        # Physical gyro proxy in this test is an input, not external GT.
        rows=[record(i*1000000000, gyro=2*math.pi/8,payload=bytes([i]))
              for i in range(9)]
        got=qualify_imu(rows)
        self.assertEqual(got["status"],"ELIGIBLE_FOR_SEPARATE_VISUAL_REPLAY_ONLY")
        self.assertFalse(got["heading_correction_authorized"])
        self.assertFalse(got["first_turn_map_populated"])
    def test_partial_gyro_turn_abstains(self):
        rows=[record(i*1000000000, gyro=0.9*2*math.pi/8,payload=bytes([i]))
              for i in range(9)]
        got=qualify_imu(rows)
        self.assertEqual(got["status"],"INSUFFICIENT_FIRST_REVOLUTION")
        self.assertFalse(got["estimated_map_turn_complete"])
    def test_no_messages_abstains(self):
        self.assertEqual(qualify_imu([])["status"],"INSUFFICIENT_IMU")
if __name__=="__main__":
    unittest.main()
