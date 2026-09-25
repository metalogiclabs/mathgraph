#!/usr/bin/env python3
"""Refine the broad finite_enumeration motif from Swarm Scale V1."""

from __future__ import annotations

from collections import Counter
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / "scripts" / "run_crystal_swarm_scale_v1.py"
RESULT = ROOT / "evidence" / "crystal-swarm-scale-v1-finite-refinement" / "result.json"
PARENT = "4a12e1aa0996b664e0ed4f5d46a2b3cf162af12a"

spec = importlib.util.spec_from_file_location("swarm_scale_v1_base", BASE_PATH)
base = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = base
spec.loader.exec_module(base)

SUBMOTIFS = {
    "exhaustive_enumeration": (
        "exhaustive", "enumerat", "itertools", "product(", "combinations(", "permutations(",
    ),
    "countermodel_falsifier": (
        "countermodel", "counterexample", "falsif", "reject", "negative witness",
    ),
    "certificate_witness_construction": (
        "certificate", "witness", "proof_atlas", "evidence_pack", "evidence pack",
    ),
    "bounded_state_closure": (
        "reclose", "closure", "kernel", "viability", "transition", "stateful", "frontier",
    ),
    "finite_model_semantics": (
        "finite_magma", "formal_world", "finite world", "model", "structure",
    ),
    "truth_assignment_search": (
        "truth", "boolean", "bool", "tauto", "logic_combination",
    ),
    "finite_optimization": (
        "minimum", "maximum", "argmin", "argmax", "optimal", "cost", "budget",
    ),
    "subset_combinatorics": (
        "powerset", "subset", "combination", "permutation", "matching", "cover",
    ),
    "bounded_numeric_search": (
        "residue", "mod ", "mod_", "interval", "matrix", "spectral", "coordinate",
    ),
}

COST = {
    "exhaustive_enumeration": 4,
    "countermodel_falsifier": 4,
    "certificate_witness_construction": 5,
    "bounded_state_closure": 6,
    "finite_model_semantics": 6,
    "truth_assignment_search": 4,
    "finite_optimization": 5,
    "subset_combinatorics": 5,
    "bounded_numeric_search": 6,
}


def classify(path: str) -> tuple[str, ...]:
    text = (ROOT / path).read_text(encoding="utf-8").lower()
    return tuple(
        name for name, needles in SUBMOTIFS.items()
        if any(needle in text for needle in needles)
    )


def main() -> None:
    families = [base.parse_family(path) for path in sorted(base.TESTS.glob("test_*.py"))]
    frontier = base.select_frontier(families)
    finite = [f for f in frontier if "finite_enumeration" in f.motifs]
    assert len(finite) == 76

    classified = []
    for family in finite:
        subs = classify(family.path)
        classified.append({
            "path": family.path,
            "domain": family.domain,
            "submotifs": subs,
            "providers": family.providers,
        })

    market = {}
    for motif in SUBMOTIFS:
        affected = [f for f in classified if motif in f["submotifs"]]
        domains = sorted({f["domain"] for f in affected})
        provider_freq = Counter()
        for f in affected:
            provider_freq.update(f["providers"])
        family_count = len(affected)
        provider_count = len(provider_freq)
        concentration = (
            max(provider_freq.values()) / family_count
            if family_count and provider_freq else 0.0
        )
        dispersion = 1.0 - concentration if family_count else 0.0
        reuse_pressure = family_count * (1.0 + dispersion) + 2.0 * len(domains)
        score = reuse_pressure / COST[motif]
        market[motif] = {
            "family_count": family_count,
            "domain_count": len(domains),
            "domains": domains,
            "provider_count": provider_count,
            "provider_concentration": concentration,
            "dispersion": dispersion,
            "reuse_pressure": reuse_pressure,
            "declared_cost": COST[motif],
            "market_score": score,
            "top_providers": provider_freq.most_common(8),
        }

    ranked = sorted(market.items(), key=lambda kv: (-kv[1]["market_score"], kv[0]))
    selected_name, selected = ranked[0]

    ordered = sorted(classified, key=lambda x: x["path"])
    development = ordered[:57]
    heldout = ordered[57:]
    dev_count = sum(selected_name in f["submotifs"] for f in development)
    hold_count = sum(selected_name in f["submotifs"] for f in heldout)
    if hold_count == 0:
        raise AssertionError("selected finite submotif has zero held-out recurrence")

    evidence = {
        "schema": "mathgraph.crystal-swarm-scale-v1-finite-refinement.qualified",
        "status": "QUALIFIED_BOUNDED",
        "parent_head": PARENT,
        "finite_frontier_families": len(finite),
        "submotif_market": market,
        "selected_submotif": selected_name,
        "selected_market_score": selected["market_score"],
        "selected_family_count": selected["family_count"],
        "selected_domain_count": selected["domain_count"],
        "selected_provider_count": selected["provider_count"],
        "anti_overfit": {
            "development_families": len(development),
            "heldout_families": len(heldout),
            "selected_submotif_development_count": dev_count,
            "selected_submotif_heldout_count": hold_count,
        },
        "top_candidates": [
            [name, data["market_score"], data["family_count"], data["domain_count"]]
            for name, data in ranked[:6]
        ],
        "classified_families": classified,
        "next_action": (
            f"compile_or_reconcile:{selected_name}; replay affected families through one "
            "canonical finite decision/witness interface and measure actual contraction"
        ),
        "boundary": (
            "Static repository-mined submotif refinement. Keyword signatures and declared "
            "costs are candidate policy only. The next experiment must execute the selected "
            "operation and measure real runtime and residual contraction."
        ),
    }
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print("CRYSTAL_SWARM_SCALE_V1_FINITE_REFINEMENT=QUALIFIED_BOUNDED")
    print(json.dumps({
        "finite_frontier_families": len(finite),
        "selected_submotif": selected_name,
        "selected_market_score": selected["market_score"],
        "selected_family_count": selected["family_count"],
        "selected_domain_count": selected["domain_count"],
        "selected_provider_count": selected["provider_count"],
        "anti_overfit": evidence["anti_overfit"],
        "top_candidates": evidence["top_candidates"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
