"""Independent agenda-based baseline for the bounded warrant resolver.

Not a MathGraph runtime component. Immutable graph, externally admitted
receipts; cycles and relations use canonical reclosure, as in the candidate.
"""
from collections import deque
from mathgraph_check.warrant_resolution import resolve_graph


class AgendaBaseline:
    def __init__(self, claims, routes, receipts, *, withdrawn=frozenset(), relations=()):
        initial = resolve_graph(claims, routes, receipts, withdrawn=withdrawn, relations=relations)
        self.claims, self.routes, self.receipts = tuple(claims), tuple(routes), tuple(receipts)
        self.relations = tuple(relations)
        self.withdrawn = set(withdrawn)
        self.children = {c.id: [] for c in claims}
        self.by_conclusion = {c.id: [] for c in claims}
        self.by_receipt = {e.id: [] for e in receipts}
        self.values = {c.id: initial.states[c.id] != "UNKNOWN" for c in claims}
        self.active = [route in initial.active_routes for route in routes]
        self.fallback = bool(relations)
        deps = {c.id: set() for c in claims}
        for i, r in enumerate(routes):
            self.by_conclusion[r.conclusion].append(i)
            for p in set(r.premises):
                self.children[p].append(i)
                deps[r.conclusion].add(p)
            for e in set(r.evidence):
                self.by_receipt[e].append(i)
        remaining = {k: len(v) for k, v in deps.items()}
        q = deque(k for k, n in remaining.items() if n == 0)
        visited = 0
        descendants = {c.id: set() for c in claims}
        while q:
            p = q.popleft()
            visited += 1
            for i in self.children[p]:
                child = routes[i].conclusion
                remaining[child] -= 1
                if remaining[child] == 0:
                    q.append(child)
        self.fallback |= visited != len(claims)
        self._canonical = initial

    def update(self, receipt, live):
        if receipt not in self.by_receipt:
            raise ValueError("UNKNOWN_RECEIPT")
        if (receipt not in self.withdrawn) == live:
            return 0
        if live:
            self.withdrawn.remove(receipt)
        else:
            self.withdrawn.add(receipt)
        if self.fallback:
            self._canonical = resolve_graph(self.claims, self.routes, self.receipts,
                        withdrawn=frozenset(self.withdrawn), relations=self.relations)
            return len(self.routes)
        # Agenda approach: recompute only affected conclusions, retry descendants
        # if and only if their support status changes.
        pending = deque(self.by_receipt[receipt])
        queued = set(pending)
        work = 0
        while pending:
            i = pending.popleft()
            queued.discard(i)
            r = self.routes[i]
            new = all(e not in self.withdrawn for e in r.evidence) and all(self.values[p] for p in r.premises)
            work += 1
            if new == self.active[i]:
                continue
            self.active[i] = new
            old_claim = self.values[r.conclusion]
            new_claim = any(self.active[j] for j in self.by_conclusion[r.conclusion])
            self.values[r.conclusion] = new_claim
            if old_claim != new_claim:
                for j in self.children[r.conclusion]:
                    if j not in queued:
                        queued.add(j)
                        pending.append(j)
        return work

    def states(self):
        if self.fallback:
            return dict(self._canonical.states)
        return {c.id: ("WARRANTED_BOUNDED" if c.kind == "formal" else "SOURCE_DOCUMENTED")
                if self.values[c.id] else "UNKNOWN" for c in self.claims}

    def active_routes(self):
        if self.fallback:
            return self._canonical.active_routes
        return tuple(sorted((r for i, r in enumerate(self.routes) if self.active[i]),
                            key=lambda r: (r.conclusion, r.evidence, r.premises, r.relation or "")))
