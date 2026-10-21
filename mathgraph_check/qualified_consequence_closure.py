"""Experimental compiled qualified-consequence closure.

Static admission is delegated to canonical resolve_graph. Route verifier and
qualification receipts become ordinary *runtime* dependencies. Strongly
connected components are recomputed to their least fixed point on updates.
No receipt admission, trust-policy change, or live-sensor verification occurs.
"""
from collections import defaultdict
import heapq

from .warrant_resolution import resolve_graph


def _components(nodes, edges):
    # Tarjan SCC, deterministic over the declared claim order.
    index = 0
    indices, low, stack, onstack, parts = {}, {}, [], set(), []
    def visit(v):
        nonlocal index
        indices[v] = low[v] = index
        index += 1
        stack.append(v)
        onstack.add(v)
        for w in sorted(edges[v]):
            if w not in indices:
                visit(w)
                low[v] = min(low[v], low[w])
            elif w in onstack:
                low[v] = min(low[v], indices[w])
        if low[v] == indices[v]:
            group = []
            while True:
                w = stack.pop()
                onstack.remove(w)
                group.append(w)
                if w == v:
                    break
            parts.append(tuple(sorted(group)))
    for v in nodes:
        if v not in indices:
            visit(v)
    return parts


class QualifiedConsequenceClosure:
    def __init__(self, claims, routes, receipts, *, withdrawn=frozenset(), relations=()):
        reference = resolve_graph(claims, routes, receipts,
                                  withdrawn=withdrawn, relations=relations)
        self.claims, self.routes = tuple(claims), tuple(routes)
        self.receipts, self.relations = tuple(receipts), tuple(relations)
        self.withdrawn = set(withdrawn)
        bridges = {r.id: r for r in relations}
        self.required = []
        self.receipt_to_routes = defaultdict(set)
        self.incoming = defaultdict(list)
        edges = {c.id: set() for c in claims}
        for i, route in enumerate(routes):
            ev = set(route.evidence)
            if route.relation is not None:
                b = bridges[route.relation]
                ev.update((b.verifier, *b.evidence))
            self.required.append(frozenset(ev))
            for e in ev:
                self.receipt_to_routes[e].add(i)
            self.incoming[route.conclusion].append(i)
            for p in route.premises:
                edges[p].add(route.conclusion)
        self.components = _components([c.id for c in claims], edges)
        self.component_of = {c: i for i, part in enumerate(self.components)
                             for c in part}
        self.component_children = defaultdict(set)
        indegree = [0] * len(self.components)
        for parent, children in edges.items():
            a = self.component_of[parent]
            for child in children:
                b = self.component_of[child]
                if a != b and b not in self.component_children[a]:
                    self.component_children[a].add(b)
                    indegree[b] += 1
        waiting = [i for i, n in enumerate(indegree) if n == 0]
        heapq.heapify(waiting)
        self.order = []
        while waiting:
            a = heapq.heappop(waiting)
            self.order.append(a)
            for b in sorted(self.component_children[a]):
                indegree[b] -= 1
                if not indegree[b]:
                    heapq.heappush(waiting, b)
        assert len(self.order) == len(self.components)
        self.rank = {c: i for i, c in enumerate(self.order)}
        self.values = {c.id: False for c in claims}
        self.route_live = [False] * len(routes)
        for component in self.order:
            self._recompute(component)
        assert self.states() == dict(reference.states)
        assert self.active_routes() == reference.active_routes

    def _recompute(self, component):
        members = self.components[component]
        before = tuple(self.values[c] for c in members)
        # Reset internally supported claims: a cycle without an external
        # grounding route must lose warrant even if previously supported.
        for c in members:
            self.values[c] = False
        while True:
            changed = False
            for c in members:
                if not self.values[c] and any(
                    not (self.required[i] & self.withdrawn)
                    and all(self.values[p] for p in self.routes[i].premises)
                    for i in self.incoming[c]
                ):
                    self.values[c] = True
                    changed = True
            if not changed:
                break
        for c in members:
            for i in self.incoming[c]:
                self.route_live[i] = (
                    not (self.required[i] & self.withdrawn)
                    and all(self.values[p] for p in self.routes[i].premises)
                )
        return before != tuple(self.values[c] for c in members)

    def update(self, receipt, live):
        if receipt not in {r.id for r in self.receipts}:
            raise ValueError("UNKNOWN_RECEIPT")
        if (receipt not in self.withdrawn) == live:
            return 0
        if live:
            self.withdrawn.remove(receipt)
        else:
            self.withdrawn.add(receipt)
        pending = {self.component_of[self.routes[i].conclusion]
                   for i in self.receipt_to_routes[receipt]}
        heap = [(self.rank[i], i) for i in pending]
        heapq.heapify(heap)
        touched = 0
        while heap:
            _, c = heapq.heappop(heap)
            if c not in pending:
                continue
            pending.remove(c)
            touched += 1
            if self._recompute(c):
                for child in self.component_children[c]:
                    if child not in pending:
                        pending.add(child)
                        heapq.heappush(heap, (self.rank[child], child))
        return touched

    def states(self):
        return {c.id: ("WARRANTED_BOUNDED" if c.kind == "formal"
                       else "SOURCE_DOCUMENTED") if self.values[c.id] else "UNKNOWN"
                for c in sorted(self.claims, key=lambda x: x.id)}

    def active_routes(self):
        return tuple(sorted((r for i, r in enumerate(self.routes) if self.route_live[i]),
                            key=lambda r: (r.conclusion, r.evidence, r.premises, r.relation or "")))
