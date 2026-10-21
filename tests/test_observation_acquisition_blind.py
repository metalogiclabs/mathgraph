"""Independent acceptance controls; intentionally only finite grammar synthesis."""
import unittest
from research.observation_acquisition_external_v1.candidate import construct
from research.observation_acquisition_external_v1.baseline import compare

class BlindSynthesis(unittest.TestCase):
    def test_prospective_finite_exhaustive(self):
        # 3-bit state, a readable bit and two hidden bits; all reversible
        # bit operations independently supplied in advance.
        states=tuple(range(8))
        trans={"flip":{x:x^1 for x in states},
               "couple1":{x:x^((x>>1)&1) for x in states},
               "couple2":{x:x^((x>>2)&1) for x in states}}
        obs={x:x&1 for x in states}
        import itertools
        for k in range(1,4):
            for subset in itertools.combinations(states,k):
                a=construct(subset,trans,obs,max_depth=4)
                b=compare(subset,trans,obs,max_depth=4)
                self.assertEqual(a["status"],b["status"],subset)
                if a["status"]=="FOUND":
                    self.assertEqual(len(a["program"]),len(b["program"]),subset)
    def test_inaccessible_observation_stays_unknown(self):
        s=(0,2)
        trans={"flip":{x:x^1 for x in range(4)}}
        obs={x:x&1 for x in range(4)}
        for f in (construct,compare):
            self.assertEqual(f(s,trans,obs,max_depth=5)["status"],
                             "UNKNOWN_NO_WITNESS_IN_BOUNDED_GRAMMAR")
    def test_explicit_budget(self):
        states=(0,1,2)
        actions={"identity":{x:x for x in range(3)}}
        obs={x:0 for x in range(3)}
        self.assertEqual(construct(states,actions,obs,max_nodes=0)["status"],"UNKNOWN_BUDGET")
        self.assertEqual(compare(states,actions,obs,max_nodes=0)["status"],"UNKNOWN_BUDGET")
    def test_constructor_rejects_bad_domain(self):
        with self.assertRaisesRegex(ValueError,"UNLAWFUL_TRANSITION_DOMAIN"):
            construct((0,1),{"bad":{0:0}},{0:0,1:1})
if __name__=="__main__":
    unittest.main()
