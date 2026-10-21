"""Independent component-local reference: rebuild affected-region from source.

Unlike the compiled candidate, this baseline recomputes a clean local closure
of all claim descendants of a changed receipt, without incremental gate counts.
Static admission and exact route identities are canonical.
"""
from collections import defaultdict, deque
from mathgraph_check.warrant_resolution import resolve_graph


class RegionBaseline:
    def __init__(self, claims, routes, receipts, *, withdrawn=frozenset(), relations=()):
        reference = resolve_graph(claims, routes, receipts, withdrawn=withdrawn, relations=relations)
        self.claims, self.routes, self.receipts = tuple(claims), tuple(routes), tuple(receipts)
        self.relations = tuple(relations)
        self.withdrawn = set(withdrawn)
        bridge = {r.id: r for r in relations}
        self.route_evidence = []
        self.receipt_to_claims = defaultdict(set)
        self.children = defaultdict(set)
        self.incoming = defaultdict(list)
        for i, r in enumerate(routes):
            ev = set(r.evidence)
            if r.relation:
                b = bridge[r.relation]
                ev.update((b.verifier, *b.evidence))
            self.route_evidence.append(ev)
            for e in ev:
                self.receipt_to_claims[e].add(r.conclusion)
            self.incoming[r.conclusion].append(i)
            for p in r.premises:
                self.children[p].add(r.conclusion)
        self.values = {c.id: reference.states[c.id] != "UNKNOWN" for c in claims}
        self.active = [r in reference.active_routes for r in routes]

    def update(self, receipt, live):
        if receipt not in {r.id for r in self.receipts}:
            raise ValueError("UNKNOWN_RECEIPT")
        if (receipt not in self.withdrawn) == live:
            return 0
        if live:
            self.withdrawn.remove(receipt)
        else:
            self.withdrawn.add(receipt)
        affected = set(self.receipt_to_claims[receipt])
        pending = deque(affected)
        while pending:
            for c in self.children[pending.popleft()]:
                if c not in affected:
                    affected.add(c)
                    pending.append(c)
        for c in affected:
            self.values[c] = False
        while True:
            changed = False
            for c in affected:
                if not self.values[c] and any(
                    not (self.route_evidence[i] & self.withdrawn)
                    and all(self.values[p] for p in self.routes[i].premises)
                    for i in self.incoming[c]
                ):
                    self.values[c] = True
                    changed = True
            if not changed:
                break
        for c in affected:
            for i in self.incoming[c]:
                self.active[i] = (
                    not (self.route_evidence[i] & self.withdrawn)
                    and all(self.values[p] for p in self.routes[i].premises)
                )
        return len(affected)

    def states(self):
        return {c.id: ("WARRANTED_BOUNDED" if c.kind == "formal"
                       else "SOURCE_DOCUMENTED") if self.values[c.id] else "UNKNOWN"
                for c in sorted(self.claims, key=lambda x: x.id)}

    def active_routes(self):
        return tuple(sorted((r for i, r in enumerate(self.routes) if self.active[i]),
                            key=lambda r: (r.conclusion, r.evidence, r.premises, r.relation or "")))
