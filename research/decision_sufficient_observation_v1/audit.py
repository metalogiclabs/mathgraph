#!/usr/bin/env python3
"""Independently test decision sufficiency vs the immutable V1 exact-quotient compiler.

This is a finite logical/API-contract falsifier, NOT a new scientific experiment
or evidence of more efficient synthesis than a conventional exact optimizer.
"""
from collections import Counter
from itertools import combinations, product
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from consequence_experiment_compiler_v1.compiler import compile_experiment

PINNED_V1 = "158681f999d1aa3336a09a7f66c52dc9cf7d925a"

def canon(seq):
    seen = {}
    return tuple(seen.setdefault(x, len(seen)) for x in seq)

def partitions(n):
    return sorted({canon(seq) for seq in product(range(n), repeat=n)})

def kernel(seq):
    return frozenset((i, j) for i, j in combinations(range(len(seq)), 2)
                     if seq[i] == seq[j])

def measure(sensors, subset, n):
    return tuple(tuple(sensors[j][i] for j in subset) for i in range(n))

def independent_opt(sensors, goal, mode):
    """Brute force every subset; never import the original optimizer's rules."""
    target = kernel(goal)
    for k in range(len(sensors)+1):
        for indexes in combinations(range(len(sensors)), k):
            out = measure(sensors, indexes, len(goal))
            found = kernel(out)
            ok = (found == target) if mode == "exact" else (found <= target)
            if ok:
                decoder = {}
                if mode == "sufficient":
                    for observed, answer in zip(out, goal):
                        if observed in decoder and decoder[observed] != answer:
                            raise AssertionError("Nonfunctional factorization")
                        decoder[observed] = answer
                    assert all(decoder[ob] == y for ob, y in zip(out, goal))
                return {"cost": k, "indexes": indexes,
                        "decoder": [{"observed": list(k), "goal": v}
                                    for k,v in sorted(decoder.items())]}
    return None

def compare_full_native(n):
    binary = list(product((0, 1), repeat=n))
    counts = Counter()
    samples = []
    for goal in partitions(n):
        for sensors in combinations(binary, 2):
            obj = {"name": "observational-sufficiency-falsifier",
                "protected": list(goal),
                "operations": [],
                "readouts": [{"name": f"r{k}", "cost":1, "values":list(x)}
                             for k,x in enumerate(sensors)],
                "grants":["r0","r1"],
                "base_readouts":[],
                "desired_labels":list(goal)}
            original = compile_experiment(obj)
            independent_exact = independent_opt(sensors, goal, "exact")
            independent_sufficient = independent_opt(sensors, goal, "sufficient")
            if independent_exact is None:
                assert original["status"] == "UNREALIZABLE_IN_COMPLETE_DECLARED_FINITE_GRAMMAR", original
                assert original["basis"] is None
            else:
                assert original["status"] == "EXACT_BASIS_CONSTRUCTED", original
                assert original["basis_cost"] == independent_exact["cost"], original
            if independent_exact is None and independent_sufficient is not None:
                label = "FALSE_OBSTRUCTION_FOR_DECISION_SUFFICIENCY"
                if len(samples) < 5:
                    samples.append({"goal": list(goal),
                        "readouts": [list(x) for x in sensors],
                        "native_v1_status":original["status"],
                        "decoder_basis":list(independent_sufficient["indexes"]),
                        "decoder":independent_sufficient["decoder"],
                        "decision_sufficient_cost":independent_sufficient["cost"]})
            elif independent_exact is not None:
                assert independent_sufficient is not None
                assert independent_sufficient["cost"] <= independent_exact["cost"]
                label = "BOTH_FEASIBLE"
            else:
                label = "BOTH_OBSTRUCTED"
            counts[label] += 1
    assert sum(counts.values()) == len(partitions(n))*len(list(combinations(binary,2)))
    return {"states":n,"target_partitions":len(partitions(n)),
            "available_binary_readouts":len(binary),
            "panels":sum(counts.values()),"counts":dict(counts),
            "first_false_obstructions":samples}

def main():
    examples = {}
    for n in (3, 4):
        examples[str(n)] = compare_full_native(n)
    assert examples["3"]["counts"] == {
        "BOTH_FEASIBLE":79,"BOTH_OBSTRUCTED":49,
        "FALSE_OBSTRUCTION_FOR_DECISION_SUFFICIENCY":12}, examples["3"]
    assert examples["4"]["counts"] == {
        "BOTH_FEASIBLE":407,"BOTH_OBSTRUCTED":1189,
        "FALSE_OBSTRUCTION_FOR_DECISION_SUFFICIENCY":204},examples["4"]
    target=(0,0,1)
    sensors=[(0,1,0),(0,1,1)]
    exact=independent_opt(sensors,target,"exact")
    sufficient=independent_opt(sensors,target,"sufficient")
    assert exact is None and sufficient["cost"]==2
    result={"status":"FINITE_COUNTEREXAMPLE_TO_EXACT_SENSOR_QUOTIENT_AS_DECISION_ADMISSION",
            "pinned_original_compiler_commit":PINNED_V1,
            "original_semantics":"joint observation kernel must equal protected decision kernel",
            "repaired_semantics":"joint observation kernel SUBSET of protected decision kernel; certify decoder after observation",
            "proof_idea":"decoder on observed image exists iff observation kernel refines decision kernel",
            "families":examples,
            "primary_three_state_witness":{"protected_decision":[0,0,1],
                "readouts":[[0,1,0],[0,1,1]],"decision_sufficient_cost":2,
                "decoder":sufficient["decoder"],"original_exact_feasible":False},
            "not_claimed":["new theorem", "physical sensor discovery", "instrument safety",
                "empirical biological advantage", "new G2 primitive", "speedup over independent exhaustive baseline"],
            "disclaimer":"V1 correctly solves its explicitly narrower exact-quotient task; the false obstruction applies only if the output is interpreted as inability to determine the protected decision."}
    out=Path("out/decision_sufficiency_falsifier")
    out.mkdir(parents=True,exist_ok=True)
    (out/"audit.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("DECISION_SUFFICIENCY_AUDIT="+json.dumps({k:v for k,v in result.items() if k!="families"},sort_keys=True))
    print("EXACT_SENSOR_QUOTIENT_TOO_STRICT_FOR_DECISION_PASS")

if __name__=="__main__":
    main()
