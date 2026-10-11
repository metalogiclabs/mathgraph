#!/usr/bin/env python3
"""Exact finite-profile qualifier. Standard library only; no producer imports.

Truth vectors are integer masks. A closure is the subset of all 256 masks
respecting pairwise observational equality, cross-checked by cell cardinality.
Only an externally pinned policy and successful replay can produce a receipt.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

PROFILE = "mathgraph.finite-representation-refinement.v1"
SCOPE = ("Exactly the eight ordered 3-bit states; deterministic Boolean policies on "
         "observational cells; the fixed five named refinements and all 256 Boolean "
         "one-bit refinements; discovery bit0 AND parity and reuse bit0 OR parity.")
BASIS = "same-owner implementation-independent qualification"
ASSUMPTIONS = ["The carrier is exactly the ordered 3-bit Boolean cube.",
               "Policies are total deterministic Boolean functions of the declared observations.",
               "Source-distinct reuse means two different target functions in the same owned source; it is not external adoption."]
PRECONDITIONS = ["All eight states, complete truth vectors, and the entire declared mask ranges are supplied."]
GUARANTEES = ["Exact old exclusion and obstruction, unique named-family repair, sham failure, ablation, full old-closure retention, and distinct reuse.",
              "All 256 Boolean one-bit refinements are checked: 32 succeed in eight induced partition classes."]
LIMITATIONS = ["Finite scope only; no universal invention theorem or autonomous improvement claim.",
              "Same-owner implementation-independent qualification, not external adoption or independent organizational trust.",
              "Named-family uniqueness is not global feature uniqueness; no historical preregistration is claimed.",
              "No freshness, revocation, supersession, present applicability, or action authorization is established."]
BASE = "conformance/capability_v1/"


class Rejected(ValueError):
    """Stable fail-closed reason code; not a refutation of mathematics."""


def require(condition, code):
    if not condition:
        raise Rejected(code)


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_KEY")
            result[key] = value
        return result

    def constant(_):
        raise Rejected("NONFINITE_NUMBER")

    def number(text):
        value = float(text)
        require(math.isfinite(value), "NONFINITE_NUMBER")
        return value

    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant, parse_float=number)
    except (ValueError, UnicodeError) as error:
        if isinstance(error, Rejected):
            raise
        raise Rejected("INVALID_JSON") from error
    require(type(value) is dict, "OBJECT_REQUIRED")
    return value


def fields(value, names):
    require(type(value) is dict and set(value) == set(names.split()), "INVALID_FIELDS")


def artifact(value):
    fields(value, "id locator sha256 size_bytes media_type")
    require(all(type(value[key]) is str and value[key].strip() for key in
                ("id", "locator", "media_type")), "INVALID_ARTIFACT")
    require(type(value["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]), "INVALID_DIGEST")
    require(type(value["size_bytes"]) is int and value["size_bytes"] >= 0, "INVALID_SIZE")


def reference(identifier, locator, raw, media_type="application/json"):
    return {"id": identifier, "locator": locator, "sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw), "media_type": media_type}


def verify_pin(raw, ref, code):
    artifact(ref)
    require(len(raw) == ref["size_bytes"] and hashlib.sha256(raw).hexdigest() == ref["sha256"], code)


def validate_structure(contract):
    """Descriptor syntax is independent of trust and supported-profile semantics."""
    fields(contract, "schema_version id version profile claim inputs outputs preconditions guarantees assumptions boundary implementation evidence limitations extensions")
    require(contract["schema_version"] == "mathgraph.capability-contract.v1", "UNSUPPORTED_CONTRACT")

    def text(value):
        require(type(value) is str and value.strip(), "INVALID_TEXT")

    def unique_ids(items, key="id"):
        require(len({item[key] for item in items}) == len(items), "DUPLICATE_ID")

    for key in ("id", "version", "profile"):
        text(contract[key])
    fields(contract["claim"], "id kind scope")
    for value in contract["claim"].values():
        text(value)
    for key in ("preconditions", "guarantees", "assumptions", "limitations"):
        require(type(contract[key]) is list, "INVALID_LIST")
        for value in contract[key]:
            text(value)
    require(contract["guarantees"] and contract["limitations"], "EMPTY_CONTRACT_BOUNDARY")
    refs = [contract["boundary"], contract["implementation"]]
    for key in ("inputs", "outputs"):
        require(type(contract[key]) is list and contract[key], "INVALID_TYPES")
        for item in contract[key]:
            fields(item, "type_id schema")
            text(item["type_id"])
            refs.append(item["schema"])
        unique_ids(contract[key], "type_id")
    require(type(contract["evidence"]) is list, "INVALID_EVIDENCE")
    refs.extend(contract["evidence"])
    by_id = {}
    for ref in refs:
        artifact(ref)
        require(ref["id"] not in by_id or by_id[ref["id"]] == ref, "CONFLICTING_ARTIFACT_ID")
        by_id[ref["id"]] = ref
    unique_ids(contract["evidence"])
    require(type(contract["extensions"]) is list, "INVALID_EXTENSIONS")
    for item in contract["extensions"]:
        fields(item, "id version critical payload")
        text(item["id"])
        text(item["version"])
        require(type(item["critical"]) is bool and type(item["payload"]) is dict, "INVALID_EXTENSION")
    unique_ids(contract["extensions"])


def validate_contract(contract):
    """Exact profile binding after structural validation and byte-pin checks."""
    require(contract["profile"] == PROFILE, "UNSUPPORTED_PROFILE")
    require(contract["id"] == "urn:mathgraph:capability:finite-developmental-growth" and
            contract["version"] == "1", "IDENTITY_MISMATCH")
    require(contract["claim"] == {"id": "urn:mathgraph:claim:finite-representation-refinement:v1",
                                 "kind": "bounded-finite-representation-refinement", "scope": SCOPE}, "SCOPE_MISMATCH")
    for name, expected in (("preconditions", PRECONDITIONS), ("assumptions", ASSUMPTIONS),
                           ("guarantees", GUARANTEES), ("limitations", LIMITATIONS)):
        require(contract[name] == expected, name.upper() + "_MISMATCH")
    require(contract["extensions"] == [], "UNSUPPORTED_EXTENSION")
    refs = [contract["boundary"], contract["implementation"]]
    for name, type_id in (("inputs", PROFILE), ("outputs", "mathgraph.capability-evaluation.v1")):
        require(type(contract[name]) is list and len(contract[name]) == 1, "INVALID_TYPES")
        item = contract[name][0]
        fields(item, "type_id schema")
        require(item["type_id"] == type_id, "TYPE_MISMATCH")
        refs.append(item["schema"])
    require(type(contract["evidence"]) is list and len(contract["evidence"]) == 1, "INVALID_EVIDENCE")
    refs.extend(contract["evidence"])
    for ref in refs:
        artifact(ref)
    require(len({ref["id"] for ref in refs}) == len(refs), "DUPLICATE_ARTIFACT_ID")
    # Only original sources are provenance. A receipt/evaluation is never evidence
    # to this qualifier, so there is no self-attestation or circular admission path.
    require(contract["implementation"]["locator"] == "experiments/developmental_capability_growth_v1/run.py" and
            contract["evidence"][0]["locator"] == "experiments/developmental_capability_growth_v1/audit_all_boolean_refinements.py",
            "SOURCE_MISMATCH")


def vector(value, maximum=1):
    require(type(value) is list and len(value) == 8 and
            all(type(bit) is int and 0 <= bit <= maximum for bit in value), "INVALID_VECTOR")
    return tuple(value)


def mask(values):
    return sum(bit << index for index, bit in enumerate(values))


def relation(observations):
    return [(i, j) for i in range(8) for j in range(i + 1, 8) if observations[i] == observations[j]]


def closure(observations):
    equal_pairs = relation(observations)
    # Enumerate all Boolean functions over the carrier and filter by equality.
    result = {candidate for candidate in range(256)
              if all(((candidate >> i) & 1) == ((candidate >> j) & 1) for i, j in equal_pairs)}
    require(len(result) == 2 ** len(set(observations)), "CLOSURE_CROSSCHECK_FAILED")
    return result


def signature(observations):
    # Each state maps to the first indistinguishable state's index, independent
    # of observation spelling; this identifies partitions without producer cells.
    return tuple(observations.index(value) for value in observations)


def witness(observations, target):
    result = []
    for observation in sorted(set(observations)):
        indices = [i for i in range(8) if observations[i] == observation]
        labels = {(target >> i) & 1 for i in indices}
        require(len(labels) == 1, "WITNESS_CONFLICT")
        result.append({"observations": list(observation), "output": labels.pop()})
    # Replay the resulting lookup at every state, not only one cell representative.
    lookup = {tuple(row["observations"]): row["output"] for row in result}
    require(mask([lookup[x] for x in observations]) == target, "WITNESS_REPLAY_FAILED")
    return result


def replay(data):
    fields(data, "schema_version profile scope states features targets baseline_features named_family selected_refinement sham_refinement refined_features ablated_features retained_targets coverage")
    require(data["schema_version"] == "mathgraph.finite-profile-input.v1" and data["profile"] == PROFILE,
            "UNSUPPORTED_PROFILE")
    require(data["scope"] == SCOPE, "SCOPE_MISMATCH")
    expected_states = [[(n >> 2) & 1, (n >> 1) & 1, n & 1] for n in range(8)]
    states = data["states"]
    require(type(states) is list and len(states) == 8 and all(
        type(row) is list and len(row) == 3 and all(type(bit) is int and bit in (0, 1) for bit in row)
        for row in states) and states == expected_states, "CARRIER_MISMATCH")
    fields(data["coverage"], "policy_masks refinement_masks")
    require(encode(data["coverage"]) == encode({"policy_masks": [0, 256], "refinement_masks": [0, 256]}),
            "INCOMPLETE_COVERAGE")
    fields(data["features"], "parity bit0 bit1 bit2 weight constant_zero")
    features = {name: vector(values, 3 if name == "weight" else 1)
                for name, values in data["features"].items()}
    for axis in range(3):
        require(features[f"bit{axis}"] == tuple(row[axis] for row in states), "REFINEMENT_MISMATCH")
    require(features["weight"] == tuple(sum(row) for row in states) and
            features["parity"] == tuple(sum(row) % 2 for row in states) and
            features["constant_zero"] == (0,) * 8, "FEATURE_MISMATCH")
    fields(data["targets"], "discovery reuse")
    targets = {}
    for name, source in (("discovery", "target_discovery"), ("reuse", "target_transfer")):
        item = data["targets"][name]
        fields(item, "source vector")
        require(item["source"] == "experiments/developmental_capability_growth_v1/run.py#" + source,
                "TARGET_SOURCE_MISMATCH")
        targets[name] = mask(vector(item["vector"]))
    a, p = features["bit0"], features["parity"]
    require(targets["discovery"] == mask([x & y for x, y in zip(a, p)]) and
            targets["reuse"] == mask([x | y for x, y in zip(a, p)]), "TARGET_MISMATCH")
    family = ["bit0", "bit1", "bit2", "weight", "constant_zero"]
    for field, expected in (("baseline_features", ["parity"]), ("named_family", family),
                            ("selected_refinement", "bit0"), ("sham_refinement", "bit1"),
                            ("refined_features", ["parity", "bit0"]), ("ablated_features", ["parity"])):
        require(data[field] == expected, field.upper() + "_MISMATCH")

    def observations(names):
        return [tuple(features[name][i] for name in names) for i in range(8)]

    old = observations(data["baseline_features"])
    refined = observations(data["refined_features"])
    sham = observations(["parity", data["sham_refinement"]])
    # Remove the supplied selected feature from the actual refined observation.
    ablated_names = [name for name in data["refined_features"] if name != data["selected_refinement"]]
    require(ablated_names == data["ablated_features"], "ABLATION_MISMATCH")
    ablated = observations(ablated_names)
    old_set, new_set, sham_set, ablated_set = map(closure, (old, refined, sham, ablated))
    target, reuse = targets["discovery"], targets["reuse"]
    conflicts = [(i, j) for i, j in relation(old) if ((target >> i) & 1) != ((target >> j) & 1)]
    successes = [name for name in family if target in closure(observations(["parity", name]))]
    require(type(data["retained_targets"]) is list, "INVALID_RETENTION")
    retained = [mask(vector(item)) for item in data["retained_targets"]]
    require(len(retained) == len(set(retained)) and set(retained) == old_set, "INCOMPLETE_RETENTION")
    checks = {
        "old_exclusion_with_obstruction": target not in old_set and bool(conflicts),
        "unique_named_family_repair": successes == ["bit0"],
        "non_tautological_feature": mask(a) not in (target, reuse),
        "new_witness": target in new_set,
        "same_shape_sham_failure": len(set(sham)) == len(set(refined)) and target not in sham_set,
        "ablation_restores_obstruction": signature(ablated) == signature(old) and target not in ablated_set,
        "retains_entire_old_closure": old_set <= new_set,
        "distinct_reuse": target != reuse and reuse not in old_set and reuse in new_set and reuse not in sham_set,
    }
    successful_masks, partitions, distribution = [], set(), {}
    for candidate in range(256):
        observations_one_bit = [(p[i], (candidate >> i) & 1) for i in range(8)]
        brute = target in closure(observations_one_bit)
        analytic = all(((target >> i) & 1) == ((target >> j) & 1)
                       for i, j in relation(observations_one_bit))
        separates = all(((candidate >> i) & 1) != ((candidate >> j) & 1) for i, j in conflicts)
        require(brute == analytic == separates, "REFINEMENT_CROSSCHECK_FAILED")
        if brute:
            successful_masks.append(candidate)
            partitions.add(signature(observations_one_bit))
            count = str(len(set(observations_one_bit)))
            distribution[count] = distribution.get(count, 0) + 1
    checks["complete_refinement_audit"] = (len(successful_masks) == 32 and len(partitions) == 8 and
                                           distribution == {"3": 4, "4": 28})
    require(all(checks.values()), "FINITE_GATE_FAILED")
    return {"old_closure_masks": sorted(old_set), "obstruction_pairs": [list(pair) for pair in conflicts],
            "successful_named_refinements": successes, "discovery_mask": target, "reuse_mask": reuse,
            "discovery_witness": witness(refined, target), "reuse_witness": witness(refined, reuse),
            "refined_closure_size": len(new_set), "retained_closure_masks": sorted(old_set & new_set),
            "boolean_refinements_tested": 256, "successful_refinements": len(successful_masks),
            "failed_refinements": 256 - len(successful_masks), "successful_partition_classes": len(partitions),
            "successful_cell_count_distribution": distribution, "successful_refinement_masks": successful_masks,
            "successful_partition_signatures": [list(partition) for partition in sorted(partitions)], "checks": checks}


def qualify(fixture_raw, contract_raw, policy_raw, expected_policy_sha256):
    evaluation = {"schema_version": "mathgraph.capability-evaluation.v1", "contract": None,
                  "contract_sha256": None, "contract_size_bytes": None, "validation": "INVALID",
                  "qualification": "UNKNOWN", "qualification_receipt": None, "trust_policy": None,
                  "freshness": "NOT_CHECKED", "revocation": "NOT_CHECKED", "supersession": "NOT_CHECKED",
                  "current_applicability": "UNKNOWN", "action_authorization": "NONE", "reason_codes": []}
    try:
        contract = decode(contract_raw)
        validate_structure(contract)
        evaluation.update(validation="VALID", contract={key: contract[key] for key in ("id", "version", "profile")},
                          contract_sha256=hashlib.sha256(contract_raw).hexdigest(), contract_size_bytes=len(contract_raw))
        data, policy = map(decode, (fixture_raw, policy_raw))
        require(type(expected_policy_sha256) is str and
                hashlib.sha256(policy_raw).hexdigest() == expected_policy_sha256, "TRUST_POLICY_PIN_MISMATCH")
        fields(policy, "schema_version id profile transport contract fixture verifier qualification_basis")
        require(policy["schema_version"] == "mathgraph.finite-trust-policy.v1" and
                policy["id"] == "urn:mathgraph:policy:finite-refinement:v1", "UNSUPPORTED_POLICY")
        require(policy["transport"] == "local-exact-bytes", "UNSUPPORTED_TRANSPORT")
        require(policy["profile"] == PROFILE, "UNSUPPORTED_PROFILE")
        require(policy["qualification_basis"] == BASIS, "UNSUPPORTED_QUALIFICATION_BASIS")
        verify_pin(contract_raw, policy["contract"], "CONTRACT_PIN_MISMATCH")
        verify_pin(fixture_raw, policy["fixture"], "FIXTURE_PIN_MISMATCH")
        verify_pin(Path(__file__).read_bytes(), policy["verifier"], "VERIFIER_PIN_MISMATCH")
        validate_contract(contract)
        require(contract["boundary"] == policy["fixture"], "BOUNDARY_MISMATCH")
        facts = replay(data)
        policy_ref = reference(policy["id"], BASE + "trust-policy.json", policy_raw)
        receipt = {"schema_version": "mathgraph.finite-qualification-receipt.v1", "qualification": "QUALIFIED_BOUNDED",
                   "basis": BASIS, "scope": SCOPE, "limitations": LIMITATIONS,
                   "contract": policy["contract"], "fixture": policy["fixture"],
                   "verifier": policy["verifier"], "trust_policy": policy_ref, "replay": facts}
        receipt_ref = reference("urn:mathgraph:receipt:finite-refinement:v1", BASE + "receipt.json", encode(receipt))
        evaluation.update(qualification="QUALIFIED_BOUNDED", qualification_receipt=receipt_ref,
                          trust_policy=policy_ref, reason_codes=["EXACT_FINITE_REPLAY_PASSED", "SAME_OWNER_INDEPENDENT_IMPLEMENTATION"])
        return {"evaluation": evaluation, "receipt": receipt}
    except (Rejected, OSError, TypeError, KeyError, OverflowError, RecursionError) as error:
        evaluation["reason_codes"] = [str(error) if isinstance(error, Rejected) else "INVALID_INPUT"]
        return {"evaluation": evaluation, "receipt": None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--policy-sha256", required=True)
    parser.add_argument("--audit-imports", action="store_true")
    args = parser.parse_args()
    try:
        result = qualify(Path(args.fixture).read_bytes(), Path(args.contract).read_bytes(),
                         Path(args.policy).read_bytes(), args.policy_sha256)
    except OSError:
        result = qualify(b"{}", b"{}", b"{}", args.policy_sha256)
    sys.stdout.buffer.write(encode(result))
    if args.audit_imports:
        nonstdlib = sorted({name.split(".")[0] for name in sys.modules
                            if name != "__main__" and name.split(".")[0] not in sys.stdlib_module_names})
        print(json.dumps({"nonstdlib_modules": nonstdlib, "isolated": bool(sys.flags.isolated),
                          "no_site": bool(sys.flags.no_site)}, sort_keys=True), file=sys.stderr)
    return 0 if result["receipt"] is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
