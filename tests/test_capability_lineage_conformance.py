"""Capability closure experiment against MathGraph's existing typed warrant resolver.

Synthetic admissions are explicitly assumed, NOT externally qualified receipts.
This file is a conformance comparison, not a new production resolver.
"""
import itertools
import random
import unittest
from collections import deque

from mathgraph_check.warrant_resolution import Claim, Receipt, Route, resolve_graph

SCOPE = "synthetic:capability-closure:bounded-v1"


def construct(n=5, seed=0):
    rng = random.Random(seed)
    # Sources are claims backed by one scoped receipt each. Derived claims
    # are conjunctive (one route) or disjunctive (alternative routes).
    names = [f"c{i}" for i in range(n + 8)]
    claims = [Claim(x, "formal", SCOPE) for x in names]
    receipts = [Receipt(f"e{i}", "formal", SCOPE) for i in range(n)]
    routes = [Route(names[i], (f"e{i}",)) for i in range(n)]
    parents = [()] * n
    ops = ["LEAF"] * n
    for i in range(n, len(names)):
        p = tuple(rng.sample(range(i), 2))
        parents.append(p)
        op = "AND" if i % 2 else "OR"
        ops.append(op)
        if op == "AND":
            # A nonempty evidence list is required by the canonical resolver;
            # a shared admitted root receipt is an explicit qualification
            # dependency of every derived route.
            routes.append(Route(names[i], ("e0",), tuple(names[k] for k in p)))
        else:
            routes.extend(Route(names[i], ("e0",), (names[k],)) for k in p)
    return claims, receipts, routes, parents, ops


class CountedDAG:
    """Experimental optimization; reference semantics come from resolve_graph."""
    def __init__(self, parents, ops, leaf_states):
        self.parents, self.ops = parents, ops
        self.children = [[] for _ in parents]
        for i in range(len(leaf_states), len(parents)):
            for p in parents[i]:
                self.children[p].append(i)
        self.values = list(leaf_states) + [False] * (len(parents) - len(leaf_states))
        self.counts = [0] * len(parents)
        for i in range(len(leaf_states), len(parents)):
            self.counts[i] = sum(self.values[p] for p in parents[i])
            self.values[i] = self.counts[i] == len(parents[i]) if ops[i] == "AND" else self.counts[i] > 0

    def update(self, source, live):
        if self.values[source] == live:
            return
        delta = 1 if live else -1
        self.values[source] = live
        pending = deque([(source, delta)])
        while pending:
            parent, sign = pending.popleft()
            for child in self.children[parent]:
                self.counts[child] += sign
                new = (self.counts[child] == len(self.parents[child])
                       if self.ops[child] == "AND" else self.counts[child] > 0)
                if self.values[child] != new:
                    self.values[child] = new
                    pending.append((child, 1 if new else -1))


class CapabilityLineageConformance(unittest.TestCase):
    def test_withdrawal_reinstatement_matches_real_resolver(self):
        # e0 is an explicit shared qualification; disabling it revokes all
        # derived routes even if other sources are still valid.
        for seed in range(8):
            claims, receipts, routes, parents, ops = construct(seed=seed)
            for rest in itertools.product((False, True), repeat=4):
                bits = (True,) + rest
                withdrawn = {f"e{i}" for i, live in enumerate(bits) if not live}
                engine = CountedDAG(parents, ops, [bits[i] and bits[0] for i in range(5)])
                # With e0 withdrawn every claim other than c1..c4 with
                # live receipts is unsupported; derived nodes are disabled.
                for step in range(20):
                    rng = random.Random(seed * 100000 + sum(bits) * 100 + step)
                    changed = rng.randrange(1, 5)
                    live = f"e{changed}" in withdrawn
                    if live:
                        withdrawn.remove(f"e{changed}")
                    else:
                        withdrawn.add(f"e{changed}")
                    current = [f"e{i}" not in withdrawn for i in range(5)]
                    # Shared qualification e0 remains admitted in this
                    # differential test; withdrawal is tested separately.
                    engine.update(changed, current[changed])
                    expected = resolve_graph(claims, routes, receipts,
                                              withdrawn=frozenset(withdrawn))
                    actual = [expected.states[f"c{i}"] == "WARRANTED_BOUNDED"
                              for i in range(len(parents))]
                    self.assertEqual(engine.values, actual,
                                     (seed, bits, step, changed))
                    # The resolver must never silently widen scope or treat
                    # withdrawal as a refutation.
                    self.assertTrue(set(expected.states.values()) <=
                                    {"UNKNOWN", "WARRANTED_BOUNDED"})

    def test_shared_evidence_withdrawal_is_precise(self):
        claims, receipts, routes, _, _ = construct()
        before = resolve_graph(claims, routes, receipts).states
        after = resolve_graph(claims, routes, receipts,
                              withdrawn=frozenset({"e2"})).states
        self.assertEqual(before["c1"], after["c1"])
        self.assertEqual(after["c2"], "UNKNOWN")
        self.assertEqual(after["c0"], "WARRANTED_BOUNDED")

    def test_unqualified_cross_scope_is_rejected(self):
        claims, receipts, routes, _, _ = construct()
        bad = list(claims)
        bad[-1] = Claim(bad[-1].id, "formal", "unrelated-scope")
        with self.assertRaisesRegex(ValueError, "CROSS_BOUNDARY"):
            resolve_graph(bad, routes, receipts)


if __name__ == "__main__":
    unittest.main()
