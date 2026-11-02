import unittest
from native import guard_outcome
class GuardOutcomeTests(unittest.TestCase):
 def test_failed_guard_is_distinguished_from_type_error(self):
  self.assertEqual(guard_outcome(1,'Probe.lean:4:0: error: Expression\n  mathgraphCandidateProbe\ndid not evaluate to `true`')['guard_false'],True)
  self.assertEqual(guard_outcome(1,'Probe.lean:3:0: error: unknown identifier')['other_errors'],True)
 def test_mixed_error_cannot_be_a_counterexample(self):
  r=guard_outcome(1,'error: Expression did not evaluate to `true`\nerror: unknown identifier');self.assertTrue(r['other_errors'])
 def test_timeout_not_a_false_guard(self):self.assertTrue(guard_outcome(124,'')['other_errors'])
if __name__=='__main__':unittest.main()

class SpoofTests(unittest.TestCase):
 def test_unknown_identifier_cannot_spoof_guard(self):
  self.assertTrue(guard_outcome(1,'Probe.lean:3:0: error: unknown identifier «did not evaluate to `true`»')['other_errors'])
 def test_wrong_location_is_not_a_failed_trusted_guard(self):
  self.assertTrue(guard_outcome(1,'Probe.lean:3:0: error: Expression\n  mathgraphCandidateProbe\ndid not evaluate to `true`')['other_errors'])
