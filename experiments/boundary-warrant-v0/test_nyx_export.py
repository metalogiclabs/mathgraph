"""Pinned Nyx #613 native evidence must qualify before graph admission."""
from dataclasses import replace
import os
from pathlib import Path
import subprocess
import unittest

from mathgraph_check.boundary_warrant import (
    admitted_route, scope_identity, BoundaryWarrant, Subject, Obligation,
    Relation, Verification, Conclusion, required_dependencies,
)
from mathgraph_check.warrant_resolution import Receipt
from nyx_export import ARTIFACT_SHA256, BASE_SHA, HEAD_SHA, export_nyx_boundary
from qualify import _l4_adapter, qualification_report
from brahe_export import export_brahe_boundary


class ThreeBoundaryProjection(unittest.TestCase):
    def test_three_inputs_use_same_graph_and_simulate_independent_withdrawal(self):
        """These synthetic receipts test graph mechanics, not evidence authenticity."""
        warrants = []
        for suffix, method in (("l4", "formal"), ("brahe", "native"), ("nyx", "native")):
            subject = Subject("test/" + suffix, "a" * 40, "b" * 64)
            obligation = Obligation(suffix, "P", "PR_AUTHOR_DECLARED", "c" * 64)
            relation = Relation("test_consistency", "producer satisfies P")
            verification = Verification(method, suffix + "-verifier", "d" * 64,
                                        (), "receipt:" + suffix)
            warrant = BoundaryWarrant(subject, obligation, relation, verification,
                                      Conclusion("SUPPORTED", ("test fixture only",)),
                                      required_dependencies(subject, obligation,
                                                            relation, verification))
            warrants.append(warrant)
        assessments = ({"weak_offering": "REJECTED_AS_SUPPORT_FOR_STRONG_OBLIGATION",
                        "axiom_free_claim": "UNKNOWN", "whole_generator_correctness": "UNKNOWN"},
                       {"base_failures": 4, "head_failures": 0},
                       {"base_failures": 1, "head_failures": 0})
        items = [(w, Receipt(w.verification.receipt_id, w.verification.method,
                             scope_identity(w))) for w in warrants]
        report = qualification_report(items, assessments)
        self.assertEqual(report["format"], "mathgraph.boundary-qualification.v1")
        self.assertEqual(len(report["warrants"]), 3)
        self.assertEqual(report["replay_evidence"]["nyx"]["base_failures"], 1)
        self.assertEqual(len(report["simulated_withdrawals"]),
                         sum(len(w.dependencies) for w in warrants))
        self.assertTrue(all(row["unaffected_still_admitted"]
                            for row in report["simulated_withdrawals"]))


SOURCE_FILE_ENVS = (
    "MATHGRAPH_NYX_BASE_EVENT", "MATHGRAPH_NYX_HEAD_EVENT",
    "MATHGRAPH_NYX_BASE_TEST", "MATHGRAPH_NYX_HEAD_TEST",
)


def pinned_nyx_sources():
    if all(os.environ.get(key) for key in SOURCE_FILE_ENVS):
        return {
            "base_event": Path(os.environ["MATHGRAPH_NYX_BASE_EVENT"]).read_bytes(),
            "head_event": Path(os.environ["MATHGRAPH_NYX_HEAD_EVENT"]).read_bytes(),
            "base_test": Path(os.environ["MATHGRAPH_NYX_BASE_TEST"]).read_bytes(),
            "head_test": Path(os.environ["MATHGRAPH_NYX_HEAD_TEST"]).read_bytes(),
        }
    repo = os.environ["MATHGRAPH_NYX_CLONE_PATH"]
    def blob(ref, path):
        return subprocess.check_output(["git", "-C", repo, "show", ref + ":" + path])
    return {
        "base_event": blob(BASE_SHA, "nyx-core/src/propagators/event.rs"),
        "head_event": blob(HEAD_SHA, "nyx-core/src/propagators/event.rs"),
        "base_test": blob(BASE_SHA, "nyx-core/tests/propagation/stopcond.rs"),
        "head_test": blob(HEAD_SHA, "nyx-core/tests/propagation/stopcond.rs"),
    }


@unittest.skipUnless(os.environ.get("MATHGRAPH_NYX_ARTIFACT_ZIP")
                     and (os.environ.get("MATHGRAPH_NYX_CLONE_PATH")
                          or all(os.environ.get(key) for key in SOURCE_FILE_ENVS)),
                     "Requires pinned native artifact and exact Nyx source bytes")
class PinnedNyxExport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = Path(os.environ["MATHGRAPH_NYX_ARTIFACT_ZIP"]).read_bytes()
        cls.sources = pinned_nyx_sources()

    def test_pinned_native_logs_and_source_admit_bounded_one_test(self):
        from hashlib import sha256
        self.assertEqual(sha256(self.raw).hexdigest(), ARTIFACT_SHA256)
        warrant, receipt, assessment = export_nyx_boundary(self.raw, **self.sources)
        self.assertEqual(warrant.verification.method, "native")
        self.assertEqual(warrant.obligation.authority,
                         "PR_TEST_DECLARED; NOT_CUSTOMER_APPROVED")
        self.assertEqual(warrant.subject.revision, HEAD_SHA)
        self.assertEqual(assessment["base_failures"], 1)
        self.assertEqual(assessment["head_failures"], 0)
        self.assertEqual(assessment["independent_owner_authority"], "UNKNOWN")
        self.assertEqual(admitted_route(warrant, receipt)[0].id,
                         "boundary:" + scope_identity(warrant))

    def test_modified_artifact_or_source_cannot_admit(self):
        with self.assertRaisesRegex(ValueError, "ARTIFACT_IDENTITY_MISMATCH"):
            export_nyx_boundary(self.raw + b"unexpected", **self.sources)
        with self.assertRaisesRegex(ValueError, "SOURCE_IDENTITY_MISMATCH"):
            export_nyx_boundary(self.raw, **{
                **self.sources, "head_event": self.sources["head_event"] + b"\n",
            })
        with self.assertRaisesRegex(ValueError, "SOURCE_IDENTITY_MISMATCH"):
            export_nyx_boundary(self.raw, **{
                **self.sources, "head_test": self.sources["head_test"] + b"\n",
            })

    def test_forged_customer_authority_cannot_reuse_qualified_receipt(self):
        warrant, receipt, _ = export_nyx_boundary(self.raw, **self.sources)
        with self.assertRaisesRegex(ValueError, "DEPENDENCY_IDENTITY_MISMATCH"):
            replace(warrant, obligation=replace(warrant.obligation,
                                                 authority="CUSTOMER_APPROVED"))
        from mathgraph_check.boundary_warrant import required_dependencies
        changed = replace(warrant.obligation, authority="CUSTOMER_APPROVED")
        fake = replace(warrant, obligation=changed, dependencies=required_dependencies(
            warrant.subject, changed, warrant.relation, warrant.verification,
        ) + tuple(d for d in warrant.dependencies if d.role == "evidence"))
        with self.assertRaisesRegex(ValueError, "UNADMITTED_RECEIPT"):
            admitted_route(fake, Receipt(receipt.id, receipt.kind, receipt.scope))


REQUIRED_JOINT_ENV = (
    "MATHGRAPH_L4_CLAIM_ARTIFACT_ZIP", "MATHGRAPH_BRAHE_ARTIFACT_ZIP",
    "MATHGRAPH_BRAHE_BASE_SOURCE", "MATHGRAPH_BRAHE_HEAD_SOURCE",
    "MATHGRAPH_NYX_ARTIFACT_ZIP",
)


@unittest.skipUnless(all(os.environ.get(key) for key in REQUIRED_JOINT_ENV)
                     and (os.environ.get("MATHGRAPH_NYX_CLONE_PATH")
                          or all(os.environ.get(key) for key in SOURCE_FILE_ENVS)),
                     "Requires all three exact historical artifacts and source files")
class PinnedThreeBoundaryAdmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        l4 = _l4_adapter().export_l4_boundary(
            Path(os.environ["MATHGRAPH_L4_CLAIM_ARTIFACT_ZIP"]))
        brahe = export_brahe_boundary(
            Path(os.environ["MATHGRAPH_BRAHE_ARTIFACT_ZIP"]),
            Path(os.environ["MATHGRAPH_BRAHE_BASE_SOURCE"]),
            Path(os.environ["MATHGRAPH_BRAHE_HEAD_SOURCE"]),
        )
        nyx = export_nyx_boundary(
            Path(os.environ["MATHGRAPH_NYX_ARTIFACT_ZIP"]).read_bytes(),
            **pinned_nyx_sources(),
        )
        cls.items = tuple((w, receipt) for w, receipt, _ in (l4, brahe, nyx))
        cls.assessments = tuple(assessment for _, _, assessment in (l4, brahe, nyx))

    def test_three_real_boundaries_share_selective_withdrawal_and_restore(self):
        report = qualification_report(self.items, self.assessments)
        self.assertEqual(report["format"], "mathgraph.boundary-qualification.v1")
        self.assertEqual(report["scope"], "RETROSPECTIVE_BOUNDED_ONLY")
        self.assertEqual(report["independent_customer_obligation_authority"], "UNKNOWN")
        self.assertEqual([w["verification"]["method"] for w in report["warrants"]],
                         ["formal", "native", "native"])
        self.assertEqual(report["warrants"][0]["verification"]["assumptions"], ["propext"])
        self.assertEqual(report["replay_evidence"]["l4yaml"]["axiom_free_claim"],
                         "REJECTED")
        self.assertEqual(report["replay_evidence"]["l4yaml"]["whole_generator_correctness"],
                         "UNKNOWN")
        self.assertEqual(report["replay_evidence"]["nyx"]["base_failures"], 1)
        self.assertEqual(report["replay_evidence"]["nyx"]["head_failures"], 0)
        self.assertEqual(len(report["simulated_withdrawals"]), 20)
        self.assertTrue(all(row["unaffected_still_admitted"]
                            for row in report["simulated_withdrawals"]))


if __name__ == "__main__":
    unittest.main()
