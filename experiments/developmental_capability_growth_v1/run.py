#!/usr/bin/env python3
"""DEVELOPMENTAL_CAPABILITY_GROWTH_V1

Dependency-free finite experiment for a bounded MathGraph developmental claim:

    verified closure failure -> obstruction certificate
    -> constrained representation refinement -> new capability
    -> sham failure -> causal ablation -> source-distinct reuse

The experiment is intentionally small enough that every closure can be
exhaustively enumerated. It does *not* claim a universal procedure for
inventing representations. Minimality is relative to a refinement family
frozen in this source file before evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import json
from typing import Callable


State = tuple[int, int, int]
LabelFn = Callable[[State], int]
FeatureFn = Callable[[State], object]

WORLD: tuple[State, ...] = tuple(product((0, 1), repeat=3))


def parity(x: State) -> int:
    return sum(x) % 2


def bit0(x: State) -> int:
    return x[0]


def bit1(x: State) -> int:
    return x[1]


def bit2(x: State) -> int:
    return x[2]


def weight(x: State) -> int:
    return sum(x)


def constant_zero(_: State) -> int:
    return 0


# Discovery target. Crucially, this is NOT any candidate refinement feature.
# It requires combining the already-visible parity distinction with a missing
# first-coordinate distinction.
def target_discovery(x: State) -> int:
    return bit0(x) & parity(x)


# Source-distinct reuse target. It differs from the discovery target but needs
# the same first-coordinate distinction together with parity.
def target_transfer(x: State) -> int:
    return bit0(x) | parity(x)


@dataclass(frozen=True)
class Representation:
    name: str
    features: tuple[tuple[str, FeatureFn], ...]

    def key(self, x: State) -> tuple[object, ...]:
        return tuple(fn(x) for _, fn in self.features)

    def extend(self, name: str, fn: FeatureFn) -> "Representation":
        return Representation(
            name=f"{self.name}+{name}",
            features=self.features + ((name, fn),),
        )

    def drop(self, name: str) -> "Representation":
        kept = tuple((n, fn) for n, fn in self.features if n != name)
        return Representation(name=f"{self.name}-{name}", features=kept)


def cells(rep: Representation) -> dict[tuple[object, ...], list[State]]:
    out: dict[tuple[object, ...], list[State]] = {}
    for x in WORLD:
        out.setdefault(rep.key(x), []).append(x)
    return out


def partition_signature(rep: Representation) -> tuple[tuple[State, ...], ...]:
    """Representation partition, independent of the spelling/order of keys."""
    groups = [tuple(sorted(xs)) for xs in cells(rep).values()]
    return tuple(sorted(groups))


def closure_size(rep: Representation) -> int:
    """Number of Boolean functions constant on rep's representation cells."""
    return 2 ** len(cells(rep))


def conflict_certificate(rep: Representation, target: LabelFn) -> list[dict[str, object]]:
    """Exact obstruction: one representation cell requires incompatible labels."""
    cert: list[dict[str, object]] = []
    for key, xs in sorted(cells(rep).items(), key=lambda kv: repr(kv[0])):
        by_label: dict[int, list[State]] = {}
        for x in xs:
            by_label.setdefault(target(x), []).append(x)
        if len(by_label) > 1:
            cert.append(
                {
                    "representation_key": list(key),
                    "states": [list(x) for x in xs],
                    "labels": {
                        str(k): [list(x) for x in v]
                        for k, v in sorted(by_label.items())
                    },
                }
            )
    return cert


def target_in_closure(rep: Representation, target: LabelFn) -> bool:
    """Analytic closure test using cell consistency."""
    return not conflict_certificate(rep, target)


def best_exact_accuracy(rep: Representation, target: LabelFn) -> float:
    """Best deterministic policy accuracy possible under this representation."""
    correct = 0
    for xs in cells(rep).values():
        counts = {0: 0, 1: 0}
        for x in xs:
            counts[target(x)] += 1
        correct += max(counts.values())
    return correct / len(WORLD)


def truth_vector(fn: Callable[[State], object]) -> tuple[object, ...]:
    return tuple(fn(x) for x in WORLD)


def represented_truth_vectors(rep: Representation) -> set[tuple[int, ...]]:
    """Exhaustively enumerate the complete finite Boolean policy closure."""
    ordered_cells = sorted(cells(rep), key=repr)
    vectors: set[tuple[int, ...]] = set()
    for outputs in product((0, 1), repeat=len(ordered_cells)):
        policy = dict(zip(ordered_cells, outputs))
        vectors.add(tuple(policy[rep.key(x)] for x in WORLD))
    return vectors


def exhaustive_target_in_closure(rep: Representation, target: LabelFn) -> bool:
    return truth_vector(target) in represented_truth_vectors(rep)


def evaluate_candidate(
    baseline: Representation,
    feature_name: str,
    feature: FeatureFn,
    target: LabelFn,
) -> dict[str, object]:
    rep = baseline.extend(feature_name, feature)
    analytic = target_in_closure(rep, target)
    exhaustive = exhaustive_target_in_closure(rep, target)
    vectors = represented_truth_vectors(rep)
    return {
        "feature": feature_name,
        "representation": rep.name,
        "cell_count": len(cells(rep)),
        "closure_size_formula": closure_size(rep),
        "closure_size_enumerated": len(vectors),
        "target_in_closure_analytic": analytic,
        "target_in_closure_exhaustive": exhaustive,
        "methods_agree": analytic == exhaustive,
        "best_accuracy": best_exact_accuracy(rep, target),
        "remaining_conflicts": len(conflict_certificate(rep, target)),
    }


def main() -> None:
    baseline = Representation("PARITY_QUOTIENT", (("parity", parity),))

    # PRECOMMITTED/FROZEN one-step refinement family. The experiment may search
    # this family but may not alter it after seeing target outcomes.
    candidates: tuple[tuple[str, FeatureFn], ...] = (
        ("bit0", bit0),
        ("bit1", bit1),
        ("bit2", bit2),
        ("weight", weight),
        ("constant_zero", constant_zero),
    )

    discovery_vector = truth_vector(target_discovery)
    transfer_vector = truth_vector(target_transfer)
    baseline_vectors = represented_truth_vectors(baseline)
    baseline_obstruction = conflict_certificate(baseline, target_discovery)

    candidate_results = [
        evaluate_candidate(baseline, name, fn, target_discovery)
        for name, fn in candidates
    ]
    successful_names = [
        str(r["feature"])
        for r in candidate_results
        if r["target_in_closure_analytic"] and r["target_in_closure_exhaustive"]
    ]

    selected_name = successful_names[0] if len(successful_names) == 1 else None
    selected_fn = dict(candidates).get(selected_name) if selected_name else None
    repaired = baseline.extend(selected_name, selected_fn) if selected_fn else None

    sham = baseline.extend("bit1", bit1)
    ablated = repaired.drop("bit0") if repaired else None

    transfer_baseline = target_in_closure(baseline, target_transfer)
    transfer_repaired = target_in_closure(repaired, target_transfer) if repaired else False
    transfer_sham = target_in_closure(sham, target_transfer)

    # Independent sanity checks make accidental implementation agreement harder:
    # formula closure size vs exhaustive enumeration, and conflict criterion vs
    # literal truth-vector membership.
    reps_to_crosscheck = [baseline, sham] + ([repaired, ablated] if repaired and ablated else [])
    closure_crosschecks = {
        rep.name: {
            "formula_size": closure_size(rep),
            "enumerated_size": len(represented_truth_vectors(rep)),
            "discovery_analytic": target_in_closure(rep, target_discovery),
            "discovery_exhaustive": exhaustive_target_in_closure(rep, target_discovery),
        }
        for rep in reps_to_crosscheck
    }

    selected_is_not_target = (
        selected_fn is not None
        and truth_vector(selected_fn) != discovery_vector
        and truth_vector(selected_fn) != transfer_vector
    )

    gates = {
        "G0_verified_old_closure_failure": (
            discovery_vector not in baseline_vectors
            and bool(baseline_obstruction)
            and not target_in_closure(baseline, target_discovery)
            and not exhaustive_target_in_closure(baseline, target_discovery)
        ),
        "G1_unique_minimal_refinement_in_frozen_family": (
            successful_names == ["bit0"]
            and not target_in_closure(baseline, target_discovery)
        ),
        "G1b_refinement_is_not_the_target_label": selected_is_not_target,
        "G2_target_enters_extended_closure": bool(
            repaired
            and target_in_closure(repaired, target_discovery)
            and exhaustive_target_in_closure(repaired, target_discovery)
        ),
        "G3_same_shape_sham_refinement_fails": (
            not target_in_closure(sham, target_discovery)
            and not exhaustive_target_in_closure(sham, target_discovery)
        ),
        "G4_real_ablation_restores_original_partition_and_obstruction": bool(
            ablated
            and partition_signature(ablated) == partition_signature(baseline)
            and not target_in_closure(ablated, target_discovery)
            and not exhaustive_target_in_closure(ablated, target_discovery)
        ),
        "G5_source_distinct_reuse": (
            discovery_vector != transfer_vector
            and not transfer_baseline
            and transfer_repaired
            and not transfer_sham
        ),
        "G6_independent_closure_checks_agree": all(
            v["formula_size"] == v["enumerated_size"]
            and v["discovery_analytic"] == v["discovery_exhaustive"]
            for v in closure_crosschecks.values()
        )
        and all(bool(r["methods_agree"]) for r in candidate_results),
    }

    verdict = "PASS_BOUNDED_DEVELOPMENTAL_EVENT" if all(gates.values()) else "FAIL"

    report = {
        "protocol": "DEVELOPMENTAL_CAPABILITY_GROWTH_V1",
        "claim_boundary": (
            "Exact finite 3-bit world; minimality is only relative to the frozen "
            "single-feature refinement family. This is not a universal invention theorem."
        ),
        "world": [list(x) for x in WORLD],
        "baseline": {
            "representation": baseline.name,
            "cell_count": len(cells(baseline)),
            "closure_size": closure_size(baseline),
            "target_in_closure": target_in_closure(baseline, target_discovery),
            "best_accuracy": best_exact_accuracy(baseline, target_discovery),
            "obstruction_certificate": baseline_obstruction,
        },
        "discovery_target": "bit0 AND parity",
        "discovery_target_truth_vector": list(discovery_vector),
        "candidate_refinements": candidate_results,
        "selected_refinement": selected_name,
        "selected_refinement_is_not_target_label": selected_is_not_target,
        "repaired": {
            "representation": repaired.name if repaired else None,
            "cell_count": len(cells(repaired)) if repaired else None,
            "closure_size": closure_size(repaired) if repaired else None,
            "target_in_closure": target_in_closure(repaired, target_discovery) if repaired else False,
            "best_accuracy": best_exact_accuracy(repaired, target_discovery) if repaired else 0.0,
        },
        "sham": {
            "representation": sham.name,
            "target_in_closure": target_in_closure(sham, target_discovery),
            "best_accuracy": best_exact_accuracy(sham, target_discovery),
        },
        "ablation": {
            "representation": ablated.name if ablated else None,
            "partition_matches_baseline": bool(
                ablated and partition_signature(ablated) == partition_signature(baseline)
            ),
            "target_in_closure": target_in_closure(ablated, target_discovery) if ablated else False,
        },
        "transfer": {
            "target": "bit0 OR parity",
            "source_distinct_from_discovery": discovery_vector != transfer_vector,
            "baseline_in_closure": transfer_baseline,
            "repaired_in_closure": transfer_repaired,
            "sham_in_closure": transfer_sham,
        },
        "closure_crosschecks": closure_crosschecks,
        "gates": gates,
        "verdict": verdict,
    }

    # Human-readable preface first; full machine certificate follows as JSON.
    print("DEVELOPMENTAL CAPABILITY GROWTH V1")
    print("----------------------------------")
    print(f"Old representation: {baseline.name}")
    print(f"Discovery target:   bit0 AND parity")
    print(f"Old closure:        {closure_size(baseline)} Boolean policies; target OUTSIDE")
    print(f"Unique refinement:  {selected_name}")
    print(f"Repaired closure:   {closure_size(repaired) if repaired else 'n/a'} Boolean policies; target INSIDE")
    print(f"Sham bit1:          {'FAILS as required' if not target_in_closure(sham, target_discovery) else 'unexpectedly succeeds'}")
    print(f"Ablation:           {'restores old obstruction' if gates['G4_real_ablation_restores_original_partition_and_obstruction'] else 'FAILED'}")
    print(f"Reuse target:       bit0 OR parity -> {'PASS' if gates['G5_source_distinct_reuse'] else 'FAIL'}")
    print(f"VERDICT:            {verdict}")
    print("\nFULL CERTIFICATE")
    print(json.dumps(report, indent=2, sort_keys=True))

    if verdict != "PASS_BOUNDED_DEVELOPMENTAL_EVENT":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
