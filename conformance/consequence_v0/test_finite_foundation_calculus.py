"""Finite executable foundation calculus: sound warrant, alternative support, and viable actions.

This is an independent finite model and exhaustive checker of its declared
semantics, not a Lean theorem about arbitrary sources or real-world actions.
"""
import itertools
import unittest

def closure(facts, rules):
    live=set(facts)
    while True:
        add={head for head, premises in rules if set(premises)<=live}
        nxt=live|add
        if nxt==live:return live
        live=nxt

def policy_resolve(source_facts, rules, revoked):
    return closure(set(source_facts)-set(revoked),rules)

def transported_warrant(facts, a, b, protected):
    """Both certified adapters carry explicitly named protected observations."""
    return set(protected)&set(facts)&set(a)&set(b)

def viability(states, goal, disturbances, choices, transitions):
    """Greatest safety/reachability-style controllable predecessor fixed point.

    A state remains if it is already a goal or each declared disturbance has
    at least one admissible action whose successor remains in the candidate.
    """
    live=set(states)
    while True:
        nxt={s for s in live if s in goal or all(
            any(transitions[(s,d,a)] in live for a in choices.get((s,d),())
                if (s,d,a) in transitions)
            for d in disturbances.get(s,()))}
        if nxt==live:return live
        live=nxt

class FoundationFinite(unittest.TestCase):
    def test_exhaustive_no_warrant_creation(self):
        atoms=("a","b","c")
        rules=[("c",("a","b"))]
        for bits in itertools.product((False,True),repeat=3):
            facts={a for a,bit in zip(atoms,bits) if bit}
            for abits in itertools.product((False,True),repeat=3):
                a={x for x,bit in zip(atoms,abits) if bit}
                for bbits in itertools.product((False,True),repeat=3):
                    b={x for x,bit in zip(atoms,bbits) if bit}
                    result=transported_warrant(facts,a,b,atoms)
                    self.assertLessEqual(len(result),len(facts))
                    self.assertTrue(result<=facts&a&b)
                    self.assertEqual(result,transported_warrant(facts,b,a,atoms))
    def test_alternative_support_and_revocation(self):
        rules=[("conclusion",("proof1",)),("conclusion",("proof2",)),
               ("dependent",("conclusion","extra"))]
        self.assertIn("conclusion",policy_resolve({"proof1","proof2","extra"},rules,{"proof1"}))
        self.assertNotIn("conclusion",policy_resolve({"proof1","proof2","extra"},rules,{"proof1","proof2"}))
        self.assertIn("dependent",policy_resolve({"proof1","proof2","extra"},rules,{"proof1"}))
        self.assertNotIn("dependent",policy_resolve({"proof1","proof2","extra"},rules,{"proof1","proof2"}))
    def test_cycle_does_not_self_warrant(self):
        rules=[("a",("b",)),("b",("a",))]
        self.assertEqual(closure(set(),rules),set())
        self.assertEqual(closure({"a"},rules),{"a","b"})
    def test_forged_rule_not_admitted(self):
        permitted=[("conclusion",("signed-source",))]
        self.assertNotIn("conclusion",closure(set(),permitted))
        self.assertNotIn("conclusion",closure({"forged-source"},permitted))
    def test_exhaustive_finite_support(self):
        atoms=("p","q","r")
        rules=[("r",("p",)),("r",("q",))]
        for bits in itertools.product((False,True),repeat=3):
            facts={a for a,b in zip(atoms,bits) if b}
            for revbits in itertools.product((False,True),repeat=3):
                revoked={a for a,b in zip(atoms,revbits) if b}
                got=policy_resolve(facts,rules,revoked)
                self.assertEqual("r" in got,("r" in facts-revoked or "p" in facts-revoked or "q" in facts-revoked))
    def test_resource_contention_and_viability(self):
        states={"fresh","spent","goal"}
        disturbances={"fresh":("first","second"),"spent":("second",)}
        choices={("fresh","first"):("consume",),("fresh","second"):("consume",),
                 ("spent","second"):()}
        transitions={("fresh","first","consume"):"spent",("fresh","second","consume"):"goal"}
        safe=viability(states,{"goal"},disturbances,choices,transitions)
        self.assertNotIn("fresh",safe)
        self.assertNotIn("spent",safe)
        self.assertIn("goal",safe)
    def test_viable_action_requires_successor_in_kernel(self):
        states={"fresh","goal","trap"}
        disturbances={"fresh":("d",),"trap":("d",)}
        choices={("fresh","d"):("good","bad"),("trap","d"):("bad",)}
        transitions={("fresh","d","good"):"goal",("fresh","d","bad"):"trap",("trap","d","bad"):"trap"}
        safe=viability(states,{"goal"},disturbances,choices,transitions)
        self.assertIn("fresh",safe)
        self.assertNotIn("trap",safe)
        self.assertEqual([a for a in choices[("fresh","d")] if transitions[("fresh","d",a)] in safe],["good"])

if __name__=="__main__":unittest.main()
