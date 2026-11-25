import unittest
import select_cases as s


class SelectionTests(unittest.TestCase):
    def test_metadata_status_is_not_part_of_normalized_problem(self):
        forms = s.smt_forms('; expected outcome hidden\n(set-info :status sat)\n(declare-fun p () Bool)\n(assert (or p (not p)))\n(check-sat)')
        clean = [x for x in forms if x[:1] != ['set-info']]
        self.assertTrue(s.pure_boolean(forms))
        text = '\n'.join(map(s.smt_text, clean))
        self.assertNotIn(':status', text)
        self.assertNotIn('expected outcome', text)
        self.assertIn('(assert (or p (not p)))', text)

    def test_semicolons_in_strings_and_quoted_names_survive(self):
        forms = s.smt_forms('(set-info :source "a;b") ; comment\n(declare-const |p;q| Bool)\n(assert |p;q|)\n(check-sat)')
        self.assertEqual(forms[0], ['set-info', ':source', '"a;b"'])
        self.assertTrue(s.pure_boolean(forms))

    def test_integer_or_quantified_problem_is_not_boolean_eligible(self):
        self.assertFalse(s.pure_boolean(s.smt_forms('(declare-const n Int)(assert (= n 1))(check-sat)')))
        self.assertFalse(s.pure_boolean(s.smt_forms('(declare-const p Bool)(assert (forall ((q Bool)) (= p q)))(check-sat)')))

    def test_source_record_identity_and_pointer_are_retained(self):
        r = {'reqid': 'T', 'fulltext': 'A requirement', 'semantics': {'CoCoSpecCode': 'H(p)'}}
        self.assertEqual(list(s.walk_requirements({'requirements': [r]})), [('/requirements/0', r)])


if __name__ == '__main__':
    unittest.main()
