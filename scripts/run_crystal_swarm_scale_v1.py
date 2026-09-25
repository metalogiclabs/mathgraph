#!/usr/bin/env python3
"""Swarm Scale V1: mine a 96-family residual market from the real test corpus.

The experiment is intentionally meta-level. It does not promote the test corpus
itself as mathematics; it measures repeated semantic-operation shapes already
present in the repository and asks which not-yet-compiled operation has the
largest cross-family reuse opportunity.
"""
from __future__ import annotations

import ast
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
RESULT = ROOT / "evidence" / "crystal-swarm-scale-v1" / "result.json"
PARENT = "3f323e5b713acd5b5c47d68fe13d485027aa676c"
FRONTIER_SIZE = 96

MOTIFS = {
    "provenance_lineage": (
        "provenance", "evidence_ref", "evidence_refs", "warrant", "lineage",
        "source_ref", "digest", "manifest", "blob_sha",
    ),
    "admission_promotion": (
        "promot", "admission", "acceptance", "lawbook", "qualif", "warranted",
    ),
    "residual_reclosure": (
        "residual", "reclose", "frontier", "unknown", "uncovered", "failure_class",
    ),
    "certificate_witness": (
        "certificate", "witness", "counterexample", "countermodel", "proof_atlas",
    ),
    "adapter_transport": (
        "adapter", "translate", "translation", "lowering", "transport", "correspondence",
    ),
    "scheduler_value": (
        "scheduler", "priority", "budget", "route_selection", "discovery_value", "cost",
    ),
    "capability_compounding": (
        "capability", "compounding", "constructor", "warm", "reuse", "learned",
    ),
    "source_grounding": (
        "source_pin", "source-pinned", "source_ref", "manifest", "digest", "blob_sha", "grounding",
    ),
    "transition_viability": (
        "viability", "stateful", "transition", "control", "action_quotient", "greatest_viability",
    ),
    "finite_enumeration": (
        "finite", "enumerat", "exhaustive", "truth_table", "truth table", "countermodel",
    ),
    "relation_compiler": (
        "equivalent", "equivalence", "implies", "implication", "separator",
        "quotient", "falsifier", "partition",
    ),
}

# The relation compiler was just qualified at the parent head. Exclude it from
# candidate actions while retaining it as a positive control in the census.
ALREADY_COMPILED = {"relation_compiler"}

# Coarse implementation costs. These are preregistered policy inputs, not claims
# of true engineering cost. V2 should replace them with measured compute/time.
COST = {
    "provenance_lineage": 5,
    "admission_promotion": 6,
    "residual_reclosure": 5,
    "certificate_witness": 5,
    "adapter_transport": 6,
    "scheduler_value": 4,
    "capability_compounding": 6,
    "source_grounding": 4,
    "transition_viability": 7,
    "finite_enumeration": 4,
}

DOMAIN_RULES = (
    ("crystal", ("crystal",)),
    ("lawbook", ("lawbook",)),
    ("finite_htilt", ("finite_htilt", "htilt")),
    ("lean_kernel_mathlib", ("lean", "kernel", "mathlib")),
    ("discovery", ("discovery", "frontier", "residual")),
    ("compounding", ("compounding", "capability", "episode")),
    ("certificate_evidence", ("certificate", "evidence", "artifact")),
    ("arc", ("arc",)),
    ("causal_continuation", ("causal", "continuation", "viability")),
    ("formal_worlds", ("formal_world", "magma", "equation", "etp")),
    ("services_product", ("api", "service", "client", "cli")),
)


@dataclass(frozen=True)
class Family:
    path: str
    domain: str
    motifs: tuple[str, ...]
    providers: tuple[str, ...]
    local_helpers: int


def domain_for(path: str) -> str:
    low = path.lower()
    for name, needles in DOMAIN_RULES:
        if any(n in low for n in needles):
            return name
    return "other"


def parse_family(path: Path) -> Family:
    source = path.read_text(encoding="utf-8")
    low = source.lower()
    motifs = tuple(
        name
        for name, needles in MOTIFS.items()
        if any(needle in low for needle in needles)
    )

    providers: set[str] = set()
    local_helpers = 0
    try:
        tree = ast.parse(source)
    except SyntaxError:
        tree = None
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("mathgraph"):
                providers.add(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("mathgraph"):
                        providers.add(alias.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("test_"):
                    local_helpers += 1

    return Family(
        path=str(path.relative_to(ROOT)),
        domain=domain_for(path.name),
        motifs=motifs,
        providers=tuple(sorted(providers)),
        local_helpers=local_helpers,
    )


def select_frontier(families: list[Family]) -> list[Family]:
    semantic = [f for f in families if f.motifs]
    by_motif = {
        motif: sorted(
            (f for f in semantic if motif in f.motifs),
            key=lambda f: (-len(f.motifs), -f.local_helpers, f.path),
        )
        for motif in MOTIFS
    }
    selected: list[Family] = []
    seen: set[str] = set()
    cursors = {motif: 0 for motif in MOTIFS}
    motif_order = tuple(MOTIFS)

    while len(selected) < FRONTIER_SIZE:
        progress = False
        for motif in motif_order:
            bucket = by_motif[motif]
            i = cursors[motif]
            while i < len(bucket) and bucket[i].path in seen:
                i += 1
            cursors[motif] = i + 1
            if i < len(bucket):
                selected.append(bucket[i])
                seen.add(bucket[i].path)
                progress = True
                if len(selected) == FRONTIER_SIZE:
                    break
        if not progress:
            break

    if len(selected) < FRONTIER_SIZE:
        remaining = sorted(
            (f for f in semantic if f.path not in seen),
            key=lambda f: (-len(f.motifs), -f.local_helpers, f.path),
        )
        selected.extend(remaining[: FRONTIER_SIZE - len(selected)])

    if len(selected) != FRONTIER_SIZE:
        raise AssertionError(f"could select only {len(selected)} semantic families")
    return selected


def motif_stats(frontier: list[Family], motif: str) -> dict:
    affected = [f for f in frontier if motif in f.motifs]
    domains = sorted({f.domain for f in affected})
    provider_freq: Counter[str] = Counter()
    helper_total = 0
    for f in affected:
        provider_freq.update(f.providers)
        helper_total += f.local_helpers

    if affected and provider_freq:
        concentration = max(provider_freq.values()) / len(affected)
    elif affected:
        concentration = 0.0
    else:
        concentration = 1.0
    dispersion = 1.0 - concentration

    provider_count = len(provider_freq)
    family_count = len(affected)
    domain_count = len(domains)
    local_helper_density = helper_total / family_count if family_count else 0.0

    # Reuse pressure rewards wide fanout, cross-domain recurrence, and
    # implementation dispersion. Helper density is capped so large test files
    # cannot dominate merely by code volume.
    reuse_pressure = (
        family_count * (1.0 + dispersion)
        + 2.0 * domain_count
        + min(local_helper_density, 5.0)
    )
    return {
        "family_count": family_count,
        "domain_count": domain_count,
        "domains": domains,
        "provider_count": provider_count,
        "provider_concentration": concentration,
        "dispersion": dispersion,
        "local_helper_density": local_helper_density,
        "reuse_pressure": reuse_pressure,
        "top_providers": provider_freq.most_common(8),
    }


def main() -> None:
    paths = sorted(TESTS.glob("test_*.py"))
    families = [parse_family(path) for path in paths]
    frontier = select_frontier(families)

    census = {
        motif: {
            "all_test_files": sum(motif in f.motifs for f in families),
            "frontier_files": sum(motif in f.motifs for f in frontier),
        }
        for motif in MOTIFS
    }

    candidates = {}
    for motif in MOTIFS:
        stats = motif_stats(frontier, motif)
        if motif in ALREADY_COMPILED:
            stats["eligible"] = False
            stats["reason"] = "already_compiled_at_parent"
            stats["market_score"] = 0.0
        else:
            stats["eligible"] = True
            cost = COST[motif]
            stats["declared_cost"] = cost
            stats["market_score"] = stats["reuse_pressure"] / cost
        candidates[motif] = stats

    eligible = [(name, data) for name, data in candidates.items() if data["eligible"]]
    eligible.sort(key=lambda item: (-item[1]["market_score"], item[0]))
    selected_name, selected = eligible[0]

    # Hold out the last 24 selected families lexically and verify that the
    # selected motif is not only an artifact of the first 72-family development
    # subset. This is a weak but explicit anti-overfit check.
    ordered = sorted(frontier, key=lambda f: f.path)
    development = ordered[:72]
    heldout = ordered[72:]
    dev_count = sum(selected_name in f.motifs for f in development)
    hold_count = sum(selected_name in f.motifs for f in heldout)
    if hold_count == 0:
        raise AssertionError("selected compiler motif has zero held-out recurrence")

    evidence = {
        "schema": "mathgraph.crystal-swarm-scale-v1.qualified",
        "status": "QUALIFIED_BOUNDED",
        "parent_head": PARENT,
        "repository_test_files": len(families),
        "semantic_test_files": sum(bool(f.motifs) for f in families),
        "frontier_size": len(frontier),
        "frontier_domains": sorted(Counter(f.domain for f in frontier).items()),
        "motif_census": census,
        "candidate_market": candidates,
        "selected_compiler_motif": selected_name,
        "selected_market_score": selected["market_score"],
        "selected_family_count": selected["family_count"],
        "selected_domain_count": selected["domain_count"],
        "selected_provider_count": selected["provider_count"],
        "anti_overfit": {
            "development_families": len(development),
            "heldout_families": len(heldout),
            "selected_motif_development_count": dev_count,
            "selected_motif_heldout_count": hold_count,
        },
        "frontier": [asdict(f) for f in frontier],
        "next_action": (
            f"compile_or_reconcile:{selected_name}; then reclose the {selected['family_count']} "
            "affected frontier families and measure actual residual contraction and real cost"
        ),
        "boundary": (
            "This is repository-mined scheduling evidence, not a theorem about globally optimal "
            "research allocation. Families are test files, motifs are explicit preregistered "
            "semantic keyword signatures, and costs are declared policy inputs. V2 must replace "
            "declared costs with measured runtime/token/money and execute the selected compiler."
        ),
    }
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print("CRYSTAL_SWARM_SCALE_V1=QUALIFIED_BOUNDED")
    print(json.dumps({
        "repository_test_files": evidence["repository_test_files"],
        "semantic_test_files": evidence["semantic_test_files"],
        "frontier_size": evidence["frontier_size"],
        "selected_compiler_motif": selected_name,
        "selected_market_score": evidence["selected_market_score"],
        "selected_family_count": evidence["selected_family_count"],
        "selected_domain_count": evidence["selected_domain_count"],
        "selected_provider_count": evidence["selected_provider_count"],
        "anti_overfit": evidence["anti_overfit"],
        "top_candidates": [
            [name, data["market_score"], data["family_count"], data["domain_count"]]
            for name, data in eligible[:5]
        ],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
