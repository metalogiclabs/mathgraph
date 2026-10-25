"""Adversarial conditional support-policy tests. No physical or safety claims."""
import random
import unittest
from assurance_policy_envelope import Rule, evaluate, oracle_recursive

class PolicyEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.claims = {"C1":"low", "C2":"alternative", "C3":"root"}
        self.rules = {
            "C1":[Rule("e1","C1",("E1",))],
            "C2":[Rule("e2","C2",("E2",)),
                  Rule("e3","C2",("E3",))],
            "C3":[Rule("r1","C3",("C1","C2"))]
        }

    def check(self, ev, policy="all", rules=None, claims=None):
        rules = self.rules if rules is None else rules
        claims = self.claims if claims is None else claims
        return evaluate(rules,ev,policy=policy,claims=claims)

    def test_all_receipts_support_both_policies(self):
        for p in ("all","any"):
            self.assertEqual(self.check({"E1","E2","E3"},p),frozenset(self.claims))

    def test_single_withdrawal_causes_policy_ambiguity(self):
        ev={"E1","E2"}
        self.assertEqual(self.check(ev,"all"),frozenset({"C1"}))
        self.assertEqual(self.check(ev,"any"),frozenset(self.claims))

    def test_common_premise_withdraws_root_both_policies(self):
        for p in ("all","any"):
            self.assertNotIn("C3", self.check({"E2","E3"},p))

    def test_unknown_evidence_is_not_automatically_true(self):
        self.assertEqual(self.check(set()),frozenset())

    def test_no_incoming_rules_cannot_be_a_warrant(self):
        r=dict(self.rules)
        r["C1"]=[]
        self.assertNotIn("C1",self.check({"E1","E2","E3"},rules=r))

    def test_missing_dependency_will_fail_closed(self):
        r=dict(self.rules)
        r["C3"]=[Rule("r","C3",("UNNAMED",))]
        self.assertNotIn("C3",self.check({"E1","E2","E3"},rules=r))

    def test_invalid_policy(self):
        with self.assertRaises(ValueError):
            self.check({"E1","E2","E3"},policy="guess")

    def test_unknown_extra_receipt_does_not_promote(self):
        for p in ("all","any"):
            self.assertEqual(self.check({"FAKE"},p),frozenset())

    def test_relation_is_conjunctive(self):
        r=dict(self.rules)
        r["C1"]=[Rule("multi","C1",("E1","E3"))]
        self.assertNotIn("C1",self.check({"E1","E2"},rules=r))

    def test_inference_is_not_atomic_independent_premises(self):
        self.assertNotIn("C3",self.check({"E1","E2"},policy="all"))
        self.assertIn("C3",self.check({"E1","E2"},policy="any"))

    def test_any_vs_all_monotonic_when_fixed_graph(self):
        for mask in range(8):
            ev={f"E{i+1}" for i in range(3) if (mask>>i)&1}
            self.assertTrue(self.check(ev,"all") <= self.check(ev,"any"))

    def test_more_receipts_cannot_destroy_support(self):
        for p in ("all","any"):
            for mask in range(8):
                ev={f"E{i+1}" for i in range(3) if (mask>>i)&1}
                self.assertTrue(self.check(ev,p) <= self.check(ev|{"E1","E2","E3"},p))

    def test_independent_dag_oracle(self):
        for policy in ("all","any"):
            for mask in range(8):
                ev={f"E{i+1}" for i in range(3) if (mask>>i)&1}
                self.assertEqual(self.check(ev,policy),
                                 oracle_recursive(self.rules,ev,policy=policy,claims=self.claims))

    def test_deterministic_generated_dags_against_oracle(self):
        rng=random.Random(10025)
        eids=["E0","E1","E2","E3"]
        for _ in range(150):
            claims={f"C{i}":f"placeholder {i}" for i in range(5)}
            r={}
            for i in range(5):
                possible=eids+[f"C{j}" for j in range(i)]
                rules=[]
                for j in range(rng.randrange(4)):
                    n=rng.randrange(1, min(3,len(possible))+1)
                    chosen=tuple(rng.sample(possible,n))
                    rules.append(Rule(f"R{i}_{j}",f"C{i}",chosen))
                r[f"C{i}"]=rules
            for mask in range(16):
                ev={f"E{i}" for i in range(4) if (mask>>i)&1}
                for mode in ("all","any"):
                    lhs=evaluate(r,ev,policy=mode,claims=claims)
                    rhs=oracle_recursive(r,ev,policy=mode,claims=claims)
                    self.assertEqual(lhs,rhs)

    def test_separate_condition_no_receipts_no_approval(self):
        self.assertEqual(len(self.check(set(),"all")),0)
        self.assertEqual(len(self.check(set(),"any")),0)

if __name__ == "__main__":
    unittest.main()
