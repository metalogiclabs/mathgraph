import unittest
from evaluate import test_summary,correct_source,TEST_NAME
import json
from pathlib import Path

def evt(action,test=None):
 d={'Action':action,'Package':'p'}
 if test:d['Test']=test
 return json.dumps(d)

class SemanticQualificationTests(unittest.TestCase):
 def test_green_empty_suite_abstains(self):
  self.assertEqual(test_summary(evt('pass'),0)['status'],'UNKNOWN_ZERO_NAMED_TESTS')
 def test_named_base_failure_witness(self):
  s='\n'.join([evt('run',TEST_NAME),evt('fail',TEST_NAME),evt('fail')]);self.assertEqual(test_summary(s,1)['status'],'FAIL_NATIVE_ASSERTION')
 def test_exact_head_success_witness(self):
  s='\n'.join([evt('run',TEST_NAME),evt('pass',TEST_NAME),evt('pass')]);self.assertEqual(test_summary(s,0)['status'],'PASS_SOURCE_NATIVE')
 def test_wrong_named_test_does_not_count(self):
  s='\n'.join([evt('run','TestOther'),evt('fail','TestOther')]);self.assertEqual(test_summary(s,1)['status'],'UNKNOWN_ZERO_NAMED_TESTS')
 def test_panicking_test_is_not_an_assertion_witness(self):
  s='\n'.join([evt('run',TEST_NAME),json.dumps({'Action':'output','Test':TEST_NAME,'Output':'panic: expected fatal'}),evt('fail',TEST_NAME)])
  self.assertEqual(test_summary(s,1)['status'],'UNKNOWN_TEST_PANIC_NOT_ASSERTION')
 def test_wrong_source_sha_rejected(self):
  self.assertFalse(correct_source(Path('.'), 'x'*40))
if __name__=='__main__':unittest.main()
