"""Independent scalar oracle for the frozen joint bias/clock finite grid.

The oracle does NOT call the optimized joint feasibility function; it
enumerates each candidate and each acquired reading from source arrays.
Only synthetic readings are admitted. No physical navigation warrant.
"""
import math
import unittest
import numpy as np

from physical_joint_bias_clock_model import (
    make_capture, joint_feasible, BIAS_GRID, CLOCK_GRID, TAU, TOLERANCE
)

def scalar_oracle(c,ids):
    values=[]
    for delta in CLOCK_GRID:
        for bias in BIAS_GRID:
            valid=True
            for idx in ids:
                t=float(c.camera_times[idx])
                observed=float(c.camera_bearing[idx])
                integrated=float(np.interp(t,c.gyro_times,c.gyro_phase))
                visual=observed+TAU*round((integrated-observed)/TAU)
                expected=(float(np.interp(t+delta,c.gyro_times,c.gyro_phase))
                          -float(np.interp(delta,c.gyro_times,c.gyro_phase))
                          -bias*t)
                if abs(visual-expected)>TOLERANCE+1e-10:
                    valid=False
                    break
            values.append(valid)
    return np.asarray(values,dtype=bool).reshape(len(CLOCK_GRID),len(BIAS_GRID))

class IndependentGridOracleTests(unittest.TestCase):
    def test_all_grid_states_replayed_independently(self):
        readings=[0,8,16,24]
        for scenario in ("steady","varying","varying_clock_shift"):
            cap=make_capture(2,scenario)
            independently=scalar_oracle(cap,readings)
            optimized=joint_feasible(cap,readings)
            self.assertTrue(np.array_equal(independently,optimized))
            self.assertTrue(independently.any())

    def test_corrupted_camera_excludes_every_strict_joint_state(self):
        cap=make_capture(0,"varying_outliers")
        readings=[0,8,16,24,32,40,48]
        self.assertFalse(scalar_oracle(cap,readings).any())
        self.assertFalse(joint_feasible(cap,readings).any())

if __name__=="__main__":
    unittest.main()
