"""Finite simple-graph semantic dialect behind the stable Crystal envelope."""
from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
import json
from mathgraph.crystal import SemanticObject

@dataclass(frozen=True)
class FiniteSimpleGraphPayload:
    vertex_count: int
    edges: tuple[tuple[int, int], ...]

    def __post_init__(self) -> None:
        if self.vertex_count < 0:
            raise ValueError("vertex_count must be non-negative")
        canonical = []
        seen = set()
        for u, v in self.edges:
            if u == v or not (0 <= u < self.vertex_count and 0 <= v < self.vertex_count):
                raise ValueError("invalid simple-graph edge")
            edge = (min(u, v), max(u, v))
            if edge in seen:
                raise ValueError("duplicate edge")
            seen.add(edge)
            canonical.append(edge)
        object.__setattr__(self, "edges", tuple(sorted(canonical)))

    def semantic_object(self) -> SemanticObject:
        payload = json.dumps(
            {"vertex_count": self.vertex_count, "edges": [list(e) for e in self.edges]},
            sort_keys=True, separators=(",", ":"),
        ).encode()
        return SemanticObject(
            type_id="graph.finite.simple@1",
            contract_version=1,
            payload=payload,
            interfaces=(
                "graph.edge-cover.minimum@1",
                "graph.isolated-vertices@1",
                "graph.matching.maximum@1",
            ),
        )

def adjacency(graph: FiniteSimpleGraphPayload) -> tuple[int, ...]:
    out = [0] * graph.vertex_count
    for u, v in graph.edges:
        out[u] |= 1 << v
        out[v] |= 1 << u
    return tuple(out)

def has_isolated_vertex(graph: FiniteSimpleGraphPayload) -> bool:
    return any(mask == 0 for mask in adjacency(graph))

def maximum_matching_number(graph: FiniteSimpleGraphPayload) -> int:
    adj = adjacency(graph)
    n = graph.vertex_count
    @lru_cache(maxsize=None)
    def go(remaining: int) -> int:
        if remaining == 0:
            return 0
        bit = remaining & -remaining
        v = bit.bit_length() - 1
        rest = remaining & ~bit
        best = go(rest)
        cand = adj[v] & rest
        while cand:
            ubit = cand & -cand
            best = max(best, 1 + go(rest & ~ubit))
            cand &= ~ubit
        return best
    return go((1 << n) - 1)

def minimum_edge_cover_number(graph: FiniteSimpleGraphPayload) -> int | None:
    n = graph.vertex_count
    full = (1 << n) - 1
    inf = n + len(graph.edges) + 1
    dp = [inf] * (1 << n)
    dp[0] = 0
    for u, v in graph.edges:
        em = (1 << u) | (1 << v)
        nxt = dp.copy()
        for covered, cost in enumerate(dp):
            if cost >= inf:
                continue
            tgt = covered | em
            nxt[tgt] = min(nxt[tgt], cost + 1)
        dp = nxt
    return None if dp[full] >= inf else dp[full]
