#!/usr/bin/env python3
"""Strict, stdlib-only validation for Resolve bundle and trust-policy v1.

This consumer validates transport integrity and the exact historical admission
profile.  It intentionally does not replay Resolve semantics; that remains the
job of ``conformance/resolve_v1/consumer.py``.
"""

import argparse
import base64
import binascii
import hashlib
import json
import math
from pathlib import Path
import sys


BUNDLE_SCHEMA = "mathgraph.resolve-bundle.v1"
POLICY_SCHEMA = "mathgraph.resolve-trust-policy.v1"
REPORT_SCHEMA = "mathgraph.resolve-protocol-validation-report.v1"
MEMBER_NAMES = {"history.md", "jpl-record.json", "record.json"}
AUTHORIZED_MEMBERS = {
    "history.md": {"size": 2281, "sha256": "41c2a2d470014b3628695c7aabf5fd0c93f6f687621fca172062f22b59ed6a1e"},
    "jpl-record.json": {"size": 4321, "sha256": "7b59ee76a39995f35a0feb0f4d91a3c6ab1234393143480c4f3e361a79fee703"},
    "record.json": {"size": 5290, "sha256": "0a850b112cce200f2fa97f0d861db712f3752712a6326e62f4c0d56996a95d87"},
}
AUTHORIZED_PROVENANCE = {
    "prior_independent_replay": {
        "actions_run": "38025236380",
        "commit": "9b3189a64825e2cb6ebc7b5c17f5f193bdf5cfe3",
        "independently_owned": False,
        "repository": "heathsanchez/realitygraph",
    },
    "producer": {
        "actions_run": "38025044631",
        "commit": "040456fc8862c79c8b384ce63846628274b678be",
        "repository": "metalogiclabs/mathgraph",
    },
}
JPL_SCOPE = (
    "nasa-jpl/L4YAML@62bf7077910e888a0bc8adfc8e08a5f500ff3ca3:"
    "yaml/yaml-test-suite@da267a5c4782e7361e82889e76c0dc7df0e1e870:48-cases"
)
EXPECTED_ADMISSIONS = {
    "mathgraph.l4yaml.48-case-qualification": {
        "assumptions": [],
        "kind": "formal",
        "outcome": "SUPPORT",
        "scope": JPL_SCOPE,
        "source": "jpl-record.json",
        "verifier": "pinned-jpl-qualified-receipt-v1",
    },
    "openai.original_publication_receipt.1": {
        "assumptions": [],
        "kind": "documentary",
        "outcome": "SUPPORT",
        "scope": "openai/math:Algebraicity of Weil classes on split abelian eightfolds:original-withdrawn-edition",
        "source": "history.md",
        "verifier": "pinned-publisher-notice-v1",
    },
    "openai.original_publication_receipt.2": {
        "assumptions": [],
        "kind": "documentary",
        "outcome": "SUPPORT",
        "scope": "openai/math:Algebraicity of Kuga–Satake Correspondences for K3 Surfaces:original-withdrawn-edition",
        "source": "history.md",
        "verifier": "pinned-publisher-notice-v1",
    },
    "openai.original_publication_receipt.3": {
        "assumptions": [],
        "kind": "documentary",
        "outcome": "SUPPORT",
        "scope": "openai/math:The rational Hodge conjecture for products of K3 surfaces:original-withdrawn-edition",
        "source": "history.md",
        "verifier": "pinned-publisher-notice-v1",
    },
}


class ProtocolError(ValueError):
    """Fail-closed validation error carrying a stable machine reason code."""

    def __init__(self, reason_code, detail=""):
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(reason_code + (f": {detail}" if detail else ""))


def reject(reason_code, detail=""):
    raise ProtocolError(reason_code, detail)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def parse_json(raw, label):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                reject("DUPLICATE_JSON_KEY", f"{label}:{key}")
            result[key] = value
        return result

    def finite_float(value):
        parsed = float(value)
        if not math.isfinite(parsed):
            reject("NONFINITE_JSON_NUMBER", label)
        return parsed

    def nonfinite_constant(_value):
        reject("NONFINITE_JSON_NUMBER", label)

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_float=finite_float,
            parse_constant=nonfinite_constant,
        )
    except ProtocolError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        reject("INVALID_JSON", f"{label}:{error}")
    if type(value) is not dict:
        reject("INVALID_ROOT_TYPE", label)
    return value


def exact_fields(value, required, label):
    if type(value) is not dict:
        reject("INVALID_FIELD_TYPE", label)
    missing = set(required) - set(value)
    if missing:
        reject("MISSING_FIELD", f"{label}:{sorted(missing)[0]}")
    extra = set(value) - set(required)
    if extra:
        reject("UNEXPECTED_FIELD", f"{label}:{sorted(extra)[0]}")


def validate_sha256(value, label):
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        reject("INVALID_SHA256", label)


def validate_provenance(value, label):
    exact_fields(value, ("producer", "prior_independent_replay"), label)
    exact_fields(value["producer"], ("repository", "commit", "actions_run"), f"{label}.producer")
    exact_fields(
        value["prior_independent_replay"],
        ("repository", "commit", "actions_run", "independently_owned"),
        f"{label}.prior_independent_replay",
    )
    for owner in ("producer", "prior_independent_replay"):
        entry = value[owner]
        if not all(type(entry[key]) is str and entry[key] for key in ("repository", "commit", "actions_run")):
            reject("INVALID_FIELD_TYPE", f"{label}.{owner}")
        if len(entry["commit"]) != 40 or any(c not in "0123456789abcdef" for c in entry["commit"]):
            reject("INVALID_GIT_COMMIT", f"{label}.{owner}.commit")
    if type(value["prior_independent_replay"]["independently_owned"]) is not bool:
        reject("INVALID_FIELD_TYPE", f"{label}.prior_independent_replay.independently_owned")


def validate_policy(policy, policy_raw, policy_sha256):
    validate_sha256(policy_sha256, "policy_sha256")
    if sha256(policy_raw) != policy_sha256:
        reject("POLICY_HASH_MISMATCH")
    exact_fields(policy, ("schema", "members", "provenance", "admissions"), "policy")
    if policy["schema"] != POLICY_SCHEMA:
        reject("UNSUPPORTED_POLICY_VERSION", str(policy["schema"]))
    validate_provenance(policy["provenance"], "policy.provenance")
    if policy["provenance"] != AUTHORIZED_PROVENANCE:
        reject("UNAUTHORIZED_PROVENANCE")
    if type(policy["members"]) is not dict:
        reject("INVALID_FIELD_TYPE", "policy.members")
    if set(policy["members"]) != MEMBER_NAMES:
        reject("MISSING_MEMBER" if MEMBER_NAMES - set(policy["members"]) else "UNEXPECTED_FIELD", "policy.members")
    for name, pin in policy["members"].items():
        exact_fields(pin, ("size", "sha256"), f"policy.members.{name}")
        if type(pin["size"]) is not int or pin["size"] < 0:
            reject("INVALID_FIELD_TYPE", f"policy.members.{name}.size")
        validate_sha256(pin["sha256"], f"policy.members.{name}.sha256")
    admissions = policy["admissions"]
    if type(admissions) is not dict:
        reject("INVALID_FIELD_TYPE", "policy.admissions")
    if set(admissions) != set(EXPECTED_ADMISSIONS):
        reject("ADMISSION_ID_MISMATCH")
    for admission_id, admission in admissions.items():
        exact_fields(admission, ("assumptions", "kind", "outcome", "scope", "source", "verifier"), f"admissions.{admission_id}")
        if type(admission["kind"]) is not str:
            reject("INVALID_FIELD_TYPE", f"admissions.{admission_id}.kind")
        if admission["kind"] not in {"documentary", "formal"}:
            reject("UNKNOWN_SEMANTIC_KIND", admission_id)
        expected = EXPECTED_ADMISSIONS[admission_id]
        checks = (
            ("source", "ADMISSION_SOURCE_MISMATCH"),
            ("scope", "ADMISSION_SCOPE_MISMATCH"),
            ("verifier", "ADMISSION_VERIFIER_MISMATCH"),
            ("assumptions", "ADMISSION_ASSUMPTIONS_MISMATCH"),
            ("kind", "ADMISSION_KIND_MISMATCH"),
            ("outcome", "ADMISSION_OUTCOME_MISMATCH"),
        )
        for field, reason in checks:
            if admission[field] != expected[field]:
                reject(reason, admission_id)


def decode_members(bundle, policy):
    members = bundle["members"]
    if type(members) is not dict:
        reject("INVALID_FIELD_TYPE", "bundle.members")
    missing = MEMBER_NAMES - set(members)
    if missing:
        reject("MISSING_MEMBER", sorted(missing)[0])
    extra = set(members) - MEMBER_NAMES
    if extra:
        reject("UNEXPECTED_FIELD", f"bundle.members.{sorted(extra)[0]}")
    decoded = {}
    for name in sorted(MEMBER_NAMES):
        member = members[name]
        exact_fields(member, ("encoding", "data", "size", "sha256"), f"bundle.members.{name}")
        if member["encoding"] != "base64" or type(member["data"]) is not str:
            reject("UNSUPPORTED_MEMBER_ENCODING", name)
        if type(member["size"]) is not int or member["size"] < 0:
            reject("INVALID_FIELD_TYPE", f"bundle.members.{name}.size")
        validate_sha256(member["sha256"], f"bundle.members.{name}.sha256")
        try:
            raw = base64.b64decode(member["data"], validate=True)
        except (binascii.Error, ValueError):
            reject("INVALID_BASE64", name)
        if base64.b64encode(raw).decode("ascii") != member["data"]:
            reject("INVALID_BASE64", name)
        if len(raw) != member["size"]:
            reject("MEMBER_SIZE_MISMATCH", name)
        if sha256(raw) != member["sha256"]:
            reject("MEMBER_HASH_MISMATCH", name)
        pin = policy["members"][name]
        if member["size"] != pin["size"]:
            reject("MEMBER_SIZE_MISMATCH", name)
        if member["sha256"] != pin["sha256"]:
            reject("MEMBER_HASH_MISMATCH", name)
        if pin != AUTHORIZED_MEMBERS[name]:
            reject("UNAUTHORIZED_MEMBER", name)
        decoded[name] = raw
    return decoded


def validate_receipt_bindings(record_raw, admissions):
    record = parse_json(record_raw, "record.json")
    derivation = record.get("derivation")
    if type(derivation) is not dict or type(derivation.get("receipts")) is not list:
        reject("MISSING_FIELD", "record.json.derivation.receipts")
    receipts = {}
    for item in derivation["receipts"]:
        exact_fields(item, ("id", "kind", "scope"), "record.json.receipt")
        if item["kind"] not in {"documentary", "formal"}:
            reject("UNKNOWN_SEMANTIC_KIND", str(item.get("id")))
        if item["id"] in receipts:
            reject("DUPLICATE_IDENTITY", item["id"])
        receipts[item["id"]] = item
    if set(receipts) != set(admissions):
        reject("ADMISSION_ID_MISMATCH")
    for admission_id, admission in admissions.items():
        receipt = receipts[admission_id]
        if receipt["kind"] != admission["kind"]:
            reject("ADMISSION_KIND_MISMATCH", admission_id)
        if receipt["scope"] != admission["scope"]:
            reject("ADMISSION_SCOPE_MISMATCH", admission_id)


def validate(bundle_raw, policy_raw, policy_sha256):
    """Validate exact Resolve v1 transport and admission contracts."""

    bundle = parse_json(bundle_raw, "bundle")
    policy = parse_json(policy_raw, "policy")
    validate_policy(policy, policy_raw, policy_sha256)
    exact_fields(bundle, ("schema", "members", "provenance"), "bundle")
    if bundle["schema"] != BUNDLE_SCHEMA:
        reject("UNSUPPORTED_BUNDLE_VERSION", str(bundle["schema"]))
    validate_provenance(bundle["provenance"], "bundle.provenance")
    if bundle["provenance"] != policy["provenance"]:
        reject("PROVENANCE_MISMATCH")
    decoded = decode_members(bundle, policy)
    validate_receipt_bindings(decoded["record.json"], policy["admissions"])
    return {
        "accepted": True,
        "admission_ids": sorted(policy["admissions"]),
        "bundle_schema": BUNDLE_SCHEMA,
        "member_sha256": {name: AUTHORIZED_MEMBERS[name]["sha256"] for name in sorted(MEMBER_NAMES)},
        "policy_schema": POLICY_SCHEMA,
        "schema": REPORT_SCHEMA,
        "semantic_replay": "NOT_PERFORMED",
    }


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--policy-sha256", required=True)
    args = parser.parse_args()
    try:
        report = validate(args.bundle.read_bytes(), args.policy.read_bytes(), args.policy_sha256)
    except (OSError, ProtocolError) as error:
        reason = error.reason_code if isinstance(error, ProtocolError) else "INPUT_READ_ERROR"
        print(canonical({"accepted": False, "reason_code": reason}), file=sys.stderr)
        return 1
    print(canonical(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
