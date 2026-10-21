"""Differential tests against canonical bounded warrant resolution.

Only externally admitted synthetic receipt values are used here.
"""
import random
import unittest

from mathgraph_check.warrant_resolution import Claim, Receipt, Route, resolve_graph
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

    def test_unsupported_semantics_fail_closed(self):
        claims = [Claim("a", "formal", "s"), Claim("b", "formal", "s")]
        receipts = [Receipt("r", "formal", "s")]
        routes = [Route("a", ("r",), ("b",)),
                  Route("b", ("r",), ("a",))]
        with self.assertRaisesRegex(ValueError, "CYCLIC"):
            IncrementalClosure(claims, routes, receipts)


if __name__ == "__main__":
    unittest.main()
