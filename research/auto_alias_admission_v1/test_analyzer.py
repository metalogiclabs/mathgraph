import unittest
from analyzer import extract_contract,separating_pairs
class Pairwise(unittest.TestCase):
 def test_mut_two_without_sep(self):
  c=r"""/*@ requires \valid(a) && \valid(b); assigns *a,*b; */ void swap(int* a,int* b){}"""
  out=extract_contract(c,"swap")
  self.assertEqual(out["obligations"][0]["source_alias_admission"],"PERMITTED_ABSENT_SEPARATION")
 def test_explicit_separated_pair(self):
  c=r"""/*@ requires \valid(a) && \valid_read(b); requires \separated(a,b); */ void incr(int* a,const int* b){}"""
  out=extract_contract(c,"incr")
  self.assertEqual(out["obligations"][0]["source_alias_admission"],"FORBIDDEN_EXPLICIT_SEPARATION")
 def test_two_inputs_share_output_separation(self):
  c=r"""/*@ requires \valid_read(p) && \valid_read(q) && \valid(r); requires \separated(p,r); requires \separated(q,r); */ void add(int* p,int* q,int* r){}"""
  out=extract_contract(c,"add")
  d={tuple(x["pair"]):x["source_alias_admission"] for x in out["obligations"]}
  self.assertEqual(d[("p","q")],"PERMITTED_ABSENT_SEPARATION")
  self.assertEqual(d[("p","r")],"FORBIDDEN_EXPLICIT_SEPARATION")
  self.assertEqual(d[("q","r")],"FORBIDDEN_EXPLICIT_SEPARATION")
 def test_nullable_input(self):
  c=r"""/*@ requires a == NULL || \valid_read(a); requires b == NULL || \valid_read(b); */ int max_ptr(int* a,int* b){return 0;}"""
  out=extract_contract(c,"max_ptr")
  self.assertEqual(out["obligations"][0]["source_nullable"],["a","b"])
 def test_unsupported_single_pointer(self):
  c=r"""/*@ requires \valid(a); */ void x(int* a){}"""
  self.assertEqual(extract_contract(c,"x")["status"],"UNKNOWN_SOURCE")
if __name__=="__main__":unittest.main()
