#!/usr/bin/env python3
"""Independent stdlib-only import of the immutable L4YAML public record.

This requalifies a local historical receipt under separately supplied exact
trust policy. It does not execute Lean, fetch sources, admit a kernel claim,
check current lifecycle, or authorize actions. Digests establish integrity;
the explicit local policy, not a producer verdict, supplies receipt authority.
"""
import argparse
import hashlib
import json
import math
import os
import stat
import sys


MAX_INPUT_BYTES = 65536
RECORD_ID = "mg-l4yaml-source-check-20261010"
RECORD_SCHEMA = "mathgraph.public-consequence-record.v1"
CONTENT_HASH = "f0d092974d5d710fe9e17fb6759a894f2c28f2d3f5456439c071bd0a71c8d3cb"
TRANSPORT_HASH = "7b59ee76a39995f35a0feb0f4d91a3c6ab1234393143480c4f3e361a79fee703"
SOURCE_COMMIT = "62bf7077910e888a0bc8adfc8e08a5f500ff3ca3"
SUITE_COMMIT = "da267a5c4782e7361e82889e76c0dc7df0e1e870"
SCOPE = f"nasa-jpl/L4YAML@{SOURCE_COMMIT}:yaml/yaml-test-suite@{SUITE_COMMIT}:48-cases"
GOAL = "finite_parser_acceptance"
VERIFIER = "pinned-jpl-qualified-receipt-v1"
AUTHORIZED_POLICY = {
    "schema": "mathgraph.import-trust-policy.v1",
    "record": {
        "id": RECORD_ID, "schema": RECORD_SCHEMA, "size": 4321,
        "sha256": TRANSPORT_HASH, "content_sha256": CONTENT_HASH,
    },
    "admission": {
        "id": "mathgraph.l4yaml.48-case-qualification",
        "source": "record.json", "kind": "formal", "outcome": "SUPPORT",
        "scope": SCOPE, "verifier": VERIFIER, "assumptions": [],
    },
    "supported_goal": GOAL,
}
SOURCE = {
    "branch_at_pin": "fix-a-grammar-completeness", "commit": SOURCE_COMMIT,
    "external_suite_commit": SUITE_COMMIT,
    "external_suite_repo": "yaml/yaml-test-suite",
    "lean_toolchain": "leanprover/lean4:v4.34.0", "repo": "nasa-jpl/L4YAML",
}
FINITE = {
    "authority": "LEAN_GUARDS_AND_COMPILED_TRYPARSE",
    "case_scope": "Pinned YAML-suite examples after specified source decoding",
    "expected_accept": 31, "expected_reject": 17, "extra_controls": 4,
    "matched_external_labels": 48, "source_cases": 48,
    "status": "PINNED_CASES_CHECKED", "total_lean_guards": 52,
}
NORMALIZATION = {
    "case_id": "26DV:0",
    "decoded_sha256": "b9ac5bb5babe113af697638577d77ee556dbc2d596bf05c5d31a8b402882976a",
    "decoder": "yaml-suite-visible-space-only-v1",
    "raw_sha256": "6a7b111962441781a368bdcb793ca5a4be450b65c2c82da48bca86f3d8944791",
    "v1_raw_mismatch": True, "v2_native_decoded_guard": "PASS",
}
EVIDENCE = {
    "external_sources": {
        "jpl": f"https://github.com/nasa-jpl/L4YAML/tree/{SOURCE_COMMIT}",
        "yaml_suite": f"https://github.com/yaml/yaml-test-suite/tree/{SUITE_COMMIT}",
    },
    "v1_compiled_parser": {
        "archive_sha256": "b75581017d6620481c77e52b350e8bb8631d11747a92789f7887cde527807086",
        "artifact_id": 11657687808,
        "artifact_url": "https://github.com/metalogiclabs/mathgraph/actions/runs/38018495536/artifacts/11657687808",
        "original_build_targets": 487, "raw_unconverted_external_agreement": 47,
        "run": 38018495536, "source_commit": "d49a17d2786e6d071af37d2aeba2f2dad7765b75",
        "url": "https://github.com/metalogiclabs/mathgraph/actions/runs/38018495536",
    },
    "v2_normalized_native_parser": {
        "archive_sha256": "61fc93815e3329c0490324f52897a94d3417044a5cf16a8e1e0f0109aa0e515e",
        "artifact_id": 11657314389,
        "artifact_url": "https://github.com/metalogiclabs/mathgraph/actions/runs/38020008793/artifacts/11657314389",
        "decoded_case_count": 48, "guards": 52,
        "lean_source_sha256": "a9a16f54c053e3c3c5a9f56486508a04ac84d9eb9e18106271daddac488d5b62",
        "run": 38020008793, "source_commit": "988afbf9a6ec69488b63af5c7ff986fde26d673c",
        "url": "https://github.com/metalogiclabs/mathgraph/actions/runs/38020008793",
    },
}


class ImportError(ValueError):
    """Fail-closed rejection with a stable machine-readable reason code."""

    def __init__(self, reason_code):
        self.reason_code = reason_code
        super().__init__(reason_code)


def require(condition, reason):
    if not condition:
        raise ImportError(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def parse_json(raw):
    require(type(raw) is bytes, "INVALID_INPUT_TYPE")
    require(len(raw) <= MAX_INPUT_BYTES, "INPUT_TOO_LARGE")

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result

    def number(value):
        parsed = float(value)
        require(math.isfinite(parsed), "NONFINITE_JSON_NUMBER")
        return parsed

    def constant(_value):
        raise ImportError("NONFINITE_JSON_NUMBER")

    try:
        result = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                            parse_float=number, parse_constant=constant)
        # Also reject escaped lone surrogates, which cannot be canonical UTF-8.
        canonical(result)
    except ImportError:
        raise
    except (ValueError, RecursionError):
        raise ImportError("INVALID_JSON") from None
    require(type(result) is dict, "INVALID_ROOT_TYPE")
    return result


def same(actual, expected, reason):
    # Canonical comparison distinguishes bool/int and float/int values.
    require(canonical(actual) == canonical(expected), reason)


def validate_record(record):
    fields = {
        "admission", "attribution", "axes", "content_sha256", "evidence", "id",
        "known_separator", "project", "publisher", "record_kind", "schema",
        "snapshot_date", "source", "test_input_normalization", "title",
    }
    require(not (set(record) - fields), "UNEXPECTED_FIELD")
    require(not (fields - set(record)), "MISSING_FIELD")
    require(record["schema"] == RECORD_SCHEMA, "UNSUPPORTED_RECORD_SCHEMA")
    require(record["record_kind"] == "READ_ONLY_EVIDENCE_PROJECTION", "UNSUPPORTED_RECORD_KIND")
    require(record["id"] == RECORD_ID, "RECORD_ID_MISMATCH")
    same(record["source"], SOURCE, "SOURCE_PIN_MISMATCH")
    same(record["evidence"], EVIDENCE, "EVIDENCE_MISMATCH")
    same(record["test_input_normalization"], NORMALIZATION, "ASSUMPTION_CONTEXT_MISMATCH")
    axes = record["axes"]
    require(type(axes) is dict, "AXIS_MISMATCH")
    same(axes.get("finite_executable"), FINITE, "FINITE_SCOPE_MISMATCH")
    same({key: value for key, value in axes.items() if key != "finite_executable"}, {
        "current_requalification": {"status": "NOT_CHECKED_AFTER_SNAPSHOT"},
        "formal_verification": {
            "authority": "ORIGINAL_JPL_LEAN_PROOF_OBJECTS",
            "scope": "Named executable factorization and scoped anchor-event lemmas only",
            "status": "PINNED_SOURCE_THEOREMS_REPLAYED",
            "universal_yaml_correctness": "UNKNOWN",
        },
        "generalization": {"status": "UNKNOWN", "truth_promoting": False},
        "global_truth_promotion": False,
        "human_digestion": {"status": "UNKNOWN", "truth_promoting": False},
        "statement_fidelity": {"status": "UNKNOWN", "truth_promoting": False},
    }, "AXIS_MISMATCH")
    same(record["admission"], {
        "automatic_api_warrant_promotion": False,
        "mathematical_theorem_badge_issued": False,
        "source_archive_hashes_replayed": True, "source_fidelity_certified": False,
        "status": "WARRANTED_ON_PINNED_BOUNDED_CASES",
    }, "ADMISSION_MISMATCH")
    same(record["known_separator"], {
        "actual_pinned_jpl_parser": "REJECT",
        "evidence_kind": "SOURCE_SPECIFIC_KNOWN_DISCREPANCY",
        "independent_normative_event_model": "ACCEPT", "input": "&x [*x]\\n",
        "jpl_completion_order_event_model": "REJECT", "novel_bug_claim": False,
        "source_to_event_translation": "RESTRICTED_MANUALLY_DECLARED",
        "whole_input_extraction_theorem": "UNKNOWN",
    }, "SEPARATOR_MISMATCH")
    require(record["content_sha256"] == CONTENT_HASH, "CONTENT_HASH_MISMATCH")
    content = {key: value for key, value in record.items() if key != "content_sha256"}
    require(digest(canonical(content)) == CONTENT_HASH, "CONTENT_HASH_MISMATCH")


def import_record(record_raw, policy_raw, policy_sha256, *, goal=GOAL):
    """Return a read-only historical result under an externally pinned policy.

    Both raw inputs are bounded UTF-8 JSON bytes. The policy digest must be
    provided separately by the caller; incoming record metadata never sets it.
    Only the exact existing authority profile is supported, even if the caller
    supplies the digest of a broader policy. Unsupported goals raise ImportError.
    """
    record = parse_json(record_raw)
    policy = parse_json(policy_raw)
    require(type(policy_sha256) is str and digest(policy_raw) == policy_sha256,
            "POLICY_HASH_MISMATCH")
    same(policy, AUTHORIZED_POLICY, "UNAUTHORIZED_POLICY")
    require(canonical(policy) + b"\n" == policy_raw, "NONCANONICAL_POLICY")
    require(goal == GOAL, "UNSUPPORTED_GOAL")
    validate_record(record)
    require(len(record_raw) == policy["record"]["size"] and
            digest(record_raw) == policy["record"]["sha256"], "RECORD_BYTES_MISMATCH")

    finite = record["axes"]["finite_executable"]
    evidence = record["evidence"]["v2_normalized_native_parser"]
    # Derive the bounded outcome from the admitted exact receipt and its scope.
    # Producer status strings were checked for consistency, never used as output.
    supported = (
        policy["admission"]["outcome"] == "SUPPORT"
        and finite["expected_accept"] + finite["expected_reject"] == finite["source_cases"]
        and finite["matched_external_labels"] == finite["source_cases"] == evidence["decoded_case_count"]
        and finite["source_cases"] + finite["extra_controls"] == finite["total_lean_guards"] == evidence["guards"]
    )
    require(supported, "FINITE_SCOPE_MISMATCH")
    return {
        "schema": "mathgraph.import-result.v1", "result_kind": "READ_ONLY_IMPORT_RESULT",
        "processing_mode": "INDEPENDENT_OFFLINE_HISTORICAL_RECORD_POLICY_VALIDATION",
        "consumer_authority": {
            "boundary": "EXACT_HISTORICAL_RECEIPT_AND_LOCAL_POLICY_ONLY",
            "kernel_replay": "NOT_PERFORMED", "kernel_admission": "NOT_PERFORMED",
            "current_truth": "NOT_ESTABLISHED",
        },
        "source_suite_replay": "NOT_PERFORMED",
        "record_id": record["id"], "record_schema": record["schema"],
        "record_sha256": digest(record_raw), "content_sha256": record["content_sha256"],
        "policy_sha256": policy_sha256, "goal": goal,
        "epistemic_status": "WARRANTED_BOUNDED",
        "source": record["source"], "snapshot_date": record["snapshot_date"],
        "verifier": policy["admission"]["verifier"], "assumptions": [],
        "scope": {
            "identity": policy["admission"]["scope"],
            **{key: finite[key] for key in (
                "case_scope", "source_cases", "expected_accept", "expected_reject",
                "extra_controls", "matched_external_labels", "total_lean_guards",
            )},
            "normalization": record["test_input_normalization"]["decoder"],
        },
        "evidence": {
            "receipt_id": policy["admission"]["id"],
            "authority": finite["authority"], "test_commit": evidence["source_commit"],
            "lean_source_sha256": evidence["lean_source_sha256"],
            "archive_sha256": evidence["archive_sha256"],
            "normalization": record["test_input_normalization"],
            "proof_replay": "NOT_PERFORMED",
        },
        "lifecycle": "UNKNOWN", "freshness": "NOT_CHECKED",
        "current_applicability": "UNKNOWN",
        "authorization": "READ_ONLY_NO_AUTOMATIC_AUTHORIZATION",
        "unknowns": {key: "UNKNOWN" for key in (
            "generalization", "human_digestion", "statement_fidelity",
            "universal_yaml_correctness", "whole_input_extraction_theorem",
        )},
    }


def read_local(path):
    require(path != "-" and ":" not in path, "LOCAL_PATH_REQUIRED")
    # Nonblocking open prevents a named pipe from stalling before the fstat gate.
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode), "REGULAR_FILE_REQUIRED")
        require(info.st_size <= MAX_INPUT_BYTES, "INPUT_TOO_LARGE")
        raw = stream.read(MAX_INPUT_BYTES + 1)
    require(len(raw) <= MAX_INPUT_BYTES, "INPUT_TOO_LARGE")
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", required=True, help="Local immutable record.json path")
    parser.add_argument("--policy", required=True, help="Separately reviewed local trust-policy.json path")
    parser.add_argument("--policy-sha256", required=True, help="Separately reviewed exact policy digest")
    parser.add_argument("--goal", default=GOAL)
    args = parser.parse_args()
    try:
        result = import_record(read_local(args.record), read_local(args.policy),
                               args.policy_sha256, goal=args.goal)
    except (ImportError, OSError, ValueError) as error:
        reason = error.reason_code if isinstance(error, ImportError) else "INPUT_READ_ERROR"
        print(canonical({"accepted": False, "reason_code": reason}).decode(), file=sys.stderr)
        return 1
    print(canonical(result).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
