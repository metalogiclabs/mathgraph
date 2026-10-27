import unittest
from oracle import require_counts,allowed,UINT_MAX
class PreregisteredTests(unittest.TestCase):
    def test_fixed_census(self):self.assertEqual(require_counts(),{"recursive_search":5467,"binary_search":1764})
    def test_unsigned_absence(self):
        self.assertTrue(allowed("recursive_search",(),0,UINT_MAX))
        self.assertFalse(allowed("recursive_search",(),0,-1))
    def test_signed_absence(self):
        self.assertTrue(allowed("binary_search",(),0,-1))
        self.assertFalse(allowed("binary_search",(),0,0))
    def test_duplicate_matches(self):
        self.assertTrue(allowed("recursive_search",(1,1),1,0))
        self.assertTrue(allowed("recursive_search",(1,1),1,1))
        self.assertTrue(allowed("binary_search",(1,1),1,0))
        self.assertTrue(allowed("binary_search",(1,1),1,1))
if __name__=="__main__":unittest.main()
