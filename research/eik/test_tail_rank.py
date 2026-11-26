from tail_rank import decision_tree,rank,sig_certificate
import unittest


class TailRankTests(unittest.TestCase):
    def test_exact_rank_boundary(self):
        thresholds=[100,90,80]
        for x,y in [(101,1),(100,1),(99,2),(90,2),(89,3),(80,3),(79,4)]:
            self.assertEqual(rank(x,thresholds),y)

    def test_threshold_falsifier(self):
        original=[100,90,80]
        mutant=[101,90,80]
        self.assertNotEqual(rank(100,original),rank(100,mutant))

    def test_tree_has_no_loop_or_table_index(self):
        s=decision_tree([100,90,80],'w','')
        self.assertNotIn('while',s)
        self.assertNotIn('[',s)
        self.assertEqual(s.count('return'),4)


if __name__=='__main__':
    unittest.main()
