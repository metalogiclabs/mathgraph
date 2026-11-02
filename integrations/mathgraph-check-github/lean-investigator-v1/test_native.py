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

class PilotIdentityTests(unittest.TestCase):
 def test_pr_profile_requires_actual_both_pinned_revisions(self):
  from native import validate_snapshot
  s={'repository':'metalogiclabs/L4YAML','head_sha':'a'*40,'base_sha':'b'*40,'module':'Scripts.Ledger','path':'Scripts/Ledger.lean','namespace':'Scripts.Ledger','cli_path':'Scripts/Main/CheckScriptsLedger.lean','cli_module':'Scripts.Main.CheckScriptsLedger','toolchain':'leanprover/lean4:v4.35.0','mode':'OWNED_FORK_PR_PILOT','command':'check','source':'head','base_source':'base','cli_source':'cli','base_cli_source':'cli'}
  self.assertTrue(validate_snapshot(s))
  for key,value in [('base_sha','main'),('module','Evil'),('repository','attacker/repo'),('base_cli_source','changed')]:
   with self.assertRaises(AssertionError): validate_snapshot({**s,key:value})
