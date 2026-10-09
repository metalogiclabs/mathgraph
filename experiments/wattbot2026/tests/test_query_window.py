import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from query_window import query_window, window_passages

class WindowTests(unittest.TestCase):
    def test_tail_evidence_not_lost(self):
        text = 'Administrative background discussion. ' * 50 + ' Training electricity consumption was 1287 MWh.'
        got = query_window('What was the training electricity consumption?', text)
        self.assertIn('1287 MWh', got['text'])
        self.assertEqual(got['text'], text[got['start']:got['end']])
        self.assertLessEqual(len(got['text']), 1100)

    def test_middle_evidence_not_lost(self):
        text = 'Routine introduction. ' * 70 + ' Cooling water consumption was 73 litres.' + ' Historical appendix. ' * 70
        got = query_window('What was the cooling water consumption?', text, 400)
        self.assertIn('73 litres', got['text'])
        self.assertEqual(got['text'], text[got['start']:got['end']])
        self.assertLessEqual(len(got['text']), 400)

    def test_short_text_is_unchanged(self):
        text = 'The training run used 17 kWh.'
        self.assertEqual(query_window('energy?', text)['text'], text)

    def test_no_overlap_keeps_prefix(self):
        text = 'alpha beta gamma ' * 300
        self.assertEqual(query_window('zebra quasar', text, 80), {'text':text[:80],'start':0,'end':80})

    def test_no_content_or_question(self):
        self.assertEqual(query_window('why?', '')['text'], '')
        self.assertEqual(query_window('', 'x'*2000)['start'], 0)

    def test_deterministic_and_unicode(self):
        text = 'Historical facts. '*150 + ' Énergie coût electricity 17.5 MWh; water 23 litres.'
        first = query_window('What electricity and water?', text, 200)
        self.assertEqual(first, query_window('What electricity and water?', text, 200))
        self.assertEqual(first['text'], text[first['start']:first['end']])

    def test_source_identity_order_and_original_are_preserved(self):
        pages = [{'ref_id':'p1','page':7,'pdf_sha256':'abc','text':'old ' * 500 + ' water use 12 litres'},
                 {'ref_id':'p2','page':8,'pdf_sha256':'def','text':'water use 14 litres'}]
        original = [dict(p) for p in pages]
        got = window_passages('What water use?', pages, 80)
        self.assertEqual(pages, original)
        for parent, child in zip(pages, got):
            for key in ('ref_id','page','pdf_sha256'):
                self.assertEqual(parent[key], child[key])
            self.assertEqual(child['text'], parent['text'][child['excerpt_start']:child['excerpt_end']])
            self.assertLessEqual(len(child['text']), 80)

    def test_positive_limit(self):
        for limit in (0,-1):
            with self.assertRaises(ValueError):
                query_window('x','xyz',limit)

if __name__ == '__main__':
    unittest.main()
