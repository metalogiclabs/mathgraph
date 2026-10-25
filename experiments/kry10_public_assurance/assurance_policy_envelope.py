#!/usr/bin/env python3
"""SACM conditional support-policy envelope. Not a proof or certification verdict.

Distinct asserted relationships into one claim can be treated as all required
or any sufficient ONLY under explicitly hypothetical policy choices. SACM does
not automatically endorse either. A missing supporting artifact never becomes
warranted merely because a path exists.

Source parser: sacm_transfer.py (pinned OASC public XML).
"""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
import json
import sys
from pathlib import Path

from sacm_transfer import parse_case, OASC_COMMIT, OASC_BLOB

@dataclass(frozen=True)
class Rule:
    name: str
    target: str
    inputs: tuple[str, ...]

def compile_rules(case):
    """Preserve each named inference as one conjunctive hyperedge."""
    collected = {}
    evidence_inputs = set()
    for kind, links in (("evidence", case.evidence_edges), ("inference", case.inference_edges)):
        for source, target, identifier in links:
            key = (kind, identifier)
            if key not in collected:
                collected[key] = (target, [])
            if collected[key][0] != target:
                raise ValueError("one relationship has multiple targets")
            collected[key][1].append(source)
            if kind == "evidence":
                evidence_inputs.add(source)
    by_target = defaultdict(list)
    for (kind, name), (target, sources) in sorted(collected.items()):
        if not sources:
            raise ValueError("empty premise set")
        if kind == "evidence" and not all(s in case.references for s in sources):
            raise ValueError("invalid evidence premise")
        if kind == "inference" and not all(s in case.claims for s in sources):
            raise ValueError("invalid inference premise")
        by_target[target].append(Rule(kind + ":" + name, target, tuple(sorted(set(sources)))))
    return dict(by_target), evidence_inputs

def evaluate(rules, accepted_evidence, *, policy, claims):
    """Least grounded fixed point of declared AND premises, all/any rule policy.

    Returns *conditionally supported* claim names only. The caller must
    separately verify artifact authenticity, claim-to-evidence correspondence,
    time and context before calling anything warranted.
    """
    if policy not in ("all", "any"):
        raise ValueError("policy must be all or any")
    accepted = set(accepted_evidence)
    qualified = set()
    for _ in range(len(claims) + 1):
        add = set()
        for claim in claims:
            incoming = rules.get(claim, ())
            if not incoming:
                continue
            statuses = [all(s in accepted or s in qualified for s in rule.inputs)
                        for rule in incoming]
            if (all(statuses) if policy == "all" else any(statuses)):
                add.add(claim)
        grown = qualified | add
        if grown == qualified:
            return frozenset(qualified)
        qualified = grown
    raise ValueError("nonconvergent evidence closure")

def oracle_recursive(rules, accepted_evidence, *, policy, claims):
    """Independent recursive DAG evaluator (not the fixed-point engine)."""
    accepted = set(accepted_evidence)
    cache = {}
    pending = set()
    def visit(claim):
        if claim in cache:
            return cache[claim]
        if claim in pending:
            raise ValueError("cyclic model")
        pending.add(claim)
        incoming = rules.get(claim, ())
        conditions = [
            all((s in accepted) if s not in claims else visit(s) for s in rule.inputs)
            for rule in incoming
        ]
        answer = bool(conditions) and (
            all(conditions) if policy == "all" else any(conditions))
        pending.remove(claim)
        cache[claim] = answer
        return answer
    return frozenset(c for c in claims if visit(c))

def audit(case, withdrawal="EV_63"):
    rules, evidence = compile_rules(case)
    if withdrawal not in evidence:
        raise ValueError("withdrawal must be a cited evidence reference")
    before = {}
    after = {}
    for policy in ("all", "any"):
        before[policy] = evaluate(rules, evidence, policy=policy, claims=case.claims)
        after[policy] = evaluate(rules, evidence - {withdrawal},
                                 policy=policy, claims=case.claims)
        for flag, got, auth in (("before", before[policy], evidence),
                                ("after", after[policy], evidence-{withdrawal})):
            independent = oracle_recursive(rules, auth, policy=policy, claims=case.claims)
            if got != independent:
                raise AssertionError(f"independent oracle mismatch: {policy}:{flag}")
    lost = {k:before[k]-after[k] for k in before}
    intersection = set.intersection(*(set(x) for x in lost.values()))
    union = set.union(*(set(x) for x in lost.values()))
    alternative = sorted(union - intersection)
    # This conditional exercise assumes all 23 "Evidence" references possess
    # authenticated, relevant and temporally current receipts. No such receipts
    # were present in the public source. Never make an actual warrant claim.
    return {
        "source": "EdgeCaseResearch/oasc, NOT Kry10",
        "commit": OASC_COMMIT,
        "source_blob": OASC_BLOB,
        "scope": "HYPOTHETICAL_ALL_RECEIPTS_QUALIFIED",
        "receipt_authenticity_in_source": "NONE_ESTABLISHED",
        "support_policy_from_source": "NOT_SPECIFIED_FOR_AUTOMATED_WARRANT",
        "withdrawal": withdrawal,
        "hypothetical_baseline_supported": {p:len(x) for p,x in before.items()},
        "hypothetical_after_supported": {p:len(x) for p,x in after.items()},
        "all_required_lost": sorted(lost["all"]),
        "any_sufficient_lost": sorted(lost["any"]),
        "lost_under_both_hypothetical_policies": sorted(intersection),
        "policy_dependent_loss": alternative,
        "root_support_after": {p:"CONDITIONAL_PATH_PRESENT" if "G1" in after[p]
                               else "NO_CONDITIONAL_PATH" for p in after},
        "independently_checked_with": "recursive_DAG_oracle",
        "actual_warrant": "UNKNOWN",
        "safety_certification": "NOT_ASSESSED",
        "Kry10_deployed_system": "NOT_TESTED"
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python assurance_policy_envelope.py OASC.xml")
    result = audit(parse_case(Path(sys.argv[1]).read_bytes()))
    print(json.dumps(result,indent=2))
