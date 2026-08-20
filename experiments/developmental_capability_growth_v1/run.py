#!/usr/bin/env python3
"""DEVELOPMENTAL_CAPABILITY_GROWTH_V1

A dependency-free finite experiment for the core MathGraph developmental claim:

    verified obstruction -> representation refinement -> new capability
    -> ablation loss -> held-out/source-distinct reuse

This is deliberately a bounded exact world.  It does *not* claim a universal
procedure for inventing representations.  Instead, it tests whether a verified
failure can constrain a finite refinement family strongly enough that the
minimal capability-changing distinction is mathematically identifiable.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import json
from typing import Callable, Iterable


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


# Discovery task: the current quotient retains parity but forgets which side of
# the first-coordinate split a state occupies.
def target_discovery(x: State) -> int:
    return x[0]


# Source-distinct reuse task.  It is not the discovery target, but it requires
# the same newly exposed distinction in combination with already-visible parity.
def target_transfer(x: State) -> int:
    return int(x[0] == parity(x))


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


def cells(rep: Representation) -> dict[tuple[object, ...], list[State]]:
    out: dict[tuple[object, ...], list[State]] = {}
    for x in WORLD:
        out.setdefault(rep.key(x), []).append(x)
    return out


def closure_size(rep: Representation) -> int:
    """Number of Boolean functions representable by a policy on rep's cells."""
    return 2 ** len(cells(rep))


def conflict_certificate(rep: Representation, target: LabelFn) -> list[dict[str, object]]:
    """Exact obstruction: same representation cell, incompatible target labels."""
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
                    "labels": {str(k): [list(x) for x in v] for k, v in sorted(by_label.items())},
                }
            )
    return cert


def target_in_closure(rep: Representation, target: LabelFn) -> bool:
    return not conflict_certificate(rep, target)


def best_exact_accuracy(rep: Representation, target: LabelFn) -> float:
    """Best possible deterministic policy accuracy under this representation."""
    correct = 0
    for xs in cells(rep).values():
        counts = {0: 0, 1: 0}
        for x in xs:
            counts[target(x)] += 1
        correct += max(counts.values())
    return correct / len(WORLD)


def truth_vector(target: LabelFn) -> list[int]:
    return [target(x) for x in WORLD]


def represented_truth_vectors(rep: Representation) -> set[tuple[int, ...]]:
    """Exhaustively enumerate the finite generative closure of Boolean policies."""
    ordered_cells = sorted(cells(rep), key=repr)
    vectors: set[tuple[int, ...]] = set()
    for outputs in product((0, 1), repeat=len(ordered_cells)):
        policy = dict(zip(ordered_cells, outputs))
        vectors.add(tuple(policy[rep.key(x)] for x in WORLD))
    return vectors


def evaluate_candidate(
    baseline: Representation,
    feature_name: str,
    feature: FeatureFn,
    target: LabelFn,
) -> dict[str, object]:
    rep = baseline.extend(feature_name, feature)
    cert = conflict_certificate(rep, target)
    return {
        "feature": feature_name,
        "representation": rep.name,
        "cell_count": len(cells(rep)),
        "closure_size": closure_size(rep),
        "target_in_closure": not cert,
        "best_accuracy": best_exact_accuracy(rep, target),
        "remaining_conflicts": len(cert),
    }


def main() -> None:
    baseline = Representation("PARITY_QUOTIENT", (("parity", parity),))

    # Frozen one-step refinement family.  The controller is allowed to search
    # this family; it is not allowed to alter the target or evaluation world.
    candidates: tuple[tuple[str, FeatureFn], ...] = (
        ("bit0", bit0),
        ("bit1", bit1),
        ("bit2", bit2),
        ("weight", weight),
        ("constant_zero", constant_zero),
    )

    baseline_vectors = represented_truth_vectors(baseline)
    discovery_vector = tuple(truth_vector(target_discovery))
    baseline_obstruction = conflict_certificate(baseline, target_discovery)

    candidate_results = [
        evaluate_candidate(baseline, name, fn, target_discovery)
        for name, fn in candidates
    ]
    successful = [r for r in candidate_results if r["target_in_closure"]]

    # Minimality here is relative to the frozen single-feature refinement family.
    # All candidates have equal extension arity, so an exact singleton is a
    # uniquely identified minimal refinement in this bounded protocol.
    successful_names = [str(r["feature"]) for r in successful]
    selected_name = successful_names[0] if len(successful_names) == 1 else None
    selected_fn = dict(candidates).get(selected_name) if selected_name else None
    repaired = baseline.extend(selected_name, selected_fn) if selected_fn else None

    sham = baseline.extend("bit1", bit1)

    transfer_baseline = target_in_closure(baseline, target_transfer)
    transfer_repaired = target_in_closure(repaired, target_transfer) if repaired else False
    transfer_sham = target_in_closure(sham, target_transfer)

    gates = {
        # G0: target really is outside the old finite generative closure.
        "G0_verified_old_closure_failure": (
            discovery_vector not in baseline_vectors
            and bool(baseline_obstruction)
            and not target_in_closure(baseline, target_discovery)
        ),
        # G1: the frozen refinement family identifies exactly one successful
        # one-feature distinction rather than permitting a post-hoc story.
        "G1_unique_minimal_refinement_in_frozen_family": successful_names == ["bit0"],
        # G2: the selected distinction actually expands capability to include target.
        "G2_target_enters_extended_closure": bool(
            repaired and target_in_closure(repaired, target_discovery)
        ),
        # G3: same-shape sham distinction does not explain the gain.
        "G3_sham_refinement_fails": not target_in_closure(sham, target_discovery),
        # G4: ablation of the new distinction restores the old impossibility.
        "G4_ablation_restores_obstruction": not target_in_closure(
            baseline, target_discovery
        ),
        # G5: the distinction supports a second, source-distinct target that is
        # impossible in the old quotient and is not rescued by the sham feature.
        "G5_source_distinct_reuse": (
            not transfer_baseline and transfer_repaired and not transfer_sham
        ),
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
        "discovery_target_truth_vector": list(discovery_vector),
        "candidate_refinements": candidate_results,
        "selected_refinement": selected_name,
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
        "transfer": {
            "target": "bit0 == parity",
            "baseline_in_closure": transfer_baseline,
            "repaired_in_closure": transfer_repaired,
            "sham_in_closure": transfer_sham,
        },
        "gates": gates,
        "verdict": verdict,
    }

    print(json.dumps(report, indent=2, sort_keys=True))
    if verdict != "PASS_BOUNDED_DEVELOPMENTAL_EVENT":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
