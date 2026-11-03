import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('contract',Path(__file__).with_name('contract.py'))
mod=importlib.util.module_from_spec(spec)
if Path(spec.origin).exists():spec.loader.exec_module(mod)

class ContractBoundary(unittest.TestCase):
    def test_multifile_discovery_preserves_uncovered_paths(self):
        files=[{'filename':'Scripts/Punt/Price.lean','status':'added'},{'filename':'Scripts/Main/PuntPrice.lean','status':'added'},{'filename':'Tests/Guards/Proofs/X.lean','status':'modified'}]
        result=getattr(mod,'scope',lambda *_:None)(files)
        self.assertEqual(result,{'modules':['Scripts.Main.PuntPrice','Scripts.Punt.Price'],'uncovered':['Tests/Guards/Proofs/X.lean'],'deleted_modules':[],'base_modules':[]})
    def test_path_traversal_is_rejected(self):
        with self.assertRaises(ValueError):getattr(mod,'scope',lambda *_:None)([{'filename':'Scripts/../Evil.lean','status':'modified'}])
    def test_transitive_imports_are_discovered_automatically(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'Scripts').mkdir()
            (p/'Scripts/A.lean').write_text('module\npublic import Scripts.B\npublic import Lean\n')
            (p/'Scripts/B.lean').write_text('module\npublic import Std.Data.HashSet\n')
            self.assertEqual(getattr(mod,'closure',lambda *_:None)(p,['Scripts.A']),['Scripts.A','Scripts.B'])
    def test_external_project_import_is_unknown_not_silently_omitted(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'Scripts').mkdir();(p/'Scripts/A.lean').write_text('import L4YAML.Parser\n')
            with self.assertRaises(ValueError):getattr(mod,'closure',lambda *_:None)(p,['Scripts.A'])
    def test_incomplete_arm_cannot_claim_introduced_failure(self):
        result=getattr(mod,'comparison',lambda *_:None)({'qualified':False,'failed':[]},{'qualified':True,'failed':[1]})
        self.assertEqual(result,'UNKNOWN')
    def test_baseline_failure_is_not_called_a_new_defect(self):
        result=getattr(mod,'comparison',lambda *_:None)({'qualified':True,'failed':[1]},{'qualified':True,'failed':[1]})
        self.assertEqual(result,'FAILURE_ON_BOTH_REVISIONS')
    def test_new_and_resolved_failure_directions(self):
        compare=getattr(mod,'comparison',lambda *_:None)
        self.assertEqual(compare({'qualified':True,'failed':[]},{'qualified':True,'failed':[1]}),'NEW_FROZEN_PROBE_FAILURE')
        self.assertEqual(compare({'qualified':True,'failed':[1]},{'qualified':True,'failed':[]}),'RESOLVED_FROZEN_PROBE_FAILURE')
    def test_changed_failure_witness_is_never_inherited(self):
        compare=getattr(mod,'comparison',lambda *_:None)
        self.assertEqual(compare({'qualified':True,'failed':[1]},{'qualified':True,'failed':[2]}),'FAILURE_ON_BOTH_REVISIONS')
    def test_live_file_list_cannot_substitute_for_sha_bound_comparison(self):
        check=getattr(mod,'pinned_files',lambda *_:None)
        with self.assertRaises(ValueError):check({'files':[]},'a'*40,'b'*40)
    def test_pinned_comparison_rejects_truncation_and_wrong_head(self):
        check=getattr(mod,'pinned_files',lambda *_:None)
        for data in [dict(base_commit={'sha':'a'*40},commits=[{'sha':'c'*40}],total_commits=1,files=[]),dict(base_commit={'sha':'a'*40},commits=[{'sha':'b'*40}],total_commits=1,files=[{}]*300)]:
            with self.assertRaises(ValueError):check(data,'a'*40,'b'*40)
    def test_renames_compile_old_and_new_modules_on_the_right_arms(self):
        row={'filename':'Scripts/B.lean','previous_filename':'Scripts/A.lean','status':'renamed'}
        result=mod.scope([row]);self.assertEqual(result.get('base_modules'),['Scripts.A']);self.assertEqual(result['modules'],['Scripts.B'])
    def test_move_outside_scripts_retains_the_base_module(self):
        row={'filename':'Other/A.lean','previous_filename':'Scripts/A.lean','status':'renamed'}
        self.assertEqual(mod.scope([row]).get('base_modules'),['Scripts.A'])
    def test_required_module_cannot_silently_disappear(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):getattr(mod,'required_roots',lambda *_:None)(Path(t),['Scripts.Missing'])

if __name__=='__main__':unittest.main()
