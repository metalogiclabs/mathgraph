"""Exact differential tests for compiled qualification gates and SCC reclosure."""
import random
import unittest
from mathgraph_check.warrant_resolution import (
    Claim, Receipt, Route, QualifiedRelation, resolve_graph,
)
from mathgraph_check.qualified_consequence_closure import QualifiedConsequenceClosure


def fixture(seed):
    rng = random.Random(seed)
    claims = [Claim(f"c{i}", "formal", "s") for i in range(24)]
    claims.append(Claim("source", "documentary", "other"))
    receipts = [Receipt(f"e{i}", "formal", "s") for i in range(8)]
    receipts += [Receipt("verifier", "formal", "s"),
                 Receipt("qualification", "formal", "s"),
                 Receipt("external", "documentary", "other")]
    routes = [Route("source", ("external",))]
    for i in range(24):
        # Include a few supported and unsupported cyclic components.
        p = tuple(f"c{j}" for j in rng.sample(range(24), rng.randrange(3)))
        routes.append(Route(f"c{i}", (f"e{rng.randrange(8)}",), p))
        if rng.random() < .5:
            routes.append(Route(f"c{i}", ("e0",)))
    bridge = Route("c20", ("external",), ("source",), "bridge")
    routes.append(bridge)
    relation = QualifiedRelation("bridge", "documentary", "other", "formal", "s",
                                 "verifier", ("qualification",), bridge)
    return claims, receipts, list(dict.fromkeys(routes)), (relation,)


class CompiledQualifiedConsequenceTests(unittest.TestCase):
    def test_randomized_shared_qualification_withdrawal_reinstatement(self):
        for seed in range(25):
            claims, receipts, routes, relations = fixture(seed)
            engine = QualifiedConsequenceClosure(claims, routes, receipts, relations=relations)
            ids = [r.id for r in receipts]
            rng = random.Random(seed + 772)
            withdrawn = set()
            # Always exercise shared verifier and qualification revocation.
            changes = ["verifier", "qualification", "verifier", "qualification"]
            changes += [rng.choice(ids) for _ in range(100)]
            for step, receipt in enumerate(changes):
                live = receipt in withdrawn
                if live:
                    withdrawn.remove(receipt)
                else:
                    withdrawn.add(receipt)
                engine.update(receipt, live)
                expected = resolve_graph(claims, routes, receipts,
                                         withdrawn=frozenset(withdrawn),
                                         relations=relations)
                self.assertEqual(engine.states(), dict(expected.states),
                                 (seed, step, receipt, "states"))
                self.assertEqual(engine.active_routes(), expected.active_routes,
                                 (seed, step, receipt, "active routes"))

    def test_rootless_cycle_and_local_withdrawal(self):
        claims = [Claim(x, "formal", "s") for x in ("root", "a", "b", "unrelated")]
        receipts = [Receipt(x, "formal", "s") for x in ("ground", "shared", "else")]
        routes = [Route("root", ("ground",)),
                  Route("a", ("shared",), ("root",)),
                  Route("a", ("shared",), ("b",)),
                  Route("b", ("shared",), ("a",)),
                  Route("unrelated", ("else",))]
        e = QualifiedConsequenceClosure(claims, routes, receipts)
        e.update("ground", False)
        self.assertEqual(e.states()["a"], "UNKNOWN")
        self.assertEqual(e.states()["b"], "UNKNOWN")
        self.assertEqual(e.states()["unrelated"], "WARRANTED_BOUNDED")
        e.update("ground", True)
        self.assertEqual(e.states()["b"], "WARRANTED_BOUNDED")

    def test_invalid_boundary_cannot_be_compiled(self):
        claims = [Claim("c", "formal", "s")]
        receipts = [Receipt("e", "documentary", "different")]
        with self.assertRaisesRegex(ValueError, "CROSS_BOUNDARY"):
            QualifiedConsequenceClosure(claims, [Route("c", ("e",))], receipts)


if __name__ == "__main__":
    unittest.main()
