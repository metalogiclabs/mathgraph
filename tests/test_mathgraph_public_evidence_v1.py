"""Release gate: only exact pinned CI archives can earn a public scope card."""
from __future__ import annotations

import copy
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
import unittest

from mathgraph_check.public_receipts import (
    RECORD_ID, JPL_COMMIT, SUITE_COMMIT, ReleaseBoundaryError,
    TRUSTED_ZIPS, build_record, build_site, canonical_json, digest,
    render_badge, render_html, resolve, _release_integrity, openapi,
)
from mathgraph_check.public_http import app_for, load_release


def call_wsgi(application, method: str, path: str, payload=None,
              content_type="application/json", length=None):
    body = b"" if payload is None else json.dumps(payload).encode()
    args = {
        "REQUEST_METHOD": method, "PATH_INFO": path,
        "CONTENT_TYPE": content_type,
        "CONTENT_LENGTH": str(len(body) if length is None else length),
        "wsgi.input": BytesIO(body),
    }
    result = []
    def started(status, headers):
        result.extend([status, dict(headers)])
    data = b"".join(application(args, started))
    return result[0], result[1], data


class PinnedEvidencePublicReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # CI MUST provide actual external proof evidence; no in-repo canned JSON
        # is allowed to masquerade as real verifier receipts.
        v1 = os.environ.get("MATHGRAPH_V1_EVIDENCE_ZIP")
        v2 = os.environ.get("MATHGRAPH_V2_EVIDENCE_ZIP")
        if not v1 or not v2:
            raise RuntimeError("REAL_PINNED_CI_ARCHIVE_INPUTS_ARE_REQUIRED")
        cls.v1, cls.v2 = Path(v1), Path(v2)
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.record = build_site(cls.v1, cls.v2, cls.root)
        cls.app = app_for(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_01_exact_archive_digests_and_source_receipts(self):
        self.assertEqual(digest(self.v1.read_bytes()), TRUSTED_ZIPS["v1"])
        self.assertEqual(digest(self.v2.read_bytes()), TRUSTED_ZIPS["v2"])
        self.assertEqual(self.record["source"]["commit"], JPL_COMMIT)
        self.assertEqual(self.record["source"]["external_suite_commit"], SUITE_COMMIT)
        self.assertTrue(self.record["admission"]["source_archive_hashes_replayed"])
        self.assertEqual(self.record["source"]["branch_at_pin"], "fix-a-grammar-completeness")

    def test_02_scope_is_not_general_proof_or_statement_fidelity(self):
        axes = self.record["axes"]
        self.assertEqual(axes["finite_executable"]["matched_external_labels"], 48)
        self.assertEqual(axes["finite_executable"]["expected_accept"], 31)
        self.assertEqual(axes["finite_executable"]["expected_reject"], 17)
        self.assertEqual(axes["finite_executable"]["total_lean_guards"], 52)
        self.assertEqual(axes["formal_verification"]["universal_yaml_correctness"], "UNKNOWN")
        self.assertEqual(axes["statement_fidelity"]["status"], "UNKNOWN")
        self.assertEqual(axes["generalization"]["status"], "UNKNOWN")
        self.assertEqual(axes["current_requalification"]["status"], "NOT_CHECKED_AFTER_SNAPSHOT")
        self.assertFalse(axes["global_truth_promotion"])
        self.assertFalse(self.record["admission"]["mathematical_theorem_badge_issued"])

    def test_03_negative_lineage_is_not_rewritten_into_a_jpl_failure(self):
        src = self.record["test_input_normalization"]
        self.assertEqual(src["case_id"], "26DV:0")
        self.assertEqual(src["decoder"], "yaml-suite-visible-space-only-v1")
        self.assertNotEqual(src["raw_sha256"], src["decoded_sha256"])
        self.assertTrue(src["v1_raw_mismatch"])
        self.assertEqual(src["v2_native_decoded_guard"], "PASS")
        self.assertTrue(self.record["known_separator"]["normative_event_model"]
                        if False else self.record["known_separator"]["independent_normative_event_model"] == "ACCEPT")
        self.assertEqual(self.record["known_separator"]["actual_pinned_jpl_parser"], "REJECT")
        self.assertFalse(self.record["known_separator"]["novel_bug_claim"])

    def test_04_qualified_query_yields_exact_scoped_consequence(self):
        query = {
            "record_id": RECORD_ID,
            "source_commit": JPL_COMMIT,
            "external_suite_commit": SUITE_COMMIT,
            "goal": "finite_parser_acceptance",
        }
        result = resolve(self.record, query)
        self.assertEqual(result["status"], "WARRANTED_BOUNDED")
        self.assertEqual(result["verified"], {"matched": 48, "total": 48, "extra_controls": 4})
        self.assertEqual(result["whole_language_validity"], "UNKNOWN")
        self.assertFalse(result["truth_promotion"])
        self.assertEqual(result["record_sha256"], self.record["content_sha256"])
        query["goal"] = "recursive_anchor_behavior"
        result = resolve(self.record, query)
        self.assertEqual(result["status"], "WARRANTED_BOUNDED_DIFFERENCE")
        self.assertEqual(result["pinned_jpl"], "REJECT")
        self.assertEqual(result["general_semantic_fidelity"], "UNKNOWN")

    def test_05_unknown_scope_and_unsupported_claims_fail_closed(self):
        common = {
            "record_id": RECORD_ID, "source_commit": JPL_COMMIT,
            "external_suite_commit": SUITE_COMMIT,
            "goal": "finite_parser_acceptance",
        }
        for diff in (
            {"source_commit": "f" * 40},
            {"external_suite_commit": "0" * 40},
            {"record_id": "other"}, 
        ):
            with self.subTest(diff=diff):
                q = {**common, **diff}
                self.assertEqual(resolve(self.record, q)["status"], "UNKNOWN")
        for goal in ("full_yaml_correctness", "natural_language_fidelity",
                     "proves_NASA_compliance", "prove_all_yamls"):
            with self.subTest(goal=goal):
                self.assertEqual(resolve(self.record, {**common, "goal": goal})["status"], "UNKNOWN")
        self.assertEqual(resolve(self.record, {**common, "truth_promoting": True})["status"], "BAD_REQUEST")
        self.assertEqual(resolve(self.record, {"goal": "finite_parser_acceptance"})["status"], "BAD_REQUEST")
        self.assertEqual(resolve(self.record, None)["status"], "BAD_REQUEST")

    def test_06_snapshot_json_cannot_be_changed_and_preserve_digest(self):
        changed = copy.deepcopy(self.record)
        changed["axes"]["generalization"]["status"] = "VERIFIED"
        with self.assertRaises(ReleaseBoundaryError):
            _release_integrity(changed)
        changed = copy.deepcopy(self.record)
        changed["admission"]["mathematical_theorem_badge_issued"] = True
        changed.pop("content_sha256")
        changed["content_sha256"] = digest(canonical_json(changed))
        with self.assertRaises(ReleaseBoundaryError):
            _release_integrity(changed)
        self.assertEqual(load_release(self.root), self.record)

    def test_07_archived_evidence_tampering_is_fatal(self):
        tampered = self.root / "tampered.zip"
        raw = bytearray(self.v2.read_bytes())
        raw[len(raw) // 2] ^= 1
        tampered.write_bytes(raw)
        with self.assertRaisesRegex(ReleaseBoundaryError, "EVIDENCE_ARCHIVE_SHA256_MISMATCH"):
            build_record(self.v1, tampered)
        tampered.write_bytes(self.v2.read_bytes() + b"x")
        with self.assertRaisesRegex(ReleaseBoundaryError, "EVIDENCE_ARCHIVE_SHA256_MISMATCH"):
            build_record(self.v1, tampered)

    def test_08_the_status_svg_is_scoped_and_never_universal(self):
        badge = render_badge(self.record)
        self.assertIn("48/48", badge)
        self.assertIn("pinned source cases", badge)
        self.assertNotIn("theorem verified", badge.lower())
        self.assertNotIn("mathematics verified", badge.lower())
        self.assertNotIn("<script", badge.lower())
        html = render_html(self.record)
        self.assertIn("Universal theorem: UNKNOWN", html)
        self.assertIn("31 accepts / 17 rejects", html)
        self.assertIn("No project endorsement", html)
        self.assertIn("&amp;x [*x]", html)
        self.assertNotIn('src="https://', html)
        self.assertNotIn("<script", html)

    def test_09_every_generated_public_surface_is_identical_on_replay(self):
        again = Path(self.temp.name) / "second"
        second = build_site(self.v1, self.v2, again)
        self.assertEqual(self.record, second)
        for name in ("record.json", "evidence.json", "index.html", "badge.svg", "openapi.json"):
            self.assertEqual((self.root / name).read_bytes(), (again / name).read_bytes())
        self.assertIn("/v1/resolve", openapi()["paths"])

    def test_10_wsgi_routes_are_read_only(self):
        path = "/v1/records/" + RECORD_ID
        status, headers, body = call_wsgi(self.app, "GET", path)
        self.assertEqual(status, "200 OK")
        self.assertEqual(json.loads(body)["id"], RECORD_ID)
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        status, _, body = call_wsgi(self.app, "HEAD", path)
        self.assertEqual(status, "200 OK")
        self.assertEqual(body, b"")
        status, _, body = call_wsgi(self.app, "GET", "/records/" + RECORD_ID)
        self.assertEqual(status, "200 OK")
        self.assertIn(b"48/48", body)
        status, _, body = call_wsgi(self.app, "GET", "/v1/badges/" + RECORD_ID + ".svg")
        self.assertEqual(status, "200 OK")
        self.assertIn(b"pinned source cases", body)
        status, _, body = call_wsgi(self.app, "GET", "/v1/records/" + RECORD_ID + "/evidence")
        self.assertEqual(status, "200 OK")
        self.assertIn("v2_normalized_native_parser", json.loads(body))
        status, _, body = call_wsgi(self.app, "GET", "/v1/openapi.json")
        self.assertEqual(status, "200 OK")
        self.assertIn("/v1/resolve", json.loads(body)["paths"])
        status, _, body = call_wsgi(self.app, "GET", "/v1/records/not-a-record")
        self.assertEqual(status, "404 Not Found")
        status, _, _ = call_wsgi(self.app, "PUT", "/v1/records/" + RECORD_ID)
        self.assertEqual(status, "405 Method Not Allowed")

    def test_11_agent_api_does_not_compute_or_accept_untrusted_promotions(self):
        valid = {
            "record_id": RECORD_ID,
            "source_commit": JPL_COMMIT,
            "external_suite_commit": SUITE_COMMIT,
            "goal": "finite_parser_acceptance",
        }
        status, headers, body = call_wsgi(self.app, "POST", "/v1/resolve", valid)
        self.assertEqual(status, "200 OK")
        self.assertEqual(json.loads(body)["status"], "WARRANTED_BOUNDED")
        self.assertEqual(headers["Cache-Control"], "no-store")
        status, _, body = call_wsgi(self.app, "POST", "/v1/resolve",
                                   {**valid, "certified": True})
        self.assertEqual(status, "400 Bad Request")
        self.assertEqual(json.loads(body)["status"], "BAD_REQUEST")
        status, _, _ = call_wsgi(self.app, "POST", "/v1/resolve", valid,
                                 content_type="text/plain")
        self.assertEqual(status, "415 Unsupported Media Type")
        status, _, _ = call_wsgi(self.app, "POST", "/v1/resolve", valid,
                                 length=100_000_000)
        self.assertEqual(status, "413 Content Too Large")
        status, _, _ = call_wsgi(self.app, "POST", "/v1/records/" + RECORD_ID, valid)
        self.assertEqual(status, "405 Method Not Allowed")

    def test_12_cannot_fake_public_html_or_status_after_build(self):
        site = self.root / "index.html"
        old = site.read_text()
        site.write_text(old + "<script>fake verified</script>")
        try:
            with self.assertRaisesRegex(ReleaseBoundaryError, "PUBLIC_HTML"):
                app_for(self.root)
        finally:
            site.write_text(old)


if __name__ == "__main__":
    unittest.main()
