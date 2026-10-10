"""Conservative living-warrant graph: source-pin and adversarial controls."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from mathgraph_check.living_warrants import (
    Claim, Receipt, Route, OPENAI_HEAD, OPENAI_HISTORY_BLOB,
    WITHDRAWN_TITLES, JPL_CLAIM, JPL_SCOPE, JPL_RECEIPT,
    build_snapshot, canonical, compare_snapshots, git_blob_sha1,
    read_withdrawals, reclose, render_html, verify_snapshot, write_snapshot
)
from mathgraph_check.public_receipts import (
    RECORD_ID as JPL_RECORD_ID, EXPECTED_RECORD_SHA256,
    build_record
)


class GraphSemanticsTests(unittest.TestCase):
    def test_synthetic_conjunctive_dependency_invalidates_only_descendants(self):
        scope = "synthetic.formal.scope@1"
        cs = [Claim(x, "formal", scope) for x in "ABC"]
        rs = [Receipt(x, "formal", scope) for x in "rstu"]
        routes = [Route("A", ("r",)), Route("A", ("s",)),
                  Route("B", ("t",), ("A",)), Route("C", ("u",))]
        initial = reclose(cs, routes, rs)
        self.assertEqual(list(initial.values()), ["WARRANTED_BOUNDED"] * 3)
        one = reclose(cs, routes, rs, withdrawn=frozenset({"r"}))
        self.assertEqual(initial, one)
        both = reclose(cs, routes, rs, withdrawn=frozenset({"r", "s"}))
        state = compare_snapshots(initial, both)
        self.assertEqual(state["A"]["after"], "STALE")
        self.assertEqual(state["B"]["after"], "STALE")
        self.assertEqual(state["C"]["after"], "WARRANTED_BOUNDED")
        self.assertFalse(state["C"]["changed"])

    def test_documentary_can_never_prove_math(self):
        with self.assertRaisesRegex(ValueError, "CROSS_BOUNDARY"):
            reclose([Claim("theorem", "formal", "scope")],
                    [Route("theorem", ("publisher-says",))],
                    [Receipt("publisher-says", "documentary", "scope")])

    def test_cross_context_invalid_without_verified_adapter(self):
        with self.assertRaisesRegex(ValueError, "CROSS_BOUNDARY"):
            reclose([Claim("a", "formal", "x"), Claim("b", "formal", "y")],
                    [Route("a", ("x",)), Route("b", ("y",), ("a",))],
                    [Receipt("x", "formal", "x"), Receipt("y", "formal", "y")])

    def test_missing_premise_and_cycles_stay_unknown(self):
        graph = [Claim(x, "formal", "scope") for x in "AB"]
        receipts = [Receipt(x, "formal", "scope") for x in ("r", "s")]
        routes = [Route("A", ("r",), ("B",)), Route("B", ("s",), ("A",))]
        self.assertEqual(reclose(graph, routes, receipts),
                         {"A": "UNKNOWN", "B": "UNKNOWN"})

    def test_bad_route_evidence_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "UNKNOWN_ROUTE_RECEIPT"):
            reclose([Claim("a", "documentary", "s")],
                    [Route("a", ("made_up",))], [])

    def test_bad_withdrawal_reference_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "UNKNOWN_WITHDRAWAL_TARGET"):
            reclose([Claim("a", "formal", "s")],
                    [Route("a", ("e",))], [Receipt("e", "formal", "s")],
                    withdrawn=frozenset({"fake"}))

    def test_duplicate_claim_ids_cannot_shadow(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_CLAIM"):
            reclose([Claim("a", "formal", "s"), Claim("a", "formal", "s")],
                    [], [])

    def test_documentary_withdrawal_does_not_create_refutation(self):
        cs = [Claim("paper", "documentary", "s"),
              Claim("theorem", "formal", "s")]
        route = [Route("paper", ("old",))]
        receipts = [Receipt("old", "documentary", "s")]
        before = reclose(cs, route, receipts)
        after = reclose(cs, route, receipts, withdrawn=frozenset({"old"}))
        states = compare_snapshots(before, after)
        self.assertEqual(states["paper"]["after"], "STALE")
        self.assertEqual(states["theorem"]["before"], "UNKNOWN")
        self.assertEqual(states["theorem"]["after"], "UNKNOWN")
        self.assertNotIn("REFUTED", json.dumps(states))

    def test_status_is_order_independent(self):
        cs = [Claim("a", "formal", "s"), Claim("b", "formal", "s")]
        receipts = [Receipt("r1", "formal", "s"), Receipt("r2", "formal", "s")]
        routes = [Route("b", ("r2",), ("a",)), Route("a", ("r1",))]
        self.assertEqual(reclose(cs, routes, receipts),
                         reclose(tuple(reversed(cs)),
                                 tuple(reversed(routes)),
                                 tuple(reversed(receipts))))

    def test_forged_self_hash_without_pinned_authority_is_not_a_warrant(self):
        data = {"schema": "mathgraph.living-warrant-snapshot.v1",
                "claims": {"fake": "WARRANTED_BOUNDED"}}
        from hashlib import sha256
        data["snapshot_sha256"] = sha256(canonical(data)).hexdigest()
        self.assertTrue(verify_snapshot(data))  # integrity only, not authority
        data["claims"]["fake"] = "REFUTED"
        with self.assertRaisesRegex(ValueError, "SNAPSHOT_CORRUPTED"):
            verify_snapshot(data)


class RealSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            history = Path(os.environ["MATHGRAPH_OPENAI_HISTORY_MD"])
            v1 = Path(os.environ["MATHGRAPH_V1_EVIDENCE_ZIP"])
            v2 = Path(os.environ["MATHGRAPH_V2_EVIDENCE_ZIP"])
        except KeyError as e:
            raise RuntimeError("Exact-source CI fixture required: " + str(e))
        cls.history = history.read_bytes()
        cls.record = build_record(v1, v2)

    def test_official_source_hash_and_exact_three(self):
        self.assertEqual(git_blob_sha1(self.history), OPENAI_HISTORY_BLOB)
        self.assertEqual(read_withdrawals(self.history), WITHDRAWN_TITLES)
        self.assertEqual(OPENAI_HEAD, "fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb")

    def test_mutated_source_refuses_publisher_notice(self):
        with self.assertRaisesRegex(ValueError, "GIT_BLOB_MISMATCH"):
            read_withdrawals(self.history + b"\n# forged\n")

    def test_jpl_receipt_pin_and_finite_case_scope(self):
        self.assertEqual(self.record["content_sha256"], EXPECTED_RECORD_SHA256)
        self.assertEqual(self.record["id"], JPL_RECORD_ID)

    def test_end_to_end_exact_source_live_graph(self):
        snap = build_snapshot(self.history, self.record)
        self.assertTrue(verify_snapshot(snap))
        items = snap["publisher_notice"]["documents"]
        self.assertEqual(tuple(x["name"] for x in items), WITHDRAWN_TITLES)
        for item in items:
            after = snap["resolutions"][item["original_support_claim"]]
            self.assertEqual(after["before"], "SOURCE_DOCUMENTED")
            self.assertEqual(after["after"], "STALE")
            self.assertEqual(item["mathematical_truth"], "UNKNOWN")
        self.assertEqual(
            snap["resolutions"][JPL_CLAIM],
            {"before": "WARRANTED_BOUNDED", "after": "WARRANTED_BOUNDED",
             "changed": False}
        )
        self.assertEqual(snap["sources"]["jpl_record_sha256"], EXPECTED_RECORD_SHA256)
        self.assertEqual(snap["interpretation"]["runtime_status"],
                         "IMMUTABLE_HISTORICAL_SNAPSHOT_NOT_CONTINUOUSLY_MONITORED")

    def test_actual_snapshot_and_html_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "history.md").write_bytes(self.history)
            (root / "jpl.json").write_text(json.dumps(self.record), encoding="utf-8")
            snap = write_snapshot(root / "history.md", root / "jpl.json", root)
            published = json.loads((root / "living.json").read_bytes())
            self.assertEqual(published, snap)
            page = (root / "living.html").read_text(encoding="utf-8")
            self.assertEqual(page, render_html(snap))
            self.assertIn("Truth is not silently rewritten", page)
            self.assertIn("not a claimed formally sound proof", page)
            self.assertIn("UNKNOWN", page)
            self.assertIn("WARRANTED_BOUNDED", page)

    def test_forged_qualified_jpl_record_rejected(self):
        altered = json.loads(json.dumps(self.record))
        altered["axes"]["generalization"]["status"] = "WARRANTED"
        with self.assertRaises(ValueError):
            build_snapshot(self.history, altered)


if __name__ == "__main__":
    unittest.main()
