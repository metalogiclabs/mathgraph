"""Differential tests against canonical bounded warrant resolution.

Only externally admitted synthetic receipt values are used here.
"""
import random
import unittest

from mathgraph_check.warrant_resolution import Claim, Receipt, Route, QualifiedRelation, resolve_graph
from mathgraph_check.incremental_closure import IncrementalClosure


class IncrementalClosureTests(unittest.TestCase):
    def test_shared_receipts_withdrawal_and_reinstatement(self):
        for seed in range(40):
            rng = random.Random(seed)
            claims = [Claim(f"c{i}", "formal", "synthetic") for i in range(25)]
            receipts = [Receipt(f"e{i}", "formal", "synthetic") for i in range(9)]
            routes = []
            for i in range(len(claims)):
                for _ in range(rng.randint(1, 3)):
                    evidence = (f"e{rng.randrange(len(receipts))}",)
                    if rng.random() < 0.65:
                        evidence = tuple(dict.fromkeys(evidence + ("e0",)))
                    parents = tuple(
                        f"c{j}" for j in
                        rng.sample(range(i), min(i, rng.randrange(3)))
                    )
                    routes.append(Route(f"c{i}", evidence, parents))
            routes = list(dict.fromkeys(routes))
            candidate = IncrementalClosure(claims, routes, receipts)
            withdrawn = set()
            for step in range(150):
                eid = f"e{rng.randrange(len(receipts))}"
                enabled = eid in withdrawn
                if enabled:
                    withdrawn.remove(eid)
                else:
                    withdrawn.add(eid)
                candidate.update(eid, enabled)
                reference = resolve_graph(claims, routes, receipts,
                                          withdrawn=frozenset(withdrawn))
                self.assertEqual(candidate.states(), dict(reference.states),
                                 (seed, step, eid))
                self.assertEqual(candidate.active_routes(), reference.active_routes,
                                 (seed, step, eid, "route lineage"))

    def test_cycle_and_qualified_relation_fallback(self):
        claims = [Claim("a", "formal", "target"),
                  Claim("b", "formal", "target"),
                  Claim("src", "documentary", "source")]
        receipts = [Receipt("root", "formal", "target"),
                    Receipt("verifier", "formal", "target"),
                    Receipt("qualification", "formal", "target"),
                    Receipt("source_receipt", "documentary", "source")]
        cycle = [Route("a", ("root",)),
                 Route("b", ("root",), ("a",)),
                 Route("a", ("root",), ("b",))]
        bridge_route = Route("a", ("source_receipt",), ("src",), "bridge")
        relation = QualifiedRelation(
            "bridge", "documentary", "source", "formal", "target",
            "verifier", ("qualification",), bridge_route)
        routes = cycle + [Route("src", ("source_receipt",)), bridge_route]
        candidate = IncrementalClosure(claims, routes, receipts,
                                        relations=(relation,))
        self.assertTrue(candidate.fallback)
        withdrawn = set()
        for rid in ("root", "qualification", "source_receipt",
                    "verifier", "root", "qualification",
                    "source_receipt", "verifier"):
            enabled = rid in withdrawn
            if enabled:
                withdrawn.remove(rid)
            else:
                withdrawn.add(rid)
            candidate.update(rid, enabled)
            expected = resolve_graph(claims, routes, receipts,
                                     withdrawn=frozenset(withdrawn),
                                     relations=(relation,))
            self.assertEqual(candidate.states(), dict(expected.states))
            self.assertEqual(candidate.active_routes(), expected.active_routes)

        # Rootless mutual support is not an admitted proof.
        unrooted = [Route("a", ("root",), ("b",)),
                    Route("b", ("root",), ("a",))]
        cyc = IncrementalClosure(claims[:2], unrooted, receipts)
        self.assertTrue(cyc.fallback)
        self.assertEqual(cyc.states()["a"], "UNKNOWN")
        self.assertEqual(cyc.states()["b"], "UNKNOWN")

    def test_invalid_graphs_still_fail_closed(self):
        claims = [Claim("a", "formal", "s")]
        receipts = [Receipt("r", "formal", "s")]
        with self.assertRaisesRegex(ValueError, "UNKNOWN_WITHDRAWAL_TARGET"):
            IncrementalClosure(claims, [Route("a", ("r",))], receipts,
                               withdrawn=frozenset({"unknown"}))
        with self.assertRaisesRegex(ValueError, "CROSS_BOUNDARY"):
            IncrementalClosure([Claim("a", "formal", "other")],
                               [Route("a", ("r",))], receipts)


if __name__ == "__main__":
    unittest.main()
