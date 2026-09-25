#!/usr/bin/env python3
from __future__ import annotations
from functools import lru_cache
from itertools import combinations
import json
from pathlib import Path

from mathgraph.crystal import SemanticObject
from mathgraph.math_claim import MathClaimPayload, VerifiedClaimRelation

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "evidence/crystal-perspective-triangulation-gallai-v0/result.json"
PARENT = "3eb314d50cefb25b187d33e3c80aa4f298e97e98"

def all_edges(n):
    return tuple(combinations(range(n), 2))

def adj_of(n, edges, mask):
    adj = [0] * n
    chosen = []
    for i, (u, v) in enumerate(edges):
        if mask & (1 << i):
            adj[u] |= 1 << v
            adj[v] |= 1 << u
            chosen.append((u, v))
    return tuple(adj), tuple(chosen)

def max_matching(adj):
    n = len(adj)
    @lru_cache(None)
    def go(rem):
        if rem == 0:
            return 0
        bit = rem & -rem
        v = bit.bit_length() - 1
        rest = rem & ~bit
        best = go(rest)
        cand = adj[v] & rest
        while cand:
            ubit = cand & -cand
            best = max(best, 1 + go(rest & ~ubit))
            cand &= ~ubit
        return best
    return go((1 << n) - 1)

def min_edge_cover(n, chosen):
    full = (1 << n) - 1
    inf = 10**9
    dp = [inf] * (1 << n)
    dp[0] = 0
    for u, v in chosen:
        em = (1 << u) | (1 << v)
        ndp = dp.copy()
        for covered, cost in enumerate(dp):
            if cost == inf:
                continue
            tgt = covered | em
            ndp[tgt] = min(ndp[tgt], cost + 1)
        dp = ndp
    return None if dp[full] == inf else dp[full]

def has_isolated(adj):
    return any(x == 0 for x in adj)

def make_objects():
    specs = {
        "canonical": ("canonical-reference-v0", (("G","FiniteSimpleGraph"),), ("NoIsolatedVertices(G)",),
                      "matchingNumber(G)+minEdgeCoverNumber(G)=vertexCount(G)", "cwi:gallai"),
        "research": ("research-paper-v0", (("G","FiniteSimpleGraph"),), ("NoIsolatedVertices(G)",),
                     "matchingNumber(G)+minEdgeCoverNumber(G)=vertexCount(G)", "arxiv:1905.02141"),
        "vixra_source": ("literature-prose-extraction-v0", (("G","ArbitraryGraph"),), (),
                         "maximumMatching(G)+minimumEdgeCover(G)<=vertexCount(G)", "vixra:2202.0183"),
        "vixra_repaired": ("finite-graph-invariant-v0", (("G","FiniteSimpleGraph"),), ("EdgeCoverExists(G)",),
                           "matchingNumber(G)+minEdgeCoverNumber(G)<=vertexCount(G)", "vixra:2202.0183|domain-repair"),
    }
    ids = {}
    for name, (dialect, context, assumptions, statement, source) in specs.items():
        obj = MathClaimPayload(
            claim_id="gallai."+name,
            dialect=dialect,
            context=context,
            assumptions=assumptions,
            statement=statement,
            source_ref=source,
        ).semantic_object()
        assert SemanticObject.from_bytes(obj.to_bytes()) == obj
        ids[name] = obj.id
    ev = "hosted:crystal-perspective-triangulation-gallai-v0"
    rels = (
        VerifiedClaimRelation(ids["canonical"], ids["research"], "equivalent", (ev,)),
        VerifiedClaimRelation(ids["canonical"], ids["vixra_repaired"], "implies", (ev,)),
    )
    return ids, [r.id for r in rels]

def main():
    total = defined = isolated = 0
    equality_failures = []
    existence_mismatches = []
    strict_weak = []
    by_n = {}
    smallest_obstruction = None

    for n in range(1, 7):
        edges = all_edges(n)
        stats = {"graphs": 0, "edge_cover_defined": 0, "isolated": 0}
        for mask in range(1 << len(edges)):
            total += 1
            stats["graphs"] += 1
            adj, chosen = adj_of(n, edges, mask)
            nu = max_matching(adj)
            rho = min_edge_cover(n, chosen)
            iso = has_isolated(adj)
            if iso:
                isolated += 1
                stats["isolated"] += 1
            if rho is not None:
                defined += 1
                stats["edge_cover_defined"] += 1

            # Empirically recover the domain condition, don't assume it.
            if (rho is None) != iso:
                existence_mismatches.append((n, mask, iso, rho))

            if rho is None:
                if smallest_obstruction is None:
                    smallest_obstruction = {
                        "n": n, "graph_mask": mask,
                        "separator": "isolated vertex",
                        "consequence": "minimum edge cover undefined"
                    }
                continue

            lhs = nu + rho
            if lhs != n:
                equality_failures.append((n, mask, nu, rho))
            if lhs < n:
                strict_weak.append((n, mask, nu, rho))

        by_n[str(n)] = stats

    assert not existence_mismatches
    assert not equality_failures
    assert not strict_weak
    assert smallest_obstruction["n"] == 1

    ids, relations = make_objects()
    evidence = {
        "schema": "mathgraph.crystal-perspective-triangulation-gallai-v0.qualified",
        "status": "QUALIFIED_BOUNDED",
        "parent_crystal_head": PARENT,
        "crystal_waist_changed": False,
        "claim_dialect_changed": False,
        "results": {
            "labelled_graphs_exhaustively_checked": total,
            "graphs_with_defined_edge_cover": defined,
            "graphs_with_isolated_vertex": isolated,
            "gallai_equality_failures_on_defined_domain": 0,
            "strict_cases_for_vixra_leq_on_defined_domain": 0,
            "edge_cover_exists_iff_no_isolated_mismatches": 0,
            "smallest_obstruction": smallest_obstruction
        },
        "per_order": by_n,
        "claim_objects": ids,
        "verified_relations": relations,
        "triangulated_structure": {
            "invariant": "edgeCoverExists(G) => matchingNumber(G)+minEdgeCoverNumber(G)=vertexCount(G)",
            "domain_equivalence_on_tested_boundary": "edgeCoverExists(G) iff G has no isolated vertex",
            "speculative_shadow": "The viXra <= statement is non-separating wherever its minimum-edge-cover term is defined; the missing consequential distinction is domain/definedness.",
            "formal_library_residual": "mathlib4 has matching infrastructure at the pinned head, but repository search found no edge-cover interface/theorem.",
            "named_obstruction": "isolated vertex"
        },
        "boundary": "Exhaustive for all labelled finite simple graphs on 1..6 vertices only; not a universal proof."
    }
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print("CRYSTAL_PERSPECTIVE_TRIANGULATION_GALLAI_V0=QUALIFIED_BOUNDED")
    print(json.dumps(evidence, sort_keys=True))

if __name__ == "__main__":
    main()
