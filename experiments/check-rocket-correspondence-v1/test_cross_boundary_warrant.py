"""Common-mode source-warrant controls, not a test of FGM/PKC or native R2U2.

Synthetic executable verdicts are intentionally assumed to agree perfectly with
the formalized candidate. That internal agreement cannot prove correspondence
to the actual frozen FRETish export, much less owner-approved mission purpose.
All receipts constructed here are synthetic resolver fixtures, NOT authenticated
execution evidence.
"""
import unittest

from rocket_profile import oracle_at
from mathgraph_check.warrant_resolution import Claim, Receipt, Route, resolve_graph


def trace(*, boost=0, coast=0):
    return [{"BOOST": int(i == boost), "COAST": int(i == coast)}
            for i in range(8)]


def values(t, lower):
    return tuple(oracle_at(t, i, lower) for i in range(8))


class RocketCommonModeControls(unittest.TestCase):
    def test_models_and_emulated_program_agree_but_external_source_does_not(self):
        t = trace(boost=0, coast=0)
        # The reference is the source-only FRETish-exported [0,7] formula.
        # It is NOT an authority about real sounding-rocket mission intent.
        source = values(t, 0)
        model = values(t, 1)
        emulated_program = values(t, 1)  # NOT a compiled R2U2 binary.
        self.assertEqual(model, emulated_program)
        self.assertNotEqual(source, model)
        self.assertEqual((source[0], model[0]), (True, False))
        self.assertEqual([i for i in range(8) if source[i] != model[i]], [0])
        # A strong, equally informed direct source/model comparison ties this.
        self.assertEqual(any(a != b for a, b in zip(source, model)), True)

    def test_aligned_source_model_and_emulation_has_no_finite_difference(self):
        t = trace(boost=0, coast=0)
        source, model, emulator = values(t, 0), values(t, 0), values(t, 0)
        self.assertEqual(source, model)
        self.assertEqual(model, emulator)
        # An observed finite match is not a universal MLTL theorem or release.

    def test_one_positive_control_does_not_establish_universal_equivalence(self):
        next_tick = trace(boost=0, coast=1)
        self.assertEqual(values(next_tick, 0)[0], values(next_tick, 1)[0])
        simultaneous = trace(boost=0, coast=0)
        self.assertNotEqual(values(simultaneous, 0)[0],
                            values(simultaneous, 1)[0])

    def test_no_trigger_is_benign_not_a_false_defect(self):
        absent = trace(boost=-1, coast=-1)
        self.assertEqual(values(absent, 0), values(absent, 1))
        self.assertEqual(values(absent, 0), (True,) * 8)

    def test_native_observation_is_not_owner_authorized_documentary_evidence(self):
        purpose = Claim("rocket-operational-purpose", "documentary",
                        "mission-owner-revision-UNKNOWN")
        receipt = Receipt("synthetic-finite-run", "native", "rocket-eight-tick-v1")
        with self.assertRaisesRegex(ValueError, "CROSS_BOUNDARY_EVIDENCE_WITHOUT_BRIDGE"):
            resolve_graph([purpose], [Route(purpose.id, (receipt.id,))], [receipt])

    def test_native_receipt_is_confined_to_exact_native_scope(self):
        claim = Claim("finite-native-observation", "native", "rocket-eight-tick-v1")
        receipt = Receipt("synthetic-finite-run", "native", "rocket-eight-tick-v1")
        # Resolver is a pure closure engine; trusted *admission* is external.
        # Passing a synthetic Receipt here is NOT a genuine native warrant.
        result = resolve_graph([claim], [Route(claim.id, (receipt.id,))], [receipt])
        self.assertEqual(result.states[claim.id], "WARRANTED_BOUNDED_NATIVE")

    def test_source_change_withdraws_only_under_the_supplied_receipt_policy(self):
        claim = Claim("finite-native-observation", "native", "rocket-eight-tick-v1")
        receipt = Receipt("synthetic-finite-run", "native", "rocket-eight-tick-v1")
        result = resolve_graph([claim], [Route(claim.id, (receipt.id,))],
                               [receipt], withdrawn=frozenset({receipt.id}))
        self.assertEqual(result.states[claim.id], "UNKNOWN")

    def test_same_status_name_cannot_cross_source_scope(self):
        claim = Claim("finite-native-observation", "native", "rocket-eight-tick-v1")
        receipt = Receipt("PASSED-success-synthetic", "native", "other-source-scope")
        with self.assertRaisesRegex(ValueError, "CROSS_BOUNDARY_EVIDENCE_WITHOUT_BRIDGE"):
            resolve_graph([claim], [Route(claim.id, (receipt.id,))], [receipt])


if __name__ == "__main__":
    unittest.main()
