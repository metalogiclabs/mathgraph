"""Experimental incremental warrant closure for validated acyclic graphs.

Receipt admission remains external. This is not a verifier or a replacement
for resolve_graph. Graphs with cycles or qualified relations are rejected.
"""
from collections import deque
import heapq

from .warrant_resolution import resolve_graph


class IncrementalClosure:
    def __init__(self, claims, routes, receipts, *, withdrawn=frozenset(), relations=()):
        if relations:
            raise ValueError("QUALIFIED_RELATIONS_NOT_SUPPORTED_IN_EXPERIMENT")
        resolve_graph(claims, routes, receipts, withdrawn=withdrawn)
        self.claims = tuple(claims)
        self.routes = tuple(routes)
        self.withdrawn = set(withdrawn)
        self.route_children = {c.id: [] for c in claims}
        self.receipt_children = {e.id: [] for e in receipts}
        self.claim_live = {c.id: False for c in claims}
        self.route_live = [False] * len(routes)
        self.supports = {c.id: 0 for c in claims}
        deps = {c.id: set() for c in claims}
        children = {c.id: set() for c in claims}
        for i, route in enumerate(routes):
            for p in set(route.premises):
                self.route_children[p].append(i)
                deps[route.conclusion].add(p)
                children[p].add(route.conclusion)
            for e in set(route.evidence):
                self.receipt_children[e].append(i)
        degree = {k: len(v) for k, v in deps.items()}
        q = deque(k for k, v in degree.items() if not v)
        order = []
        while q:
            node = q.popleft()
            order.append(node)
            for child in children[node]:
                degree[child] -= 1
                if not degree[child]:
                    q.append(child)
        if len(order) != len(claims):
            raise ValueError("CYCLIC_GRAPH_OUTSIDE_EXPERIMENT_PROFILE")
        rank = {node: i for i, node in enumerate(order)}
        route_order = sorted(range(len(routes)), key=lambda i: rank[routes[i].conclusion])
        self.route_rank = {route: i for i, route in enumerate(route_order)}
        for i in route_order:
            route = routes[i]
            live = (all(e not in self.withdrawn for e in set(route.evidence))
                    and all(self.claim_live[p] for p in set(route.premises)))
            self.route_live[i] = live
            if live:
                self.supports[route.conclusion] += 1
                self.claim_live[route.conclusion] = True

    def update(self, receipt, live):
        if receipt not in self.receipt_children:
            raise ValueError("UNKNOWN_RECEIPT")
        if (receipt not in self.withdrawn) == live:
            return 0
        if live:
            self.withdrawn.remove(receipt)
        else:
            self.withdrawn.add(receipt)
        dirty = set(self.receipt_children[receipt])
        heap = [(self.route_rank[i], i) for i in dirty]
        heapq.heapify(heap)
        visited = 0
        while heap:
            _, i = heapq.heappop(heap)
            if i not in dirty:
                continue
            dirty.remove(i)
            visited += 1
            route = self.routes[i]
            next_live = (all(e not in self.withdrawn for e in set(route.evidence))
                         and all(self.claim_live[p] for p in set(route.premises)))
            if next_live == self.route_live[i]:
                continue
            self.route_live[i] = next_live
            previous = self.claim_live[route.conclusion]
            self.supports[route.conclusion] += 1 if next_live else -1
            current = self.supports[route.conclusion] > 0
            self.claim_live[route.conclusion] = current
            if previous != current:
                for child in self.route_children[route.conclusion]:
                    if child not in dirty:
                        dirty.add(child)
                        heapq.heappush(heap, (self.route_rank[child], child))
        return visited

    def states(self):
        return {
            c.id: ("WARRANTED_BOUNDED" if c.kind == "formal"
                   else "SOURCE_DOCUMENTED") if self.claim_live[c.id] else "UNKNOWN"
            for c in self.claims
        }
