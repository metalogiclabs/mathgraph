#!/usr/bin/env python3
"""Independent, stdlib-only Resolve v1 historical replay. No network or services.

This deliberately narrow profile admits one historical publication. Generic
closure and the bounded countermodel checker below are exercised separately by
synthetic conformance; synthetic input is never admitted by the historical CLI.
"""
import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import sys


RECORD_ID = "mg-living-warrant-openai-jpl-20261010"
JPL_ID = "mg-l4yaml-source-check-20261010"
SNAPSHOT_HASH = "b95297a081d513fb0ec145a776cc997eaed18109d6b2af39fa8e61f6d637af41"
JPL_CONTENT_HASH = "f0d092974d5d710fe9e17fb6759a894f2c28f2d3f5456439c071bd0a71c8d3cb"
OPENAI_COMMIT = "fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb"
OPENAI_BLOB = "693874f398905b1bc59e01b898b223ae9956bfc2"
JPL_COMMIT = "62bf7077910e888a0bc8adfc8e08a5f500ff3ca3"
SUITE_COMMIT = "da267a5c4782e7361e82889e76c0dc7df0e1e870"
JPL_SCOPE = f"nasa-jpl/L4YAML@{JPL_COMMIT}:yaml/yaml-test-suite@{SUITE_COMMIT}:48-cases"
TITLES = (
    "Algebraicity of Weil classes on split abelian eightfolds",
    "Algebraicity of Kuga–Satake Correspondences for K3 Surfaces",
    "The rational Hodge conjecture for products of K3 surfaces",
)
PINS = {
    "record.json": {"size": 5290, "sha256": "0a850b112cce200f2fa97f0d861db712f3752712a6326e62f4c0d56996a95d87"},
    "history.md": {"size": 2281, "sha256": "41c2a2d470014b3628695c7aabf5fd0c93f6f687621fca172062f22b59ed6a1e"},
    "jpl-record.json": {"size": 4321, "sha256": "7b59ee76a39995f35a0feb0f4d91a3c6ab1234393143480c4f3e361a79fee703"},
}
PROVENANCE = {
    "producer": {"repository": "metalogiclabs/mathgraph", "commit": "040456fc8862c79c8b384ce63846628274b678be", "actions_run": "38025044631"},
    "prior_independent_replay": {"repository": "heathsanchez/realitygraph", "commit": "9b3189a64825e2cb6ebc7b5c17f5f193bdf5cfe3", "actions_run": "38025236380", "independently_owned": False},
}
HISTORICAL_VERIFIERS = {"pinned-publisher-notice-v1", "pinned-jpl-qualified-receipt-v1"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(value, names):
    require(type(value) is dict and set(value) == set(names), "unsupported or missing fields")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).digest().hex()


def parse_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    def number(value):
        parsed = float(value)
        require(math.isfinite(parsed), "non-finite JSON number")
        return parsed

    def constant(_):
        raise ValueError("non-finite JSON constant")

    result = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                        parse_constant=constant, parse_float=number)
    require(type(result) is dict, "JSON root must be an object")
    return result


def identifiers(values):
    require(type(values) is list and all(type(x) is str and x for x in values), "invalid references")
    require(len(values) == len(set(values)), "duplicate references")
    return set(values)


def typed_index(items):
    require(type(items) is list, "expected typed object list")
    result = {}
    for item in items:
        fields(item, ("id", "kind", "scope"))
        require(all(type(x) is str and x for x in item.values()), "invalid typed object")
        require(item["kind"] in {"documentary", "formal"}, "unsupported claim kind")
        require(item["id"] not in result, "duplicate identity")
        result[item["id"]] = item
    return result


def countermodel(admission):
    """Verify a total two-element magma and a concrete failed commutativity equation."""
    require(admission["verifier"] == "finite-magma-noncommutative-v1", "refutation requires native verifier")
    require(admission["kind"] == "formal" and admission["scope"] == "magma:commutative:order=2", "countermodel scope mismatch")
    witness = admission["witness"]
    fields(witness, ("schema", "table", "assignment"))
    require(witness["schema"] == "finite-magma-countermodel.v1", "unsupported witness")
    table, assignment = witness["table"], witness["assignment"]
    require(type(table) is list and len(table) == 2, "invalid finite carrier")
    require(all(type(row) is list and len(row) == 2 and all(type(v) is int and 0 <= v < 2 for v in row) for row in table), "operation must be total on carrier")
    require(type(assignment) is list and len(assignment) == 2 and all(type(v) is int and 0 <= v < 2 for v in assignment), "invalid assignment")
    x, y = assignment
    require(table[x][y] != table[y][x], "witness does not refute commutativity")


def resolve(graph, admissions, allowed_verifiers):
    """Least supported closure; each route is conjunctive and routes are alternatives.

    Admission is a caller trust decision. In the CLI it is made only by replay's
    external policy pin + exact historical source checks, never by a self-hash.
    No kind/scope transport, assumptions, or generalized relations exist in v1.
    """
    fields(graph, ("claims", "receipts", "routes", "withdrawn_evidence"))
    claims, receipts = typed_index(graph["claims"]), typed_index(graph["receipts"])
    require(type(admissions) is dict and set(admissions) == set(receipts), "receipt admission identity mismatch")
    withdrawn = identifiers(graph["withdrawn_evidence"])
    require(withdrawn <= receipts.keys(), "unknown withdrawal")
    evidence_states = {}
    for rid, receipt in receipts.items():
        admission = admissions[rid]
        require(type(admission) is dict, "invalid admission")
        refute = admission.get("outcome") == "REFUTE"
        fields(admission, ("kind", "scope", "verifier", "assumptions", "source", "outcome", "witness") if refute else ("kind", "scope", "verifier", "assumptions", "source", "outcome"))
        require(admission["kind"] == receipt["kind"] and admission["scope"] == receipt["scope"], "admission scope/kind mismatch")
        require(type(admission["verifier"]) is str and admission["verifier"] in allowed_verifiers, "unapproved verifier")
        require(admission["assumptions"] == [] and type(admission["source"]) is str and admission["source"], "unsupported assumptions or source")
        require(admission["outcome"] in {"SUPPORT", "REFUTE"}, "unsupported evidence outcome")
        if refute:
            countermodel(admission)
        evidence_states[rid] = "REFUTED" if refute else ("SOURCE_DOCUMENTED" if receipt["kind"] == "documentary" else "WARRANTED_BOUNDED")
    require(type(graph["routes"]) is list, "invalid routes")
    for route in graph["routes"]:
        fields(route, ("conclusion", "premises", "evidence"))
        require(type(route["conclusion"]) is str and route["conclusion"] in claims, "unknown conclusion")
        premises, evidence = identifiers(route["premises"]), identifiers(route["evidence"])
        require(premises <= claims.keys() and evidence <= receipts.keys(), "unresolved reference")
        require(premises or evidence, "rootless empty route")
        conclusion = claims[route["conclusion"]]
        for node in [claims[p] for p in premises] + [receipts[e] for e in evidence]:
            require((node["kind"], node["scope"]) == (conclusion["kind"], conclusion["scope"]), "unsupported kind/scope transport")
        if any(evidence_states[e] == "REFUTED" for e in evidence):
            require(not premises and len(evidence) == 1, "refutation route must be a direct checked witness")
    states = {cid: "UNKNOWN" for cid in claims}
    changed = True
    while changed:
        changed = False
        for route in graph["routes"]:
            if any(e in withdrawn for e in route["evidence"]):
                continue
            if any(states[p] not in {"SOURCE_DOCUMENTED", "WARRANTED_BOUNDED"} for p in route["premises"]):
                continue
            cid = route["conclusion"]
            outcome = "SOURCE_DOCUMENTED" if claims[cid]["kind"] == "documentary" else "WARRANTED_BOUNDED"
            if any(evidence_states[e] == "REFUTED" for e in route["evidence"]):
                outcome = "REFUTED"
            require(states[cid] in {"UNKNOWN", outcome}, "conflicting support and refutation")
            if states[cid] == "UNKNOWN":
                states[cid] = outcome
                changed = True
    return dict(sorted(states.items()))


def compare(before, after):
    result = {}
    for cid in sorted(before):
        final = "STALE" if before[cid] != "UNKNOWN" and after[cid] == "UNKNOWN" else after[cid]
        result[cid] = {"before": before[cid], "after": final, "changed": before[cid] != final}
    return result


def content_hash(record, field, expected):
    require(record.get(field) == expected, "wrong canonical content digest")
    payload = {key: value for key, value in record.items() if key != field}
    require(sha(canonical(payload)) == expected, "canonical payload integrity mismatch")


def replay_record(record, jpl, notice, policy):
    """Semantic qualification following byte admission; callable for negative tests."""
    fields(record, ("schema", "id", "snapshot_sha256", "derivation", "interpretation", "publisher_notice", "resolutions", "sources"))
    require(record["schema"] == "mathgraph.living-warrant-snapshot.v1" and record["id"] == RECORD_ID, "unsupported historical identity")
    require(jpl["schema"] == "mathgraph.public-consequence-record.v1" and jpl["id"] == JPL_ID, "wrong JPL record")
    require(jpl["source"]["commit"] == JPL_COMMIT and jpl["source"]["external_suite_commit"] == SUITE_COMMIT, "wrong JPL commits")
    require(jpl["axes"]["finite_executable"]["source_cases"] == 48 and jpl["admission"]["status"] == "WARRANTED_ON_PINNED_BOUNDED_CASES", "wrong bounded receipt")
    sources = record["sources"]
    fields(sources, ("jpl_record_id", "jpl_record_sha256", "openai"))
    require(sources["jpl_record_id"] == JPL_ID and sources["jpl_record_sha256"] == JPL_CONTENT_HASH, "wrong JPL source")
    require(sources["openai"] == {"byte_sha256": PINS["history.md"]["sha256"], "commit": OPENAI_COMMIT, "git_blob_sha1": OPENAI_BLOB, "notice_date": "2026-10-07", "path": "history.md", "url": f"https://github.com/openai/math/blob/{OPENAI_COMMIT}/history.md"}, "wrong publisher source")
    require(len(notice) == 2281 and sha(notice) == PINS["history.md"]["sha256"], "wrong notice bytes")
    require(hashlib.sha1(b"blob " + str(len(notice)).encode() + b"\0" + notice).hexdigest() == OPENAI_BLOB, "wrong Git blob")
    notice_text = notice.decode("utf-8")
    for title in TITLES:
        require("- " + title + "\n" in notice_text, "missing withdrawal")
    documents = [{"editorial_status": "WITHDRAWN_BY_PUBLISHER", "mathematical_truth": "UNKNOWN", "name": title, "original_support_claim": f"openai.original_support.{i}"} for i, title in enumerate(TITLES, 1)]
    require(record["publisher_notice"] == {"cause_as_reported": "sign_error_in_original_argument", "documents": documents, "does_not_imply": "mathematical_theorem_refuted", "kind": "PUBLICATION_WITHDRAWAL"}, "unsupported publisher notice")
    derivation = record["derivation"]
    fields(derivation, ("claims", "receipts", "routes", "withdrawn_evidence", "receipt_admission"))
    require(derivation["receipt_admission"] == {"documentary": "exact pinned OpenAI history notice", "formal": "exact pinned JPL finite parser receipt"}, "unsupported receipt contract")
    expected_claims, expected_receipts, expected_admissions = [], [], {}
    for i, title in enumerate(TITLES, 1):
        scope = f"openai/math:{title}:original-withdrawn-edition"
        expected_claims.extend([{"id": f"openai.original_support.{i}", "kind": "documentary", "scope": scope}, {"id": f"openai.theorem.{i}", "kind": "formal", "scope": scope}])
        rid = f"openai.original_publication_receipt.{i}"
        expected_receipts.append({"id": rid, "kind": "documentary", "scope": scope})
        expected_admissions[rid] = {"kind": "documentary", "scope": scope, "verifier": "pinned-publisher-notice-v1", "source": "history.md", "assumptions": [], "outcome": "SUPPORT"}
    expected_claims.append({"id": "jpl.l4yaml.finite_parser_acceptance", "kind": "formal", "scope": JPL_SCOPE})
    rid = "mathgraph.l4yaml.48-case-qualification"
    expected_receipts.append({"id": rid, "kind": "formal", "scope": JPL_SCOPE})
    expected_admissions[rid] = {"kind": "formal", "scope": JPL_SCOPE, "verifier": "pinned-jpl-qualified-receipt-v1", "source": "jpl-record.json", "assumptions": [], "outcome": "SUPPORT"}
    require(typed_index(derivation["claims"]) == typed_index(expected_claims), "wrong historical claims")
    require(typed_index(derivation["receipts"]) == typed_index(expected_receipts), "wrong historical receipts")
    require(policy["admissions"] == expected_admissions, "unapproved historical admissions")
    require(derivation["withdrawn_evidence"] == [f"openai.original_publication_receipt.{i}" for i in range(1, 4)], "wrong historical withdrawals")
    graph = {k: v for k, v in derivation.items() if k != "receipt_admission"}
    before = resolve({**graph, "withdrawn_evidence": []}, policy["admissions"], HISTORICAL_VERIFIERS)
    after = resolve(graph, policy["admissions"], HISTORICAL_VERIFIERS)
    resolutions = compare(before, after)
    require(canonical(record["resolutions"]) == canonical(resolutions), "producer status assertion mismatch")
    return resolutions


def replay(bundle_raw, policy_raw, policy_sha256):
    require(type(policy_sha256) is str and len(policy_sha256) == 64 and sha(policy_raw) == policy_sha256, "external policy SHA-256 mismatch")
    policy = parse_json(policy_raw)
    fields(policy, ("schema", "members", "provenance", "admissions"))
    require(policy["schema"] == "mathgraph.resolve-trust-policy.v1", "unsupported policy")
    require(canonical(policy["members"]) == canonical(PINS) and canonical(policy["provenance"]) == canonical(PROVENANCE), "unsupported authority profile")
    require(canonical(policy) + b"\n" == policy_raw, "policy must be canonical JSON")
    bundle = parse_json(bundle_raw)
    fields(bundle, ("schema", "members", "provenance"))
    require(bundle["schema"] == "mathgraph.resolve-bundle.v1", "unsupported bundle schema")
    require(canonical(bundle) + b"\n" == bundle_raw, "bundle must be canonical JSON")
    require(canonical(bundle["provenance"]) == canonical(policy["provenance"]), "provenance mismatch")
    fields(bundle["members"], PINS)
    decoded = {}
    for name, pin in policy["members"].items():
        member = bundle["members"][name]
        fields(member, ("encoding", "data", "size", "sha256"))
        require(member["encoding"] == "base64" and type(member["data"]) is str, "unsupported member transport")
        require(type(member["size"]) is int and member["size"] == pin["size"] and member["sha256"] == pin["sha256"], "member pin mismatch")
        raw = base64.b64decode(member["data"], validate=True)
        require(base64.b64encode(raw).decode("ascii") == member["data"], "noncanonical base64")
        require(len(raw) == pin["size"] and sha(raw) == pin["sha256"], "member bytes mismatch")
        decoded[name] = raw
    record, jpl = parse_json(decoded["record.json"]), parse_json(decoded["jpl-record.json"])
    content_hash(record, "snapshot_sha256", SNAPSHOT_HASH)
    content_hash(jpl, "content_sha256", JPL_CONTENT_HASH)
    resolutions = replay_record(record, jpl, decoded["history.md"], policy)
    return {"schema": "mathgraph.resolve-replay-report.v1", "record_id": RECORD_ID,
            "bundle_sha256": sha(bundle_raw), "trust_policy_sha256": policy_sha256,
            "historical_evidence_qualification": "PINNED_INPUTS_QUALIFIED_UNDER_POLICY",
            "historical_resolution": resolutions, "current_applicability": "UNKNOWN",
            "freshness": "NOT_CHECKED", "lifecycle": "IMMUTABLE_HISTORICAL_SNAPSHOT",
            "revocation_or_supersession": "NOT_CHECKED",
            "action_authorization": "NONE", "original_jpl_lean_rerun": False,
            "provenance": PROVENANCE}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--policy-sha256", required=True, help="Trusted SHA-256 supplied outside the bundle")
    parser.add_argument("--audit-imports", action="store_true")
    args = parser.parse_args()
    try:
        result = replay(args.bundle.read_bytes(), args.policy.read_bytes(), args.policy_sha256)
        if args.audit_imports:
            origins = {name: str(Path(module.__file__).resolve()) for name, module in sorted(sys.modules.items()) if name != "__main__" and getattr(module, "__file__", None)}
            require(all("site-packages" not in path and Path(path).is_relative_to(Path(sys.base_prefix).resolve()) for path in origins.values()), "non-stdlib import")
            print(canonical({"import_origins": origins}).decode(), file=sys.stderr)
        print(canonical(result).decode())
    except (ValueError, KeyError, TypeError, OSError) as error:
        print("REPLAY_REJECTED: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
