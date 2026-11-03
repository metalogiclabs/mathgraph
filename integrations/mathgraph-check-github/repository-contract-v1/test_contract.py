import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('contract',Path(__file__).with_name('contract.py'))
mod=importlib.util.module_from_spec(spec)
if Path(spec.origin).exists():spec.loader.exec_module(mod)

class ContractBoundary(unittest.TestCase):
    def test_multifile_discovery_preserves_uncovered_paths(self):
        files=[{'filename':'Scripts/Punt/Price.lean','status':'added'},{'filename':'Scripts/Main/PuntPrice.lean','status':'added'},{'filename':'Tests/Guards/Proofs/X.lean','status':'modified'}]
        result=getattr(mod,'scope',lambda *_:None)(files)
        self.assertEqual(result,{'modules':['Scripts.Main.PuntPrice','Scripts.Punt.Price'],'uncovered':['Tests/Guards/Proofs/X.lean'],'deleted_modules':[]})
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

if __name__=='__main__':unittest.main()
