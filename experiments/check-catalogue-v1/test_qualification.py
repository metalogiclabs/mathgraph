from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
from unittest import mock

SPEC=importlib.util.spec_from_file_location('catalogue_qualification',Path(__file__).with_name('qualify.py'))
Q=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(Q)


class QualificationTests(unittest.TestCase):
    def test_real_combined_child_preserves_parent_and_caller_checkout(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); repo=root/'repo'; repo.mkdir()
            git=lambda *args: subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
            git('init','-q')
            path=repo/Q.REPORT_PATH; path.parent.mkdir(parents=True)
            source=('source\n'+Q.OLD_CONDITION+'\n').encode(); path.write_bytes(source)
            (repo/'other').write_text('original')
            git('add','.');git('-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','parent')
            parent=git('rev-parse','HEAD')
            (repo/'other').write_text('caller staged change');git('add','other')
            path.write_text('caller unstaged change')
            before=Q.repository_state(repo);status=git('status','--porcelain')
            first=root/'first';second=root/'second';first.mkdir();second.mkdir()
            expected=hashlib.sha256(source.replace(Q.OLD_CONDITION.encode(),Q.NEW_CONDITION.encode())).hexdigest()
            a=Q.prepare_status_child(repo,parent,first,hashlib.sha256(source).hexdigest(),expected)
            b=Q.prepare_status_child(repo,parent,second,hashlib.sha256(source).hexdigest(),expected)
            self.assertEqual(a['commit'],b['commit']);self.assertEqual(a['parent'],parent)
            self.assertEqual(git('diff-tree','--no-commit-id','--name-only','-r',parent,a['commit']),Q.REPORT_PATH)
            self.assertEqual(Q.repository_state(repo),before);self.assertEqual(git('status','--porcelain'),status)
            self.assertEqual(path.read_text(),'caller unstaged change')
            self.assertEqual(a['source_sha256'],expected)
            with self.assertRaisesRegex(RuntimeError,'SOURCE_PIN'):
                Q.prepare_status_child(repo,parent,first,'0'*64,expected)

    def test_qualification_rejects_missing_prompt_and_inherited_profile_success(self):
        result={'subjects':{'base':'A','head':'B'},'status':'COMPLETED_BOUNDED_AGREEMENT',
                'profile_counts':{'agreement':4,'discrepancy':0,'unknown':0,'not_run':0},
                'coverage':{'items':[{'id':i,'full_family_coverage':'UNESTABLISHED'} for i in range(1,105)],
                            'complete_failure_coverage':False},'profiles':{}}
        for profile in Q.PROFILE_CASE_IDS:
            result['profiles'][profile]={'status':'OBSERVED_AGREEMENT','base':{'mismatches':0},'head':{'mismatches':0}}
        with mock.patch.object(Q,'validate_coverage'):
            with self.assertRaisesRegex(RuntimeError,'PROFILE_RECEIPT'):
                Q.validate_aggregate(result,0,'A','B',(Q.NO_MISMATCHES,Q.NO_MISMATCHES),None)
        result['coverage']['items'].pop()
        with self.assertRaisesRegex(RuntimeError,'CATALOGUE'):
            Q.validate_aggregate(result,0,'A','B',(Q.NO_MISMATCHES,Q.NO_MISMATCHES),None)

    def test_partial_repair_cannot_receive_an_all_green_coverage_ledger(self):
        source=Q.ROOT/'integrations/mathgraph-check-github/catalogue-check-v1/catalogue.json'
        canonical=json.loads(source.read_text())
        coverage={'revision':canonical['revision'],'source':canonical['source'],
                  'catalogue_sha256':Q.digest(source.read_bytes()),
                  'items':[{**row,'status':'BOUNDED_AGREEMENT','incomplete':False,'checks':[],
                            'residual':'unassessed','full_family_coverage':'UNESTABLISHED'} for row in canonical['items']]}
        result={'coverage':coverage,'profile_counts':{'agreement':4,'discrepancy':0,'unknown':0,'not_run':0}}
        with self.assertRaisesRegex(RuntimeError,'PROFILE_COUNTS'):
            Q.validate_coverage(result,(Q.ORIGINAL_MISMATCHES,Q.PARTIAL_MISMATCHES))
        result['profile_counts']={'agreement':3,'discrepancy':2,'unknown':0,'not_run':0}
        with self.assertRaisesRegex(RuntimeError,'CATALOGUE_ROW_OUTCOME|CATALOGUE_PROFILE_MAPPING'):
            Q.validate_coverage(result,(Q.ORIGINAL_MISMATCHES,Q.PARTIAL_MISMATCHES))

    def test_failed_setup_is_retained_without_any_qualification_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'run'
            with mock.patch.object(Q,'verifier_identity',side_effect=RuntimeError('UNCOMMITTED_INPUT')):
                code=Q.main(['--repo',temp,'--out',str(out),'--lean','missing'])
            self.assertEqual(code,2)
            summary=json.loads((out/'summary.json').read_text())
            self.assertEqual(summary['engineering_qualification'],'FAILED')
            self.assertIn('UNCOMMITTED_INPUT',summary['failure'])
            self.assertEqual(summary['runs'],{})

if __name__=='__main__': unittest.main()
