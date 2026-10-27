import unittest
from oracle import cases,admissible,contract_ground_truth,EXPECTED_COUNT
class ProspectiveCases(unittest.TestCase):
    def test_frozen_census(self):
        self.assertEqual(sum(1 for _ in cases()),EXPECTED_COUNT)
    def test_absence_is_length_not_minus_one(self):
        self.assertTrue(admissible((1,2,3),4,3))
        self.assertFalse(admissible((1,2,3),4,-1))
    def test_duplicate_index_is_any_match(self):
        self.assertTrue(admissible((1,1,2),1,0))
        self.assertTrue(admissible((1,1,2),1,1))
        self.assertFalse(admissible((1,1,2),1,2))
    def test_empty_is_zero(self):
        self.assertTrue(admissible((),3,0))
        self.assertFalse(admissible((),3,1))
    def test_contract_oracle(self):
        self.assertEqual(contract_ground_truth((1,2,3),4)["valid_results"],[3])
if __name__=="__main__":unittest.main()
