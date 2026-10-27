import unittest
from run_native import added,CASES
class SourceGateTests(unittest.TestCase):
    def test_appends_only_before_single_macro_close(self):
        s="verus! {\nfn main() {}\n} // verus!\n"
        x=added(s,"proof fn check() { assert(true); }")
        self.assertTrue(x.endswith("} // verus!\n"))
        self.assertEqual(x.count("} // verus!"),1)
    def test_rejects_ambiguous_insertions(self):
        with self.assertRaises(ValueError):added("fn main() {}","proof fn x() {}")
        with self.assertRaises(ValueError):added("} // verus! } // verus!","proof fn x() {}")
    def test_distinct_protected_obligations(self):
        for value in CASES.values():
            self.assertNotEqual(value[4],value[5])
            self.assertIn("assert(!",value[5])
if __name__=="__main__":unittest.main()
