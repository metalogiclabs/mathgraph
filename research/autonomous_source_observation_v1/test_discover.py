import unittest
from discover import classify,cases,authorized
class SourceOnlyTests(unittest.TestCase):
  def test_boolean_result_inferred(self):
    s=r"""/*@ requires n > 0;
     behavior present:
     assumes \exists integer i; i >= 0;
     ensures \result == 1;
     behavior not_present:
     assumes \forall integer i; i != 4;
     ensures \result == 0;
     complete behaviors;
    */ int arraysearch(int* a,int x,int n){return 0;}"""
    q=classify(s);self.assertEqual(q["family"],"BOOLEAN_PRESENCE")
    self.assertFalse(q["empty_allowed"])
    self.assertEqual(q["parameter_positions"],{"array":0,"length":2,"key":1})
  def test_absence_negative_one(self):
    s=r"""/*@ behavior present:
     assumes \exists integer i; i >= 0;
     ensures a[\result] == x;
     behavior missing:
     assumes \forall integer i; i != 3;
     ensures \result == -1;
    */ int search(int* a,int n,int x){return -1;}"""
    q=classify(s);self.assertEqual(q["family"],"INDEX_OR_NEGATIVE_ONE")
  def test_unknown_contract_abstains(self):
    s=r"""/*@ ensures \result >= -1; */ int search(int* a,int n,int x){return -1;}"""
    self.assertEqual(classify(s)["status"],"UNKNOWN_UNSUPPORTED_CONTRACT")
  def test_probes_are_source_only(self):
    spec={"family":"INDEX_OR_LENGTH","sorted_required":True,"empty_allowed":True}
    v=list(cases(spec))
    self.assertEqual(len(v),3)
    self.assertTrue(authorized(spec,(1,3),5,2))
    self.assertFalse(authorized(spec,(1,3),5,-1))
    self.assertTrue(authorized(spec,(1,3),3,1))
  def test_bool_in_range(self):
    spec={"family":"BOOLEAN_PRESENCE"}
    self.assertTrue(authorized(spec,(1,3),5,0))
    self.assertFalse(authorized(spec,(1,3),5,2))
    self.assertTrue(authorized(spec,(1,3),3,1))
if __name__=="__main__":unittest.main()
