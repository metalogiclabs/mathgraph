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

def conditional_minimum_evidence_sets(rules, evidence, claims, *, target="G1"):
    """Exact unit-cost set minimization, no actual evidence qualification.

    Exhaustive baseline enumerates subsets in cardinality order. A separate
    recursive DAG oracle agrees for each tested subset. Minimality is therefore
    certified only inside these hand-chosen AND/OR semantics and unit costs.
    """
    from itertools import combinations
    refs = tuple(sorted(evidence))
    if target not in claims:
        raise ValueError("target is not a claim")
    tested = 0
    winning = []
    for count in range(len(refs) + 1):
        for combination in combinations(refs, count):
            tested += 1
            accepted = set(combination)
            fast = target in evaluate(rules, accepted, policy="any", claims=claims)
            independent = target in oracle_recursive(
                rules, accepted, policy="any", claims=claims)
            if fast != independent:
                raise AssertionError("minimum-set oracle divergence")
            if fast:
                winning.append(list(combination))
        if winning:
            break
    if not winning:
        return {"obstruction": "NO_ALLOWED_SUPPORT_SET", "tested": tested}
    all_assumed = set(refs)
    all_policy_initial = target in evaluate(
        rules, all_assumed, policy="all", claims=claims)
    if not all_policy_initial:
        raise AssertionError("all-relations baseline is not supported")
    necessary_under_all = [
        ref for ref in refs if target not in evaluate(
            rules, all_assumed - {ref}, policy="all", claims=claims)]
    # A monotone formula with every input individually necessary cannot be
    # supported by any proper subset. This is a finite combinatorial fact,
    # not a conclusion about the real meaning of the SACM argument.
    return {
        "unit_cost_only": True,
        "all_source_receipts_hypothetically_qualified": True,
        "any_policy_minimum_number": len(winning[0]),
        "any_policy_minimal_sets": winning,
        "exhaustive_subsets_evaluated": tested,
        "independent_recursive_baseline_for_every_tested_subset": True,
        "all_policy_individually_necessary_evidence_references": necessary_under_all,
        "all_policy_minimum_number_if_all_necessary": len(necessary_under_all)
            if len(necessary_under_all) == len(refs) else "NOT_DETERMINED",
        "unsafe_to_use_for_release": True,
        "actual_evidence_warrants": "UNKNOWN"
    }


def mixed_policy_evaluation(rules, evidence, claims, choices):
    """Least supported fixpoint given explicit per-claim assumptions."""
    accepted = set(evidence)
    supported = set()
    for _ in range(len(claims) + 1):
        changed = set(supported)
        for claim in claims:
            rule_list = rules.get(claim, ())
            if not rule_list:
                continue
            satisfied = [all(x in accepted or x in supported for x in rel.inputs)
                         for rel in rule_list]
            mode = choices.get(claim, "all")
            if mode not in ("all", "any"):
                raise ValueError(f"unsupported rule-combination policy for {claim}")
            if all(satisfied) if mode == "all" else any(satisfied):
                changed.add(claim)
        if changed == supported:
            return frozenset(changed)
        supported = changed
    raise ValueError("mixed policy closure did not converge")

def mixed_oracle(rules, evidence, claims, choices):
    """Independent recursive evaluator, separate from iterative closure."""
    accepted = set(evidence)
    memo = {}
    pending = set()
    def check(c):
        if c in memo:
            return memo[c]
        if c in pending:
            raise ValueError("cyclic support graph")
        pending.add(c)
        inc = rules.get(c, ())
        flags = []
        for rel in inc:
            flags.append(all((x in accepted) if x not in claims else check(x)
                             for x in rel.inputs))
        mode = choices.get(c, "all")
        if mode not in ("all", "any"):
            raise ValueError("unrecognized policy")
        answer = bool(flags) and (all(flags) if mode == "all" else any(flags))
        pending.remove(c)
        memo[c] = answer
        return answer
    return frozenset(c for c in claims if check(c))

def minimal_policy_question(rules, evidence, claims, withdrawal, target="G1"):
    """Enumerate the finite per-claim policy grammar; find smallest query.

    This is a *policy-ambiguity separating question*, not proof of source
    semantics, real sufficiency of alternatives or real safety.
    """
    from itertools import combinations, product
    ambiguous = sorted(c for c,r in rules.items() if len(r)>1)
    if len(ambiguous) > 12:
        raise ValueError("finite enumeration limit; result UNKNOWN")
    outcomes = {}
    for modes in product(("any","all"), repeat=len(ambiguous)):
        choice = dict(zip(ambiguous,modes))
        active = set(evidence)-{withdrawal}
        out = mixed_policy_evaluation(rules,active,claims,choice)
        independent = mixed_oracle(rules,active,claims,choice)
        if out != independent:
            raise AssertionError(f"mixed-policy oracle mismatch {choice}")
        key = tuple(modes)
        outcomes[key] = target in out
    minima=[]
    for k in range(len(ambiguous)+1):
        for subset in combinations(range(len(ambiguous)),k):
            partition = {}
            for assignment, outcome in outcomes.items():
                x = tuple(assignment[i] for i in subset)
                partition.setdefault(x,set()).add(outcome)
            if all(len(v)==1 for v in partition.values()):
                minima.append(tuple(ambiguous[i] for i in subset))
        if minima:
            break
    if not minima:
        raise AssertionError("full policy assignment should determine result")
    counts = {"conditional_support_present":sum(outcomes.values()),
              "no_conditional_support":sum(not o for o in outcomes.values())}
    return {
        "finite_policy_space":len(outcomes),
        "claims_with_multiple_incoming_relations":ambiguous,
        "conditional_top_claim_outcomes":counts,
        "minimum_number_of_policy_questions":len(minima[0]),
        "all_minimal_question_sets":[list(q) for q in minima],
        "first_minimum_question_wording":(
            "For claim "+minima[0][0]+
            ", are all incoming argument relationships mandatory, or may"
            " one complete relationship suffice, and what exact reviewed"
            " safety-case policy authorizes that choice?"
        ) if len(minima[0]) == 1 else "Clarify source-authoritative aggregation policy",
        "independently_checked_assignments":len(outcomes),
        "source_policy_authority": "NOT_AVAILABLE",
        "actual_claim_verdict":"UNKNOWN",
        "consequential_action_authorized":False
    }

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
    minimum = conditional_minimum_evidence_sets(rules, evidence, case.claims)
    question = minimal_policy_question(rules, evidence, case.claims, withdrawal)
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
        "conditional_minimum_support_ambiguity": minimum,
        "smallest_separating_policy_question": question,
        "actual_warrant": "UNKNOWN",
        "safety_certification": "NOT_ASSESSED",
        "Kry10_deployed_system": "NOT_TESTED"
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python assurance_policy_envelope.py OASC.xml")
    result = audit(parse_case(Path(sys.argv[1]).read_bytes()))
    print(json.dumps(result,indent=2))
