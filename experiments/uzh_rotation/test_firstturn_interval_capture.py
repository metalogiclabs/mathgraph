"""Independent finite oracle for a first-turn gyro-interval capture adapter.

The oracle enumerates every admissible physical camera phase. It does not use
the C implementation's interval-endpoint shortcut.
"""

import ctypes
from pathlib import Path
import subprocess
import tempfile
import unittest

from audit_finite_partial_map import Map


HERE = Path(__file__).parent
TICKS_PER_TURN = 1024
TICKS_PER_BIN = 16


class FirstTurnIntervalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="mathgraph-firstturn-bound-")
        so = Path(cls.tmp.name) / "libbound.so"
        subprocess.run(
            ["gcc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-O2",
             "-fPIC", "-shared", str(HERE / "firstturn_interval_capture.c"),
             str(HERE / "finite_partial_map.c"),
             str(HERE / "finite_jitter_embedded.c"), "-o", str(so)],
            capture_output=True, text=True, check=True,
        )
        cls.native = ctypes.CDLL(str(so))
        cls.native.mg_map_init.argtypes = [ctypes.POINTER(Map)]
        cls.native.mg_map_freeze.argtypes = [ctypes.POINTER(Map)]
        cls.native.mg_firstturn_capture_interval.argtypes = [
            ctypes.POINTER(Map), ctypes.c_uint16, ctypes.c_uint16,
            ctypes.c_uint16,
        ]
        cls.native.mg_firstturn_capture_interval.restype = ctypes.c_int

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def attempt(self, estimated, radius, column=0x1234):
        record = Map()
        self.native.mg_map_init(ctypes.byref(record))
        result = self.native.mg_firstturn_capture_interval(
            ctypes.byref(record), estimated, radius, column,
        )
        return result, record

    def test_exhaustive_interval_agrees_with_enumerated_physical_angles(self):
        # Exhaustive over 1024 reported phases and exact integer uncertainty
        # sets, including the wrap between bins 63 and 0.
        for radius in (0, 1, 2, 3, 7, 8, 15, 16):
            for phase in range(TICKS_PER_TURN):
                possible = {
                    ((phase + shift) % TICKS_PER_TURN) // TICKS_PER_BIN
                    for shift in range(-radius, radius + 1)
                }
                status, record = self.attempt(phase, radius)
                if len(possible) == 1:
                    known_bin = next(iter(possible))
                    self.assertEqual(status, 0, (phase, radius))
                    self.assertEqual(record.count, 1)
                    self.assertEqual(record.columns[known_bin], 0x1234)
                    self.assertTrue(record.seen[known_bin // 8] &
                                    (1 << (known_bin % 8)))
                else:
                    self.assertEqual(status, 2, (phase, radius))
                    self.assertEqual(record.count, 0)
                    self.assertEqual(list(record.seen), [0] * 8)

    def test_exact_bin_boundaries_duplicates_and_freeze(self):
        record = Map()
        self.native.mg_map_init(ctypes.byref(record))
        capture = self.native.mg_firstturn_capture_interval
        self.assertEqual(capture(ctypes.byref(record), 8, 7, 0x1234), 0)
        self.assertEqual(capture(ctypes.byref(record), 8, 7, 0x1235), 1)
        self.assertEqual(capture(ctypes.byref(record), 8, 7, 0xFFFF), -2)
        self.assertEqual(record.count, 0)
        self.assertEqual(capture(ctypes.byref(record), 8, 7, 0x1234), -2)
        self.assertEqual(capture(ctypes.byref(record), 16, 1, 0x5678), 2)
        self.assertEqual(capture(ctypes.byref(record), 0, 1, 0x5678), 2)
        self.assertEqual(capture(ctypes.byref(record), 1023, 1, 0x5678), 2)
        self.assertEqual(capture(ctypes.byref(record), 1024, 0, 0), -1)
        self.assertEqual(self.native.mg_map_freeze(ctypes.byref(record)), 0)
        self.assertEqual(capture(ctypes.byref(record), 24, 0, 0), -1)

    def test_declared_radius_is_not_self_authenticating(self):
        # Deliberately violating source bound: physical angle is in bin 1,
        # sensor reports bin-0 center + a FALSE +/-2 tick guarantee.
        result, record = self.attempt(8, 2, 0x9999)
        self.assertEqual(result, 0)
        self.assertEqual(record.count, 1)
        self.assertEqual(record.columns[0], 0x9999)
        self.assertNotEqual(0, (8 + 16) // 16)


if __name__ == "__main__":
    unittest.main()
