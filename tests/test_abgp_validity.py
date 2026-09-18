import unittest

from mathgraph.abgp.validity import validate_arm_input


class ABGPValidityTests(unittest.TestCase):
    def test_p_verifier_access_is_protocol_invalidity(self):
        issues = validate_arm_input(
            "P",
            {
                "hard_gates": {
                    "zero_verifier": False,
                    "zero_search": True,
                    "label_free": True,
                    "source_distinct": True,
                    "targeted_deletion": True,
                }
            },
        )
        self.assertEqual(
            tuple(issue.code for issue in issues),
            ("P_FUTURE_VERIFIER_ACCESS",),
        )

    def test_p_failed_targeted_deletion_is_not_protocol_invalidity(self):
        issues = validate_arm_input(
            "P",
            {
                "hard_gates": {
                    "zero_verifier": True,
                    "zero_search": True,
                    "label_free": True,
                    "source_distinct": True,
                    "targeted_deletion": False,
                }
            },
        )
        self.assertEqual(issues, ())

    def test_unknown_arm_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown ABGP arm"):
            validate_arm_input("X", {"hard_gates": {}})


if __name__ == "__main__":
    unittest.main()
