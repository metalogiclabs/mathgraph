import unittest
from source_oracle import UINT_MAX,census,vectors,authorized
class FrozenSourceTests(unittest.TestCase):
    def test_census(self):
        self.assertEqual(census(),{"sorted_minus_one":1764,"unsorted_uintmax":5467})
    def test_empty_sentinels(self):
        self.assertTrue(authorized("sorted_minus_one",(),1,-1))
        self.assertFalse(authorized("sorted_minus_one",(),1,0))
        self.assertTrue(authorized("unsorted_uintmax",(),1,UINT_MAX))
        self.assertFalse(authorized("unsorted_uintmax",(),1,-1))
    def test_duplicates_allow_any_matching_index(self):
        for case in ("sorted_minus_one","unsorted_uintmax"):
            self.assertTrue(authorized(case,(1,1,2),1,0))
            self.assertTrue(authorized(case,(1,1,2),1,1))
            self.assertFalse(authorized(case,(1,1,2),1,2))
    def test_unsorted_domain(self):
        self.assertIn(((2,-1,2),-1),set(vectors("unsorted_uintmax")))
    def test_uintmax_is_not_minus_one(self):
        self.assertNotEqual(UINT_MAX,-1)
        self.assertFalse(authorized("unsorted_uintmax",(0,1),2,2))
        self.assertTrue(authorized("unsorted_uintmax",(0,1),2,UINT_MAX))
if __name__=="__main__":unittest.main()
