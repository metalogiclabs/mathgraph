"""A separate consumer may retrieve only an externally admitted historical receipt."""

import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import bridge
import persisted
from test_bridge import exact_request, observed_accept, trusted_context, POLICY


RESEARCH_BRANCH = "research/check-kernel-persisted-reuse-20261104"


def gh_context():
    return trusted_context()


def native_report():
    obs = observed_accept()
    context = gh_context()
    return {
        "schema": "mathgraph.kernel-receipt-bridge-report.v1",
        "status": "WARRANTED_BOUNDED",
        "source_validation": {
            "checker_commit": POLICY["checker"]["commit"],
            "config_sha256": POLICY["source"]["config_sha256"],
            "export_sha256": POLICY["source"]["export_sha256"],
            "theorem": POLICY["theorem"]["name"],
        },
        "observation": obs,
        "qualification": bridge.qualify(obs, exact_request(), POLICY,
                                        trusted_context=context),
        "mutation": {"same_config_unmutated_control": {"exit_code": 0},
                     "native": {"exit_code": 1}, "expected_exit_code": 1},
        "withdrawal": {"after": bridge.resolve(
            obs, exact_request(), POLICY, trusted_context=context,
            withdrawn=frozenset({"native.accept"}))["states"],
            "expected_dependent_unknown": True},
    }


def stored():
    return (json.dumps(native_report(), sort_keys=True, separators=(",", ":")) + "\n").encode()


def gh_metadata():
    context = gh_context()
    return {
        "run": {
            "id": context["run_id"], "run_attempt": context["attempt"],
            "head_sha": context["source_commit"],
            "head_branch": RESEARCH_BRANCH, "path": ".github/workflows/check-kernel-receipt-bridge-v1.yml",
            "event": "push", "status": "in_progress",
            "repository": {"full_name": "metalogiclabs/mathgraph"},
        },
        "jobs": [
            {"id": 123, "name": "native-receipt", "run_id": context["run_id"],
             "status": "completed", "conclusion": "success"},
        ],
        "artifacts": [
            {"id": 456, "name": "kernel-bridge-native-evidence",
             "expired": False, "digest": "sha256:" + "e" * 64,
             "workflow_run": {"id": context["run_id"],
                              "head_sha": context["source_commit"]}},
        ],
    }


def digest(data):
    return hashlib.sha256(data).hexdigest()


class PersistedConsumerTests(unittest.TestCase):
    def test_fetch_metadata_uses_only_source_bound_authenticated_github_endpoints(self):
        context = gh_context()
        run_id = context["run_id"]
        prefix = f"https://api.github.com/repos/metalogiclabs/mathgraph/actions/runs/{run_id}"
        records = {prefix: gh_metadata()["run"],
                   prefix + "/jobs?per_page=100": {"jobs": gh_metadata()["jobs"]},
                   prefix + "/artifacts?per_page=100": {"artifacts": gh_metadata()["artifacts"]}}
        accessed = []

        def fake_open(request, timeout):
            accessed.append(request.full_url)
            self.assertEqual(request.get_header("Authorization"), "Bearer fixture-token")
            return io.BytesIO(json.dumps(records[request.full_url]).encode())

        with patch("persisted.urlopen", side_effect=fake_open):
            result = persisted.fetch_metadata(context, "fixture-token")
        self.assertEqual(accessed, list(records))
        self.assertEqual(result, gh_metadata())

    def test_missing_github_token_or_untrusted_repository_never_fetches(self):
        for context, token in ((gh_context(), ""),
                               ({**gh_context(), "repository": "other/repo"}, "token"),
                               ({**gh_context(), "run_id": True}, "token")):
            with self.subTest(context=context, token=bool(token)):
                with patch("persisted.urlopen") as urlopen:
                    with self.assertRaisesRegex(ValueError, "UNTRUSTED_API_CONTEXT"):
                        persisted.fetch_metadata(context, token)
                    urlopen.assert_not_called()

    def test_reader_obtains_bytes_from_stored_file_and_records_separate_costs(self):
        raw = stored()
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "native-report.json"
            archive.write_bytes(raw)
            result = persisted.run_consumer(
                archive, digest(raw), POLICY, gh_context(),
                metadata_provider=lambda: gh_metadata())
            self.assertEqual(result["status"], "HISTORICAL_WARRANT_RETRIEVED")
            self.assertEqual(result["current_applicability"], "UNKNOWN")
            self.assertEqual(result["native_checker_invocations_in_consumer"], 0)
            self.assertEqual(set(result["timing_ns"]),
                             {"metadata_fetch", "stored_file_read", "appraisal_and_resolve",
                              "warm_lookup_median", "warm_lookup_p95"})
            self.assertTrue(all(type(value) is int and value >= 0
                                for value in result["timing_ns"].values()))

    def test_session_authenticates_once_then_serves_1000_exact_local_requests(self):
        raw = stored()
        with patch("persisted.appraise", wraps=persisted.appraise) as admitted:
            session = persisted.WarmReceiptSession(
                gh_metadata(), raw, digest(raw), POLICY, gh_context())
            for _ in range(1000):
                result = session.lookup(exact_request(), POLICY)
                self.assertEqual(result["status"], "HISTORICAL_WARRANT_RETRIEVED")
                self.assertEqual(result["current_applicability"], "UNKNOWN")
            self.assertEqual(admitted.call_count, 1)

    def test_warm_session_dependency_withdrawal_and_source_drift_fail_closed(self):
        raw = stored()
        session = persisted.WarmReceiptSession(gh_metadata(), raw, digest(raw), POLICY,
                                               gh_context())
        dropped = session.lookup(exact_request(), POLICY,
                                 withdrawn=frozenset({"native.accept"}))
        self.assertEqual(dropped["status"], "UNKNOWN")
        self.assertEqual(dropped["states"]["independent.control"], "WARRANTED_BOUNDED")
        for section, field, value in (("source", "config_sha256", "1" * 64),
                                      ("source", "permitted_axioms", ["A"]),
                                      ("checker", "commit", "1" * 40),
                                      ("consumer", "type_expr_id", 1)):
            changed = copy.deepcopy(POLICY)
            changed[section][field] = value
            self.assertEqual(session.lookup(exact_request(), changed)["status"], "UNKNOWN")
        with self.assertRaisesRegex(ValueError, "UNKNOWN_WITHDRAWAL_TARGET"):
            session.lookup(exact_request(), POLICY, withdrawn=frozenset({"bogus"}))

    def test_exact_stored_receipt_from_trusted_producer_retrieves_historical_warrant(self):
        raw = stored()
        result = persisted.consume(gh_metadata(), raw, digest(raw), POLICY, gh_context())
        self.assertEqual(result["status"], "HISTORICAL_WARRANT_RETRIEVED")
        self.assertEqual(result["current_applicability"], "UNKNOWN")
        self.assertEqual(result["permission"], "ADVISORY_ONLY")
        self.assertEqual(result["states"]["consumer.exact_bar_type"], "WARRANTED_BOUNDED")
        self.assertEqual(result["source"], "STORED_GITHUB_ACTIONS_ARTIFACT")

    def test_external_digest_mismatch_rejects_even_with_self_consistent_json(self):
        raw = stored()
        changed = json.loads(raw)
        changed["status"] = "WARRANTED_BOUNDED"
        changed["attacker_self_hash"] = digest(raw)
        forged = json.dumps(changed).encode()
        result = persisted.appraise(gh_metadata(), forged, digest(raw), POLICY, gh_context())
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason"], "ARTIFACT_BYTES_MISMATCH")

    def test_missing_or_changed_github_run_job_and_artifact_fail_closed(self):
        raw = stored()
        mutations = (
            ("run", "id", 999), ("run", "head_sha", "b" * 40),
            ("run", "head_branch", "main"), ("run", "path", "attacker.yml"),
            ("run", "event", "pull_request"),
            ("run", "run_attempt", 2),
            ("run", "repository", "not-an-object"),
            ("run", "id", True),
            ("job", "run_id", True),
            ("job", "conclusion", "failure"),
            ("job", "status", "in_progress"),
            ("artifact", "expired", True),
            ("artifact", "name", "other-artifact"),
            ("artifact", "digest", "not-a-sha256"),
            ("artifact", "workflow_run", {"id": 1, "head_sha": "b" * 40}),
        )
        for section, field, value in mutations:
            with self.subTest(section=section, field=field):
                meta = gh_metadata()
                obj = meta["run"] if section == "run" else meta["jobs"][0] if section == "job" else meta["artifacts"][0]
                obj[field] = value
                result = persisted.appraise(meta, raw, digest(raw), POLICY, gh_context())
                self.assertEqual(result["status"], "UNKNOWN")
                self.assertNotEqual(result["reason"], "NONE")

    def test_changed_theorem_source_axiom_checker_or_consumer_does_not_transport(self):
        raw = stored()
        mutations = (
            ("theorem", "type_expr_id", 2),
            ("source", "export_sha256", "c" * 64),
            ("source", "permitted_axioms", ["A"]),
            ("source", "exporter", {}),
            ("checker", "commit", "0" * 40),
            ("consumer", "type_expr_id", 2),
            ("consumer", "authority", "MODEL_INFERRED"),
        )
        for section, field, value in mutations:
            with self.subTest(section=section, field=field):
                policy = copy.deepcopy(POLICY)
                policy[section][field] = value
                result = persisted.consume(gh_metadata(), raw, digest(raw), policy, gh_context())
                self.assertEqual(result["status"], "UNKNOWN")

    def test_report_fingerprint_cannot_be_substituted_even_with_matching_external_digest(self):
        report = native_report()
        report["qualification"]["fingerprint"] = "0" * 64
        raw = json.dumps(report).encode()
        self.assertEqual(
            persisted.consume(gh_metadata(), raw, digest(raw), POLICY, gh_context())["status"],
            "UNKNOWN")

    def test_withdrawing_actual_prior_receipt_removes_dependent_only(self):
        raw = stored()
        result = persisted.consume(gh_metadata(), raw, digest(raw), POLICY, gh_context(),
                                   withdrawn=frozenset({"native.accept"}))
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["states"]["kernel.bar"], "UNKNOWN")
        self.assertEqual(result["states"]["consumer.exact_bar_type"], "UNKNOWN")
        self.assertEqual(result["states"]["independent.control"], "WARRANTED_BOUNDED")

    def test_duplicate_json_keys_and_missing_authenticated_metadata_fail_closed(self):
        raw = stored()
        self.assertEqual(persisted.appraise({}, raw, digest(raw), POLICY, gh_context())["status"],
                         "UNKNOWN")
        malformed = b'{"schema":"x","schema":"y"}'
        result = persisted.appraise(gh_metadata(), malformed, digest(malformed), POLICY, gh_context())
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason"], "DUPLICATE_JSON_KEY")


if __name__ == "__main__":
    unittest.main()
