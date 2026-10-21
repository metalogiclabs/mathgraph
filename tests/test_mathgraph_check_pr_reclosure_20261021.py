"""Exact-head PR warrant reclosure: bounded regression tests.

Receipt objects are *not* independently authenticated by this resolver.
All outcomes are conditional on external admission of evidence.
"""
import unittest

from mathgraph_check.warrant_resolution import (
    Claim, Receipt, Route, QualifiedRelation, resolve_graph, compare_snapshots
)


SCOPE = "owned/pr-20@0123456789abcdef"
OTHER = "owned/independent@abcdef0123456789"


def fixture():
    claims = [
        Claim("unit", "formal", SCOPE),
        Claim("integration", "formal", SCOPE),
        Claim("merge_candidate", "formal", SCOPE),
        Claim("unrelated", "formal", OTHER),
    ]
    receipts = [
        Receipt("unit_ci", "formal", SCOPE),
        Receipt("integration_ci", "formal", SCOPE),
        Receipt("alternate_integration", "formal", SCOPE),
        Receipt("policy_review", "formal", SCOPE),
        Receipt("other_ci", "formal", OTHER),
    ]
    routes = [
        Route("unit", ("unit_ci",)),
        Route("integration", ("integration_ci",), ("unit",)),
        Route("integration", ("alternate_integration",)),
        Route("merge_candidate", ("policy_review",), ("integration",)),
        Route("unrelated", ("other_ci",)),
    ]
    return claims, receipts, routes


class PRReclosure(unittest.TestCase):
    def resolve(self, withdrawn=frozenset(), *, routes=None):
        claims, receipts, default_routes = fixture()
        return resolve_graph(claims, default_routes if routes is None else routes,
                             receipts, withdrawn=withdrawn)

    def test_exact_withdrawal_preserves_unrelated_and_alternative(self):
        before = self.resolve()
        after = self.resolve(frozenset({"unit_ci", "alternate_integration"}))
        delta = compare_snapshots(before.states, after.states)
        self.assertEqual(delta["unit"]["after"], "STALE")
        self.assertEqual(delta["integration"]["after"], "STALE")
        self.assertEqual(delta["merge_candidate"]["after"], "STALE")
        self.assertEqual(delta["unrelated"]["after"], "WARRANTED_BOUNDED")
        self.assertFalse(delta["unrelated"]["changed"])

    def test_alternate_support_survives_primary_withdrawal(self):
        states = self.resolve(frozenset({"unit_ci"})).states
        self.assertEqual(states["unit"], "UNKNOWN")
        self.assertEqual(states["integration"], "WARRANTED_BOUNDED")
        self.assertEqual(states["merge_candidate"], "WARRANTED_BOUNDED")

    def test_restoration_is_exact(self):
        original = dict(self.resolve().states)
        lost = self.resolve(frozenset({"unit_ci", "alternate_integration"}))
        self.assertEqual(lost.states["merge_candidate"], "UNKNOWN")
        restored = dict(self.resolve().states)
        self.assertEqual(original, restored)

    def test_revoking_final_policy_blocks_merge_only(self):
        states = self.resolve(frozenset({"policy_review"})).states
        self.assertEqual(states["merge_candidate"], "UNKNOWN")
        self.assertEqual(states["integration"], "WARRANTED_BOUNDED")
        self.assertEqual(states["unrelated"], "WARRANTED_BOUNDED")

    def test_unrooted_cycle_never_creates_authority(self):
        scope = SCOPE
        claims = [Claim("a", "formal", scope), Claim("b", "formal", scope)]
        receipts = [Receipt("w", "formal", scope)]
        routes = [Route("a", ("w",), ("b",)), Route("b", ("w",), ("a",))]
        states = resolve_graph(claims, routes, receipts).states
        self.assertEqual(dict(states), {"a": "UNKNOWN", "b": "UNKNOWN"})

    def test_cross_revision_evidence_fails_closed(self):
        claims = [Claim("merged", "formal", SCOPE)]
        receipts = [Receipt("old_ci", "formal", "owned/pr-20@OLD_HEAD")]
        with self.assertRaisesRegex(ValueError, "CROSS_BOUNDARY"):
            resolve_graph(claims, [Route("merged", ("old_ci",))], receipts)

    def test_unknown_withdrawal_target_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "UNKNOWN_WITHDRAWAL_TARGET"):
            self.resolve(frozenset({"invented_receipt"}))

    def test_documentary_claim_cannot_become_formal_without_bridge(self):
        claims = [Claim("theorem", "formal", SCOPE)]
        receipts = [Receipt("review_text", "documentary", SCOPE)]
        with self.assertRaisesRegex(ValueError, "CROSS_BOUNDARY"):
            resolve_graph(claims, [Route("theorem", ("review_text",))], receipts)

    def test_bridge_requires_exact_route_and_qualified_verifier(self):
        claim = Claim("formal_admission", "formal", SCOPE)
        receipt = Receipt("outside_report", "documentary", OTHER)
        verifier = Receipt("relation_proof", "formal", SCOPE)
        target_evidence = Receipt("target_scope", "formal", SCOPE)
        route = Route("formal_admission", ("outside_report",),
                      relation="specific_adapter")
        bridge = QualifiedRelation(
            "specific_adapter", "documentary", OTHER, "formal", SCOPE,
            "relation_proof", ("target_scope",), route)
        result = resolve_graph([claim], [route],
                               [receipt, verifier, target_evidence],
                               relations=[bridge])
        self.assertEqual(result.states["formal_admission"], "WARRANTED_BOUNDED")
        lost = resolve_graph([claim], [route],
                             [receipt, verifier, target_evidence],
                             relations=[bridge],
                             withdrawn=frozenset({"relation_proof"}))
        self.assertEqual(lost.states["formal_admission"], "UNKNOWN")
        changed_route = Route("formal_admission", ("outside_report",),
                              premises=(), relation=None)
        with self.assertRaisesRegex(ValueError, "CROSS_BOUNDARY"):
            resolve_graph([claim], [changed_route],
                          [receipt, verifier, target_evidence],
                          relations=[bridge])


if __name__ == "__main__":
    unittest.main()
