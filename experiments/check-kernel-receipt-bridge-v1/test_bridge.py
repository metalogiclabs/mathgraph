"""Behavioral checks for bounded Flash evidence → existing MathGraph resolver."""
import copy
import json
from pathlib import Path
import unittest

import bridge


POLICY = json.loads((Path(__file__).parent / "policy.json").read_text())


def observed_accept():
    return {
        "schema": "mathgraph.kernel-native-observation.v1",
        "checker": copy.deepcopy(POLICY["checker"]),
        "source": copy.deepcopy(POLICY["source"]),
        "theorem": copy.deepcopy(POLICY["theorem"]),
        "runner": {
            "repository": "metalogiclabs/mathgraph",
            "workflow": "check-kernel-receipt-bridge-v1.yml",
            "run_id": 41650000001,
            "attempt": 1,
            "source_commit": "a" * 40,
            "evidence_acquisition": "IN_PROCESS_NATIVE_SUBPROCESS",
        },
        "native": {"exit_code": 0, "elapsed_ns": 1200000,
                   "binary_sha256": "b" * 64, "stdout_sha256": "c" * 64,
                   "stderr_sha256": "d" * 64},
    }


def exact_request():
    return copy.deepcopy(POLICY["consumer"])


def trusted_context():
    return {
        "repository": "metalogiclabs/mathgraph",
        "workflow": "check-kernel-receipt-bridge-v1.yml",
        "run_id": 41650000001,
        "attempt": 1,
        "source_commit": "a" * 40,
    }


class KernelReceiptBridgeTests(unittest.TestCase):
    def test_exact_native_accept_supports_only_operator_adopted_type(self):
        obs = observed_accept()
        decision = bridge.qualify(obs, exact_request(), POLICY,
                                  trusted_context=trusted_context())
        self.assertEqual(decision["status"], "ADMITTED_BOUNDED")
        self.assertEqual(decision["permission"], "ADVISORY_ONLY")
        self.assertEqual(decision["source_sha256"],
                         "962cfb1378bc2f73e327fd88e526a0b9b7108f4ad1a1df55766d7d1156ad8d76")
        states = bridge.resolve(obs, exact_request(), POLICY,
                                trusted_context=trusted_context())["states"]
        self.assertEqual(states["kernel.bar"], "WARRANTED_BOUNDED")
        self.assertEqual(states["consumer.exact_bar_type"], "WARRANTED_BOUNDED")
        self.assertEqual(states["independent.control"], "WARRANTED_BOUNDED")

    def test_unadmitted_consumer_statement_never_inherits_kernel_accept(self):
        changed = exact_request()
        changed["type_expr_id"] = 1  # weaker or simply different target
        decision = bridge.qualify(observed_accept(), changed, POLICY,
                                  trusted_context=trusted_context())
        self.assertEqual(decision["status"], "UNKNOWN")
        states = bridge.resolve(observed_accept(), changed, POLICY,
                                trusted_context=trusted_context())["states"]
        self.assertEqual(states["kernel.bar"], "WARRANTED_BOUNDED")
        self.assertEqual(states["consumer.exact_bar_type"], "UNKNOWN")
        self.assertEqual(states["independent.control"], "WARRANTED_BOUNDED")

    def test_missing_privileged_runner_context_never_admits_saved_json(self):
        result = bridge.resolve(observed_accept(), exact_request(), POLICY)
        self.assertEqual(result["decision"]["status"], "UNKNOWN")
        self.assertEqual(result["states"]["kernel.bar"], "UNKNOWN")
        self.assertEqual(result["states"]["consumer.exact_bar_type"], "UNKNOWN")

    def test_bad_native_or_source_or_checker_context_fails_closed(self):
        changes = (
            ("native", "exit_code", 1),
            ("native", "exit_code", True),
            ("native", "binary_sha256", "0" * 64),  # legitimate binary may vary; see next test
            ("checker", "commit", "f" * 40),
            ("checker", "lineage", "NUCLEUS_INDEPENDENT"),
            ("source", "export_sha256", "f" * 64),
            ("source", "config_sha256", "f" * 64),
            ("source", "permitted_axioms", ["A"]),
            ("source", "unpermitted_axiom_hard_error", False),
            ("source", "exporter", {}),
            ("theorem", "type_expr_id", 13),
            ("theorem", "name", "fake"),
            ("runner", "evidence_acquisition", "SAVED_JSON"),
            ("runner", "source_commit", "f" * 40),
            ("runner", "run_id", 99),
            ("runner", "workflow", "attacker.yml"),
        )
        for section, field, value in changes:
            # A different *valid* binary digest does not invalidate a native
            # acceptance, but does change the exact reuse key.
            if (section, field) == ("native", "binary_sha256"):
                continue
            with self.subTest(section=section, field=field):
                changed = observed_accept()
                changed[section][field] = value
                decision = bridge.qualify(changed, exact_request(), POLICY,
                                          trusted_context=trusted_context())
                self.assertEqual(decision["status"], "UNKNOWN")
                states = bridge.resolve(changed, exact_request(), POLICY,
                                        trusted_context=trusted_context())["states"]
                self.assertEqual(states["consumer.exact_bar_type"], "UNKNOWN")
                self.assertEqual(states["independent.control"], "WARRANTED_BOUNDED")

    def test_unrecognized_consumer_authority_cannot_be_promoted(self):
        changed = exact_request()
        changed["authority"] = "MODEL_INFERRED"
        decision = bridge.qualify(observed_accept(), changed, POLICY,
                                  trusted_context=trusted_context())
        self.assertEqual(decision["status"], "UNKNOWN")

    def test_invalid_native_sha_or_missing_exit_never_admits(self):
        for field, value in (("binary_sha256", "not-a-digest"),
                             ("stdout_sha256", None),
                             ("exit_code", None)):
            with self.subTest(field=field):
                changed = observed_accept()
                changed["native"][field] = value
                self.assertEqual(
                    bridge.qualify(changed, exact_request(), POLICY,
                                   trusted_context=trusted_context())["status"],
                    "UNKNOWN")

    def test_selective_withdrawal_preserves_only_unrelated_support(self):
        obs, target, context = observed_accept(), exact_request(), trusted_context()
        for dropped, expected in (
            ("native.accept", ("UNKNOWN", "UNKNOWN", "WARRANTED_BOUNDED")),
            ("identity.verified", ("WARRANTED_BOUNDED", "UNKNOWN", "WARRANTED_BOUNDED")),
            ("identity.adoption", ("WARRANTED_BOUNDED", "UNKNOWN", "WARRANTED_BOUNDED")),
            ("control.fixture", ("WARRANTED_BOUNDED", "WARRANTED_BOUNDED", "UNKNOWN")),
        ):
            with self.subTest(dropped=dropped):
                states = bridge.resolve(obs, target, POLICY,
                                        trusted_context=context,
                                        withdrawn=frozenset({dropped}))["states"]
                self.assertEqual(tuple(states[k] for k in (
                    "kernel.bar", "consumer.exact_bar_type", "independent.control")),
                    expected)
        with self.assertRaisesRegex(ValueError, "UNKNOWN_WITHDRAWAL_TARGET"):
            bridge.resolve(obs, target, POLICY, trusted_context=context,
                           withdrawn=frozenset({"fake.receipt"}))

    def test_reuse_requires_trusted_prior_and_identical_complete_identity(self):
        prior = observed_accept()
        identity = bridge.candidate_identity(prior, exact_request(), POLICY)
        parameters = dict(prior_trusted_context=trusted_context(),
                          trusted_prior_receipt=True)
        decision = bridge.reuse(prior, exact_request(), POLICY, candidate=identity,
                                **parameters)
        self.assertEqual(decision["status"], "REUSABLE_BOUNDED")
        self.assertEqual(decision["permission"], "ADVISORY_ONLY")
        untrusted = bridge.reuse(prior, exact_request(), POLICY,
                                 candidate=identity,
                                 prior_trusted_context=trusted_context(),
                                 trusted_prior_receipt=False)
        self.assertEqual(untrusted["status"], "UNKNOWN")
        for section, field, value in (
            ("source", "export_sha256", "c" * 64),
            ("source", "config_sha256", "e" * 64),
            ("source", "permitted_axioms", ["A"]),
            ("source", "exporter", {"name": "new-exporter"}),
            ("checker", "commit", "c" * 40),
            ("theorem", "type_expr_id", 13),
            ("consumer", "type_expr_id", 13),
            ("self", "binary_sha256", "d" * 64),
            ("self", "adapter_sha256", "0" * 64),
        ):
            with self.subTest(section=section, field=field):
                changed = copy.deepcopy(identity)
                if section == "self":
                    changed[field] = value
                else:
                    changed[section][field] = value
                result = bridge.reuse(prior, exact_request(), POLICY,
                                      candidate=changed, **parameters)
                self.assertEqual(result["status"], "UNKNOWN")

    def test_cache_identity_binds_exact_bridge_code_not_only_input_bytes(self):
        identity = bridge.candidate_identity(observed_accept(), exact_request(), POLICY)
        self.assertRegex(identity["adapter_sha256"], r"^[0-9a-f]{64}$")

    def test_identical_source_with_different_binary_has_different_cache_identity(self):
        first = observed_accept()
        second = observed_accept()
        second["native"]["binary_sha256"] = "e" * 64
        first_key = bridge.qualify(first, exact_request(), POLICY,
                                   trusted_context=trusted_context())["fingerprint"]
        second_key = bridge.qualify(second, exact_request(), POLICY,
                                    trusted_context=trusted_context())["fingerprint"]
        self.assertNotEqual(first_key, second_key)


if __name__ == "__main__":
    unittest.main()
