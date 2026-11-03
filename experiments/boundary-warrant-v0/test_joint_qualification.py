"""Two method-specific admissions must share selective warrant withdrawal."""
from dataclasses import replace
import importlib.util
import os
from pathlib import Path
import unittest

from mathgraph_check.boundary_warrant import (
    admitted_route, resolve_boundaries, scope_identity,
)
from mathgraph_check.warrant_resolution import Receipt, compare_snapshots

HERE = Path(__file__).resolve().parent
L4_ADAPTER = HERE.parent / "check-l4-claim-consumer-v1" / "boundary_export.py"
REQUIRED_ENV = (
    "MATHGRAPH_L4_CLAIM_ARTIFACT_ZIP", "MATHGRAPH_BRAHE_ARTIFACT_ZIP",
    "MATHGRAPH_BRAHE_BASE_SOURCE", "MATHGRAPH_BRAHE_HEAD_SOURCE",
)


def _load_l4():
    spec = importlib.util.spec_from_file_location("qualified_l4_boundary_export", L4_ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def real_boundaries():
    """Never build the admitted receipts from an unexamined JSON status."""
    l4, l4_receipt, l4_assessment = _load_l4().export_l4_boundary(
        Path(os.environ["MATHGRAPH_L4_CLAIM_ARTIFACT_ZIP"]),
    )
    from brahe_export import export_brahe_boundary
    brahe, brahe_receipt, brahe_assessment = export_brahe_boundary(
        Path(os.environ["MATHGRAPH_BRAHE_ARTIFACT_ZIP"]),
        Path(os.environ["MATHGRAPH_BRAHE_BASE_SOURCE"]),
        Path(os.environ["MATHGRAPH_BRAHE_HEAD_SOURCE"]),
    )
    return ((l4, l4_receipt), (brahe, brahe_receipt)), (l4_assessment, brahe_assessment)


@unittest.skipUnless(all(os.environ.get(x) for x in REQUIRED_ENV),
                     "Requires both exact historical artifacts and pinned source blobs")
class CrossMethodAdmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items, cls.assessments = real_boundaries()
        cls.current = {dependency.key: dependency.sha256
                       for warrant, _ in cls.items for dependency in warrant.dependencies}
        cls.ids = [admitted_route(warrant, receipt)[0].id
                   for warrant, receipt in cls.items]

    def test_both_real_methods_close_only_at_their_bounded_scope(self):
        l4, brahe = [w for w, _ in self.items]
        self.assertEqual((l4.verification.method, brahe.verification.method),
                         ("formal", "native"))
        self.assertEqual(l4.verification.assumptions, ("propext",))
        self.assertEqual(brahe.obligation.authority,
                         "PR_TEST_DECLARED; NOT_CUSTOMER_APPROVED")
        self.assertEqual(self.assessments[0]["weak_offering"],
                         "REJECTED_AS_SUPPORT_FOR_STRONG_OBLIGATION")
        self.assertEqual(self.assessments[1]["base_failures"], 4)
        observed = resolve_boundaries(self.items, self.current)
        self.assertEqual(dict(observed.states), {
            self.ids[0]: "WARRANTED_BOUNDED",
            self.ids[1]: "WARRANTED_BOUNDED_NATIVE",
        })
        self.assertEqual(len(observed.active_routes), 2)

    def test_every_changed_dependency_selectively_withdraws_and_restores(self):
        before = resolve_boundaries(self.items, self.current)
        for idx, (warrant, _) in enumerate(self.items):
            for dependency in warrant.dependencies:
                with self.subTest(method=warrant.verification.method,
                                  dependency=dependency.key):
                    changed = dict(self.current)
                    changed[dependency.key] = "f" * 64 if dependency.sha256 != "f" * 64 else "e" * 64
                    after = resolve_boundaries(self.items, changed)
                    delta = compare_snapshots(before.states, after.states)
                    self.assertEqual(delta[self.ids[idx]]["after"], "STALE")
                    self.assertTrue(delta[self.ids[idx]]["changed"])
                    self.assertFalse(delta[self.ids[1-idx]]["changed"])
                    self.assertEqual(len(after.active_routes), 1)
                    restored = resolve_boundaries(self.items, self.current)
                    self.assertEqual(dict(restored.states), dict(before.states))

    def test_missing_authority_or_evidence_is_unknown_not_approved(self):
        for idx, (warrant, _) in enumerate(self.items):
            for role in ("obligation", "evidence"):
                key = next(d.key for d in warrant.dependencies if d.role == role)
                current = dict(self.current)
                current.pop(key)
                result = resolve_boundaries(self.items, current)
                self.assertEqual(result.states[self.ids[idx]], "UNKNOWN")
                self.assertNotEqual(result.states[self.ids[idx]], "WARRANTED_BOUNDED")
                self.assertEqual(result.states[self.ids[1-idx]],
                                 ("WARRANTED_BOUNDED_NATIVE", "WARRANTED_BOUNDED")[idx])

    def test_method_or_obligation_relabel_cannot_reuse_an_old_receipt(self):
        formal, formal_receipt = self.items[0]
        native, native_receipt = self.items[1]
        with self.assertRaisesRegex(ValueError, "UNADMITTED_RECEIPT"):
            admitted_route(formal, native_receipt)
        with self.assertRaisesRegex(ValueError, "UNADMITTED_RECEIPT"):
            admitted_route(native, formal_receipt)
        with self.assertRaisesRegex(ValueError, "UNADMITTED_RECEIPT"):
            admitted_route(formal, Receipt(formal_receipt.id, "native", scope_identity(formal)))
        with self.assertRaisesRegex(ValueError, "DEPENDENCY_IDENTITY_MISMATCH"):
            replace(formal, obligation=replace(formal.obligation, statement="P or True"))
        with self.assertRaisesRegex(ValueError, "DEPENDENCY_IDENTITY_MISMATCH"):
            replace(native, obligation=replace(native.obligation, authority="CUSTOMER_APPROVED"))

    def test_report_is_read_only_projection_of_qualified_graph_and_unknowns(self):
        from qualify import qualification_report
        report = qualification_report(self.items, self.assessments)
        self.assertEqual(report["format"], "mathgraph.boundary-qualification.v0")
        self.assertEqual(report["current_upstream_applicability"], "UNKNOWN")
        self.assertEqual(report["pinned_states"], {
            self.ids[0]: "WARRANTED_BOUNDED",
            self.ids[1]: "WARRANTED_BOUNDED_NATIVE",
        })
        self.assertEqual(len(report["warrants"]), 2)
        self.assertEqual({w["verification"]["method"] for w in report["warrants"]},
                         {"formal", "native"})
        self.assertEqual(report["warrants"][0]["verification"]["assumptions"],
                         ["propext"])
        self.assertEqual(report["warrants"][1]["obligation"]["authority"],
                         "PR_TEST_DECLARED; NOT_CUSTOMER_APPROVED")
        self.assertEqual(report["replay_evidence"]["brahe"]["base_failures"], 4)
        self.assertEqual(report["replay_evidence"]["brahe"]["head_failures"], 0)
        # These mutations are synthetic, not a claim about current upstream HEAD.
        self.assertEqual(len(report["simulated_withdrawals"]),
                         sum(len(w.dependencies) for w, _ in self.items))
        self.assertTrue(all(row["unaffected_still_admitted"]
                            for row in report["simulated_withdrawals"]))


if __name__ == "__main__":
    unittest.main()
