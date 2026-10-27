import unittest
from extractor import classify,authorized,all_cases,probes
class ACSLImplicationTests(unittest.TestCase):
 def test_pair_max_conjunction(self):
  c=r"""/*@ ensures \result == x || \result == y; ensures \result >= x && \result >= y; */"""
  self.assertEqual(classify(c)["family"],"SCALAR_PAIR_MAX")
 def test_array_quantifier_entailment(self):
  c=r"""/*@ requires n > 0; ensures \forall integer k; 0 <= k < n ==> \result >= a[k];
           ensures \exists integer k; 0 <= k < n && \result == a[k]; */"""
  self.assertEqual(classify(c)["family"],"QUANTIFIED_ARRAY_MAX")
 def test_conjunctive_implication_does_not_overconstrain_odd(self):
  c=r"""/*@ requires n > 0; ensures \forall integer k; (0<=k<n) && (k%2==0) ==> (a[k] == 0); */"""
  v=classify(c);self.assertEqual(v["family"],"EVEN_INDEX_ZERO_ONLY")
  self.assertTrue(v["partial_spec"])
  self.assertTrue(authorized(v["family"],(1,2,3,4),(0,999,0,-999),None))
  self.assertFalse(authorized(v["family"],(1,2,3,4),(1,2,0,4),None))
 def test_drop_one_required_clause_abstains(self):
  c=r"""/*@ ensures \result == x || \result == y; */"""
  self.assertEqual(classify(c)["status"],"UNKNOWN_UNSUPPORTED_CONTRACT")
 def test_drop_implication_abstains(self):
  c=r"""/*@ requires n > 0; ensures \forall integer k; (0<=k<n) && (k%2==0) && (a[k] == 0); */"""
  self.assertEqual(classify(c)["status"],"UNKNOWN_UNSUPPORTED_CONTRACT")
 def test_added_requirement_abstains(self):
  c=r"""/*@ ensures \result == x || \result == y; ensures \result >= x && \result >= y; requires x>0; */"""
  self.assertEqual(classify(c)["status"],"UNKNOWN_UNSUPPORTED_CONTRACT")
 def test_contradictory_postcondition_abstains(self):
  c=r"""/*@ ensures \result == x || \result == y; ensures \result >= x && \result >= y; ensures \result == 0; */"""
  self.assertEqual(classify(c)["status"],"UNKNOWN_UNSUPPORTED_CONTRACT")
 def test_missing_array_frame_abstains(self):
  c=r"""/*@ requires n > 0; requires \valid_read(a); ensures \forall integer k; 0 <= k < n ==> \result >= a[k];
    ensures \exists integer k; 0 <= k < n && \result == a[k]; */"""
  self.assertEqual(classify(c)["status"],"UNKNOWN_UNSUPPORTED_CONTRACT")
 def test_source_supports_real_conjunctive_guard(self):
  c=r"""/*@ requires n > 0; requires \valid(a + (0..n-1));
   ensures \forall integer k; (0<=k<n) && (k%2==0) ==> (a[k] == 0); */"""
  self.assertEqual(classify(c)["family"],"EVEN_INDEX_ZERO_ONLY")
 def test_frozen_census(self):
  self.assertEqual({x:sum(1 for _ in all_cases(x)) for x in
        ("SCALAR_PAIR_MAX","QUANTIFIED_ARRAY_MAX","ALL_EVEN_BOOLEAN","EVEN_INDEX_ZERO_ONLY","INDEX_DOUBLE_GUARDED")},
        {"SCALAR_PAIR_MAX":49,"QUANTIFIED_ARRAY_MAX":780,"ALL_EVEN_BOOLEAN":780,
         "EVEN_INDEX_ZERO_ONLY":780,"INDEX_DOUBLE_GUARDED":5})
 def test_probes_within_predeclared_domains(self):
  for k in ("SCALAR_PAIR_MAX","QUANTIFIED_ARRAY_MAX","ALL_EVEN_BOOLEAN","EVEN_INDEX_ZERO_ONLY","INDEX_DOUBLE_GUARDED"):
    self.assertTrue(set(probes(k)).issubset(set(all_cases(k))))
if __name__=="__main__":unittest.main()
