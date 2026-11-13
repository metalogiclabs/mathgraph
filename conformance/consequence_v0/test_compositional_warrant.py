"""Finite compositional warrant preservation: independent reference oracle.

The theorem here is exhaustive over a declared three-claim finite universe.
A policy is an external set of trusted facts and admissible inference rules.
A transport contract carries only explicitly preserved observations.
"""
import itertools
import unittest
from test_finite_foundation_calculus import closure

ATOMS=("p","q","r")
RULES=(("r",("p","q")),)

def independent_oracle(facts, rules):
    # Exhaustive subset enumeration; unlike the production worklist, this
    # chooses the smallest closed superset of the trusted premises.
    supersets=[]
    for bits in itertools.product((False,True),repeat=len(ATOMS)):
        candidate={a for a,b in zip(ATOMS,bits) if b}
        if not set(facts)<=candidate:continue
        if all(not set(premises)<=candidate or head in candidate for head,premises in rules):
            supersets.append(candidate)
    return set.intersection(*supersets)

def carry(source, allowed, policy):
    # An adapter cannot create facts, even if it advertises them.
    return set(source)&set(allowed)&set(policy)

class CompositionalWarrant(unittest.TestCase):
    def test_exhaustive_reference_semantics(self):
        for facts_bits in itertools.product((False,True),repeat=3):
            facts={a for a,b in zip(ATOMS,facts_bits) if b}
            self.assertEqual(closure(facts,RULES),independent_oracle(facts,RULES))
    def test_exhaustive_two_adapter_composition(self):
        for fb in itertools.product((False,True),repeat=3):
            source={a for a,b in zip(ATOMS,fb) if b}
            for ab in itertools.product((False,True),repeat=3):
                a={x for x,b in zip(ATOMS,ab) if b}
                for bb in itertools.product((False,True),repeat=3):
                    b={x for x,v in zip(ATOMS,bb) if v}
                    for pb in itertools.product((False,True),repeat=3):
                        policy={x for x,v in zip(ATOMS,pb) if v}
                        two=carry(carry(source,a,policy),b,policy)
                        composed=carry(source,a&b,policy)
                        self.assertEqual(two,composed)
                        self.assertTrue(two<=source&policy)
    def test_no_forged_derived_claim_from_transport(self):
        # A producer cannot claim r merely because it supplies an r-labelled
        # object; only a receiver's admitted inference rule may derive r.
        for source in ({"p"},{"q"},{"p","q"}):
            imported=carry(source,{"p","q","r"},{"p","q"})
            got=closure(imported,RULES)
            self.assertEqual("r" in got,source=={"p","q"})
    def test_revocation_alternate_support_under_external_policy(self):
        rules=(("r",("p",)),("r",("q",)))
        for live in (set(),{"p"},{"q"},{"p","q"}):
            got=closure(live,rules)
            self.assertEqual("r" in got,bool(live))
    def test_unsupported_cycle_stays_unwarranted(self):
        self.assertEqual(closure(set(),(("p",("q",)),("q",("p",)))),set())

if __name__=="__main__":unittest.main()
