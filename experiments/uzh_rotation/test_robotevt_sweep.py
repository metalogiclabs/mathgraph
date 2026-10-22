"""Independent controls for the RobotEvt angular-sweep admission gate."""

import unittest

import numpy as np

from audit_robotevt_sweep import classify_trajectory


def z_rotation(angles):
    """Analytic one-axis rotation, independent of the implementation."""
    angles = np.asarray(angles)
    out = np.zeros((len(angles), 3, 3))
    out[:, 0, 0] = out[:, 1, 1] = np.cos(angles)
    out[:, 0, 1] = -np.sin(angles)
    out[:, 1, 0] = np.sin(angles)
    out[:, 2, 2] = 1
    return out


def x_rotation(angles):
    out = np.zeros((len(angles), 3, 3))
    out[:, 0, 0] = 1
    out[:, 1, 1] = out[:, 2, 2] = np.cos(angles)
    out[:, 1, 2] = -np.sin(angles)
    out[:, 2, 1] = np.sin(angles)
    return out


class TestSweepQualification(unittest.TestCase):
    def classify(self, matrices):
        return classify_trajectory(np.arange(len(matrices), dtype=float) / 100, matrices)

    def test_three_full_turns_admitted_despite_wrapping(self):
        result = self.classify(z_rotation(np.linspace(0, 6 * np.pi, 2401)))
        self.assertEqual(result["admission"], "ADMITTED")
        self.assertAlmostEqual(result["longest_directional_streak_turns"], 3, places=4)
        self.assertAlmostEqual(result["yaw_excursion_turns"], 3, places=4)
        self.assertLessEqual(result["axis_aligned_path_fraction"], 1.0)

    def test_many_partial_sweeps_have_large_path_but_no_full_turn(self):
        angles = 0.8 * np.pi * np.sin(np.linspace(0, 10 * np.pi, 2401))
        result = self.classify(z_rotation(angles))
        self.assertGreater(result["absolute_yaw_path_turns"], 6)
        self.assertAlmostEqual(result["yaw_excursion_turns"], 0.8, places=3)
        self.assertLess(result["longest_directional_streak_turns"], 0.81)
        self.assertEqual(result["admission"], "REJECTED")

    def test_one_complete_revolution_does_not_satisfy_two_turn_gate(self):
        result = self.classify(z_rotation(np.linspace(0, 2 * np.pi, 801)))
        self.assertEqual(result["admission"], "REJECTED")

    def test_full_x_rotation_does_not_get_mislabeled_as_z_spinning(self):
        result = self.classify(x_rotation(np.linspace(0, 6 * np.pi, 2401)))
        self.assertLess(result["axis_aligned_path_fraction"], 0.05)
        self.assertEqual(result["admission"], "UNKNOWN")

    def test_sampling_alias_blocks_acceptance_even_if_phase_looks_good(self):
        result = self.classify(z_rotation(np.linspace(0, 6 * np.pi, 11)))
        self.assertEqual(result["admission"], "UNKNOWN")
        self.assertFalse(result["sampling_admissible"])

    def test_slow_small_reverse_jitter_is_not_a_turn_break(self):
        angles = np.linspace(0, 6 * np.pi, 2401)
        angles[1000] -= np.deg2rad(0.55)
        result = self.classify(z_rotation(angles))
        self.assertEqual(result["admission"], "ADMITTED")

    def test_bad_rotation_matrix_is_rejected(self):
        matrices = z_rotation(np.linspace(0, 2 * np.pi, 101))
        matrices[50, 0, 0] = 2
        with self.assertRaises(ValueError):
            self.classify(matrices)

    def test_non_increasing_timestamps_rejected(self):
        matrices = z_rotation(np.linspace(0, 2 * np.pi, 101))
        with self.assertRaises(ValueError):
            classify_trajectory(np.zeros(len(matrices)), matrices)


if __name__ == "__main__":
    unittest.main()
