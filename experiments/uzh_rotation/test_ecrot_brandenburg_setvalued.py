import random,unittest
from audit_ecrot_brandenburg_setvalued import group_source, interval_oracle,explicit_oracle,summarize
def make(times,options):
    return [(t*1000000000,t*1000000000,float(v),bytes([i,j]))
            for i,(t,variants) in enumerate(zip(times,options))
            for j,v in enumerate(variants)]
class TestAlternatives(unittest.TestCase):
    def test_all_choices_short(self):
        d=summarize(group_source(make([0,1,2],[[.2],[.2,.4],[.2]])))
        self.assertEqual(d["status"],"NO_FULL_TURN_IN_ANY_RECORDED_SOURCE_CHOICE")
        self.assertEqual(d["source_choice_count"],2)
    def test_conflicting_bytes_preserved(self):
        d=summarize(group_source(make([0,1],[[0],[1,2]])))
        self.assertEqual(d["duplicate_groups"][0]["distinct_serializations"],2)
    def test_straddling_threshold_is_unknown(self):
        d=summarize(group_source(make([0,8],[[0.],[1.3,1.8]])))
        self.assertEqual(d["status"],"UNKNOWN_CROSSING_OR_DIRECTION")
    def test_full_then_reverse_does_not_falsely_reject(self):
        d=summarize(group_source(make([0,10,20],[[1],[1],[-1]])))
        self.assertNotEqual(d["status"],"NO_FULL_TURN_IN_ANY_RECORDED_SOURCE_CHOICE")
    def test_nominal_full_turn_still_no_control_authority(self):
        d=summarize(group_source(make([0,10],[[1],[1]])))
        self.assertEqual(d["status"],"ELIGIBLE_FOR_SEPARATE_VISUAL_REPLAY_ONLY")
        self.assertFalse(d["navigation_authorized"])
    def test_backward_time_rejected(self):
        with self.assertRaisesRegex(ValueError,"backward"):
            group_source(make([0,2,1],[[1],[1],[1]]))
    def test_nonfinite_rejected(self):
        with self.assertRaisesRegex(ValueError,"invalid source"):
            group_source(make([0,1],[[0],[float("nan")]]))
    def test_exact_independent_enumeration_random_finite(self):
        rng=random.Random(1274)
        for _ in range(48):
            n=rng.randrange(3,8)
            choices=[[rng.randrange(-4,7)/4 for _ in range(rng.randrange(1,3))]
                     for _ in range(n)]
            g=group_source(make(list(range(n)),choices))
            a=interval_oracle(g)
            b=explicit_oracle(g,max_combinations=512)
            self.assertEqual(b["status"],"EXHAUSTIVE")
            for k in ("final_low","final_high","max_abs_prefix"):
                self.assertEqual(a[k],b[k],(k,choices))
if __name__=="__main__":unittest.main()
