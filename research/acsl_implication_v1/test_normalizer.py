import unittest
from normalizer import normalize,inputs,probes,authorized
class Tests(unittest.TestCase):
 def test_max_implication_and_existence(self):
  c=r"""/*@ requires n>0; ensures \forall integer k; 0<=k<n ==> \result >= a[k]; ensures \exists integer k; 0<=k<n && \result==a[k]; assigns \nothing; */ int arraymax(int *a,int n){return 0;}"""
  x=normalize(c);self.assertEqual(x["family"],"MAX_OF_ARRAY")
  self.assertTrue(x["frame_unchanged"]);self.assertEqual(len(probes(x)),3)
  self.assertTrue(authorized(x,(1,2),(1,2),2))
  self.assertFalse(authorized(x,(1,2),(1,2),1))
 def test_even_behavior(self):
  c=r"""/*@ requires n>0; behavior all_even: assumes \forall integer k; 0<=k<n ==> a[k]%2 == 0; ensures \result == 1; behavior all_not_even: assumes \exists integer k; 0<=k<n && a[k]%2 != 0; ensures \result == 0; assigns \nothing; */ int areElementsEven(int *a,int n){return 0;}"""
  x=normalize(c);self.assertEqual(x["family"],"ALL_EVEN_01")
  self.assertTrue(authorized(x,(2,4),(2,4),1));self.assertFalse(authorized(x,(2,3),(2,3),1))
 def test_zero_even_positions_does_not_invent_odd_frame(self):
  c=r"""/*@ requires n>0; ensures \forall integer k; (0<=k<n) && (k%2==0) ==> (a[k] == 0); */ void func(int *a,int n) {}"""
  x=normalize(c);self.assertEqual(x["family"],"ZERO_EVEN_POSITIONS")
  self.assertTrue(authorized(x,(9,7,5),(0,999,0),None))
  self.assertFalse(authorized(x,(9,7,5),(9,7,0),None))
 def test_index_double_pre_and_post(self):
  c=r"""/*@ requires n>0; requires \forall integer k; 0<=k<n ==> a[k] == k && 2*k <= INT_MAX; ensures \forall integer k; 0<=k<n ==> a[k] == 2*k; */ void arrayDouble(int *a,int n) {}"""
  x=normalize(c);self.assertEqual(x["family"],"DOUBLE_INDEX_INITIALIZED")
  self.assertEqual(tuple(inputs(x))[0],(0,))
  self.assertTrue(authorized(x,(0,1,2),(0,2,4),None))
 def test_old_pointer_abstention(self):
  c=r"""/*@ requires \separated(a,b); ensures \old(*b) ==> *a==0; */ void reset(int *a,int const *b) {}"""
  self.assertEqual(normalize(c)["status"],"UNKNOWN_UNSUPPORTED")
if __name__=="__main__":unittest.main()
