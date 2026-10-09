import csv
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from submission_gate import COLUMNS, validate_submission

class SubmissionGateTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path=Path(self.folder.name)/'candidate.csv'
        self.good=dict(zip(COLUMNS,['q1','How much?','17 kWh','17','kWh',"['p1']","['https://example.org/p1']","['17 kWh']",'Candidate only.']))
    def write(self,rows,columns=COLUMNS):
        with self.path.open('w',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(rows)
    def test_valid_roundtrip_does_not_rewrite_values(self):
        self.good['answer_value']='0';self.good['answer']='0 kWh'
        self.write([self.good]);before=self.path.read_bytes()
        audit=validate_submission(self.path,['q1'])
        self.assertEqual(audit['rows'],1);self.assertEqual(audit['null_cells'],0)
        self.assertEqual(self.path.read_bytes(),before)
    def test_each_empty_column_is_rejected(self):
        for col in COLUMNS:
            with self.subTest(col=col):
                self.write([dict(self.good,**{col:''})])
                with self.assertRaisesRegex(ValueError,'Empty submission fields'):
                    validate_submission(self.path,['q1'])
    def test_na_like_nonempty_strings_are_rejected(self):
        for token in ('NA','NaN','null','None'):
            with self.subTest(token=token):
                self.write([dict(self.good,answer_unit=token)])
                with self.assertRaisesRegex(ValueError,'null values'):
                    validate_submission(self.path,['q1'])
    def test_explicit_abstention_is_allowed(self):
        row=dict(self.good)
        for col in COLUMNS[2:]:row[col]='is_blank'
        row['answer']='No supported answer.';row['explanation']='No evidence.'
        self.write([row]);self.assertEqual(validate_submission(self.path,['q1'])['rows'],1)
    def test_ids_cannot_be_substituted(self):
        self.write([self.good])
        with self.assertRaisesRegex(ValueError,'IDs differ'):validate_submission(self.path,['q2'])
    def test_duplicate_ids_are_rejected(self):
        self.write([self.good,self.good])
        with self.assertRaises(ValueError):validate_submission(self.path,['q1','q2'])
    def test_shape_is_enforced(self):
        self.write([self.good],tuple(reversed(COLUMNS)))
        with self.assertRaisesRegex(ValueError,'columns'):validate_submission(self.path,['q1'])
    def test_whitespace_and_missing_rows_are_rejected(self):
        self.write([dict(self.good,answer='   ')])
        with self.assertRaises(ValueError):validate_submission(self.path,['q1'])
        self.write([])
        with self.assertRaises(ValueError):validate_submission(self.path,['q1'])

if __name__=='__main__':unittest.main()
