import importlib.util,json,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('rules',Path(__file__).with_name('rules.py'));rules=importlib.util.module_from_spec(spec)
if Path(spec.origin).exists():spec.loader.exec_module(rules)
HERE=Path(__file__).resolve().parent
class CliContract(unittest.TestCase):
 def setUp(self):
  self.contract=json.loads((HERE/'contract.json').read_text());self.case=json.loads((HERE/'cases.json').read_text())['ledger-diff'][0]
 def obs(self,**kw):return {'complete':True,'exit':0,'stdout':'report\n','stderr':'','effects':{},**kw}
 def compare(self,b=None,h=None,again=None):return getattr(rules,'compare_case',lambda *_:{'state':'MISSING'})(b or self.obs(),again or b or self.obs(),h or self.obs(),self.case,self.contract)
 def test_identical_native_observations_are_finite_parity(self):self.assertEqual(self.compare()['state'],'PARITY')
 def test_actual_stdout_exit_stderr_or_file_change_is_detected(self):
  for h in [self.obs(stdout='changed\n'),self.obs(exit=1),self.obs(stderr='warn\n'),self.obs(effects={'out':{'before':None,'after':'a'*64}})]:self.assertEqual(self.compare(h=h)['state'],'DIFFERENCE')
 def test_timeout_or_incomplete_observation_is_not_a_counterexample(self):self.assertEqual(self.compare(h=self.obs(complete=False,exit=124))['state'],'UNKNOWN')
 def test_broken_reference_is_not_parity_even_if_head_agrees(self):self.assertEqual(self.compare(b=self.obs(exit=1),h=self.obs(exit=1))['state'],'UNKNOWN')
 def test_nondeterministic_reference_cannot_authorize_comparison(self):self.assertEqual(self.compare(again=self.obs(stdout='other'))['state'],'UNKNOWN')
 def test_only_declared_provenance_line_may_change(self):
  lines=self.contract['generator_provenance_lines'];f=getattr(rules,'project_stdout',lambda *_:'MISSING')
  self.assertEqual(f('header\n'+lines[0]+'\nbody\n','generator-provenance',self.contract),f('header\n'+lines[1]+'\nbody\n','generator-provenance',self.contract))
  self.assertNotEqual(f('header\n'+lines[0]+'\nbody\n','generator-provenance',self.contract),f('header\n'+lines[1]+'\nchanged\n','generator-provenance',self.contract))
  with self.assertRaises(ValueError):f('body\n','generator-provenance',self.contract)
 def test_error_category_is_explicit_and_empty_stderr_still_differs(self):
  self.case['expected_base_exit']=1;self.case['comparison']['stderr']='nonempty'
  b=self.obs(exit=1,stderr='Python trace');self.assertEqual(self.compare(b=b,h=self.obs(exit=1,stderr='Lean error'))['state'],'PARITY');self.assertEqual(self.compare(b=b,h=self.obs(exit=1))['state'],'DIFFERENCE')
 def test_workspace_effects_preserve_deletions_and_content_identity(self):
  f=getattr(rules,'effects',lambda *_:None);self.assertEqual(f({'a':'x','b':'y'},{'b':'z','c':'w'}),{'a':{'before':'x','after':None},'b':{'before':'y','after':'z'},'c':{'before':None,'after':'w'}})
 def test_unsafe_fixture_paths_are_rejected(self):
  f=getattr(rules,'safe_path',lambda *_:None)
  for name in ['../x','/x','a/../x','.lake/x','scripts/x','a\\x']:
   with self.assertRaises(ValueError):f(name)
 def test_project_closure_includes_original_cli_and_required_grammar_only(self):
  f=getattr(rules,'project_closure',lambda *_:None)
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'Scripts/Main').mkdir(parents=True);(p/'L4YAML').mkdir();(p/'Scripts/Main/X.lean').write_text('public import L4YAML.X\n');(p/'L4YAML/X.lean').write_text('import Lean\n');self.assertEqual(f(p,['Scripts.Main.X']),['L4YAML.X','Scripts.Main.X'])
 def test_missing_import_and_external_project_are_unknown(self):
  f=getattr(rules,'project_closure',lambda *_:None)
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'Scripts').mkdir();(p/'Scripts/X.lean').write_text('import Mathlib\n')
   with self.assertRaises(ValueError):f(p,['Scripts.X'])
   with self.assertRaises(ValueError):f(p,['Scripts.Absent'])

class LakeRegistration(unittest.TestCase):
 def test_transitive_modules_are_registered_as_build_roots(self):
  f=getattr(rules,'lake_config',lambda *_:'')
  s=f({'head_module':'Scripts.Main.X'},['Scripts.Main.X','Scripts.Helper','L4YAML.Surface.X','L4YAML.Surface.Y'])
  for m in ['Scripts.Main.X','Scripts.Helper','L4YAML.Surface.X','L4YAML.Surface.Y']:self.assertIn('`'+m,s)

class WorkspaceEffects(unittest.TestCase):
 def test_script_and_lake_outputs_cannot_be_hidden_by_infrastructure_exclusions(self):
  f=getattr(rules,'workspace_hashes',lambda *_:{})
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);before=f(p,{'file_bytes':10000,'files':100},{'scripts/oracle.py'})
   for name in ['scripts/observable.txt','.lake/observable.txt','scripts/oracle.py','.lake/build/lib/lean/Trusted.olean']:
    q=p/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_text('created')
   after=f(p,{'file_bytes':10000,'files':100},{'scripts/oracle.py'});delta=rules.effects(before,after)
   self.assertEqual(set(delta),{'scripts/observable.txt','.lake/observable.txt'})
   self.assertIn('scripts/oracle.py',f(p,{'file_bytes':10000,'files':100},set()))
