import unittest
from normalizer import classify,authorizes,cases,probes
class SourceOnly(unittest.TestCase):
 def test_conditional_reset_old_state(self):
  c=r"""/*@ requires \separated(a,b); assigns *a; ensures \old(*b) ==> *a == 0; ensures ! \old(*b) ==> *a == \old(*a); ensures *b == \old(*b); */ void reset(int* a,int const* b){}"""
  f=classify(c)["family"];self.assertEqual(f,"CONDITIONAL_RESET_OLD_FRAME")
  self.assertTrue(authorizes(f,(5,0),(5,0),None));self.assertFalse(authorizes(f,(5,0),(0,0),None))
  self.assertFalse(authorizes(f,(5,1),(0,2),None))
 def test_swap_distinct_scope(self):
  c=r"""/*@ assigns *a, *b; ensures *a == \old(*b) && *b == \old(*a); */ void swap(int* a,int* b){}"""
  q=classify(c);self.assertEqual(q["family"],"TWO_POINTER_SWAP_DISTINCT_SCOPE")
  self.assertTrue(q["distinct_pointer_scope_only"])
  self.assertTrue(authorizes(q["family"],(2,7),(7,2),None))
 def test_weak_array_spec_no_invented_frame(self):
  c=r"""/*@ requires 0 <= n1 < n && 0 <= n2 < n; ensures (arr[n2] == \old(arr[n1])) && (arr[n2] == \old(arr[n1])); */ void swap(int* arr,int n,int n1,int n2){}"""
  q=classify(c);self.assertTrue(q["no_inferred_frame"])
  self.assertTrue(authorizes(q["family"],((2,7,5),0,2),(999,888,2),None))
  self.assertFalse(authorizes(q["family"],((2,7,5),0,2),(2,7,5),None))
 def test_separated_pointer_frame(self):
  c=r"""/*@ requires \separated(p,q); assigns \nothing; ensures \result == *p + *q; */ int add(int* p,int* q){return 0;}"""
  f=classify(c)["family"];self.assertTrue(authorizes(f,(2,-4),(2,-4),-2))
  self.assertFalse(authorizes(f,(2,-4),(9,-4),-2))
 def test_label_relational_unknown(self):
  c=r"""/*@ predicate unchanged{L0,L1}(int* a) = \at(*a,L0)==\at(*a,L1); */ int foo(void){return 0;}"""
  self.assertEqual(classify(c)["status"],"UNKNOWN_UNSUPPORTED")
 def test_all_probes_within_frozen_corpus(self):
  families=["CONDITIONAL_RESET_OLD_FRAME","INCREMENT_OLD_FRAME","TWO_POINTER_SWAP_DISTINCT_SCOPE","WEAK_DUPLICATE_ARRAY_POST","POINTER_SUM_UNCHANGED","POINTER_PLUS_FIVE_UNCHANGED"]
  for family in families:
   self.assertEqual(len(probes(family)),3)
   allcases=set(cases(family))
   for x in probes(family):self.assertIn(x,allcases)
if __name__=="__main__":unittest.main()
