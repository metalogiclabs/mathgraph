"""Adversarial controls for ECRot one-column event/gyro replay."""

import math
import struct
import unittest

import numpy as np

from audit_ecrot_line_revisit import (
    accumulate_column_packet,
    decode_event_packet,
    gyro_integrated_phase,
    match_angular_map,
    sha256_file,
)


def packet_with_events(events):
    # Independent ROS1 wire serialization: Header, height, width, Event[].
    frame = b"sensor"
    head = struct.pack("<IIII", 1, 100, 10, len(frame)) + frame
    head += struct.pack("<III", 480, 640, len(events))
    return head + b"".join(struct.pack("<HHIIB", *ev) for ev in events)


class TestECRotWireAndGyro(unittest.TestCase):
    def test_raw_event_packet_matches_declared_ros1_layout(self):
        raw = packet_with_events([(320, 17, 100, 11, 1), (321, 479, 100, 12, 0)])
        height, width, events = decode_event_packet(raw)
        self.assertEqual((height, width), (480, 640))
        self.assertEqual(len(events), 2)
        self.assertEqual((int(events[0]["x"]), int(events[0]["y"])), (320, 17))
        self.assertEqual((int(events[1]["x"]), int(events[1]["p"])), (321, 0))
        self.assertEqual((int(events[0]["sec"]), int(events[0]["nsec"])), (100, 11))

    def test_wrong_event_packet_length_fails_closed(self):
        truncated = packet_with_events([(320, 17, 100, 11, 1)])[:-1]
        with self.assertRaisesRegex(ValueError, "payload"):
            decode_event_packet(truncated)

    def test_gyro_trapezoid_is_not_endpoint_rectangle(self):
        time = np.array([0., 1., 2.])
        velocity = np.array([0., 1., 0.])
        np.testing.assert_allclose(gyro_integrated_phase(time, velocity), [0., .5, 1.])

    def test_non_increasing_imu_time_rejected(self):
        with self.assertRaises(ValueError):
            gyro_integrated_phase(np.array([0., 1., 1.]), np.ones(3))


class TestVisualMatch(unittest.TestCase):
    def test_single_observed_map_sector_cannot_create_false_uniqueness(self):
        known = np.array([[10., 0.], [0., 0.], [0., 0.]])
        decision = match_angular_map(known, np.array([10., 0.]), min_events=5)
        self.assertEqual(decision["decision"], "UNKNOWN")

    def test_same_physical_column_first_cycle_frozen_from_later_revisit(self):
        events = decode_event_packet(packet_with_events([
            (320, 17, 100, 100000000, 1),
            (321, 17, 100, 100000000, 1),
            (320, 60, 101, 990000000, 0),
        ]))[2]
        first = np.zeros((64, 24, 2), dtype=np.int64)
        tail = np.zeros_like(first)
        t = np.array([100., 101., 102.])
        ph = np.array([0., math.pi, 2 * math.pi + .1])
        count = accumulate_column_packet(events, t, ph, first, tail)
        self.assertEqual(count["selected_column"], 2)
        self.assertEqual(count["valid_time"], 2)
        self.assertEqual(int(first[3, 0, 1]), 1)
        self.assertEqual(int(tail[0, 3, 0]), 1)
        self.assertEqual(int(first.sum()), 1)
        self.assertEqual(int(tail.sum()), 1)

    def test_events_outside_imu_timestamps_are_not_fabricated(self):
        events = decode_event_packet(packet_with_events([
            (320, 17, 99, 900000000, 1),
        ]))[2]
        first = np.zeros((64, 24, 2), dtype=np.int64)
        tail = np.zeros_like(first)
        count = accumulate_column_packet(events, np.array([100., 101.]),
                                         np.array([0., 2 * math.pi]), first, tail)
        self.assertEqual(count["selected_column"], 1)
        self.assertEqual(count["valid_time"], 0)
        self.assertEqual(int(first.sum() + tail.sum()), 0)

    def test_unique_sector_selected_without_gyro_label_as_input(self):
        known = np.array([[12., 0.], [0., 10.], [5., 5.]])
        tail = np.array([13., 0.])
        result = match_angular_map(known, tail, min_events=5)
        self.assertEqual(result["best_sector"], 0)
        self.assertGreater(result["margin"], 0.2)
        self.assertEqual(result["decision"], "CANDIDATE")

    def test_repeated_environment_is_unknown_not_confident(self):
        known = np.array([[10., 0.], [10., 0.], [0., 10.]])
        result = match_angular_map(known, np.array([10., 0.]), min_events=5)
        self.assertEqual(result["decision"], "UNKNOWN")
        self.assertEqual(result["competing_sectors"], [0, 1])

    def test_no_tail_observation_cannot_make_a_heading_correction(self):
        known = np.array([[10., 0.], [0., 10.]])
        result = match_angular_map(known, np.array([0., 0.]), min_events=5)
        self.assertEqual(result["decision"], "UNKNOWN")
        self.assertIsNone(result["best_sector"])

    def test_unique_but_low_margin_withholds(self):
        known = np.array([[10., 0.], [10., 1.]])
        result = match_angular_map(known, np.array([10., 0.]), min_events=5)
        self.assertEqual(result["decision"], "UNKNOWN")
        self.assertEqual(result["best_sector"], 0)

    def test_source_hash_is_computed_from_bytes(self):
        import hashlib
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temporary:
            file = Path(temporary) / "sample.bag"
            file.write_bytes(b"original sensor bytes")
            self.assertEqual(sha256_file(file), hashlib.sha256(file.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
