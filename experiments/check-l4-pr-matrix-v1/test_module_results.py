from pathlib import Path
import importlib.util,sys,unittest,json,tempfile
sys.path.insert(0,str(Path(__file__).parent))
spec=importlib.util.spec_from_file_location('native_modules',Path(__file__).with_name('native_modules.py'))
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class GuardBoundary(unittest.TestCase):
    def test_false_guard_is_a_finite_observation(self):
        log='Audit.lean:5:0: error: Expression\n  x\ndid not evaluate to `true`\n'
        self.assertEqual(getattr(mod,'chunk_result',lambda *_:None)(1,log,2),{'qualified':True,'failed':[0]})
    def test_a_tool_error_cannot_masquerade_as_a_counterexample(self):
        log='Audit.lean:5:0: error: Expression\n  x\ndid not evaluate to `true`\nAudit.lean:6:0: error: unknown identifier\n'
        self.assertEqual(getattr(mod,'chunk_result',lambda *_:None)(1,log,2),{'qualified':False,'failed':[]})
    def test_timeout_with_partial_guard_output_is_unknown(self):
        log='Audit.lean:5:0: error: Expression\n  x\ndid not evaluate to `true`\n'
        self.assertEqual(getattr(mod,'chunk_result',lambda *_:None)(124,log,2),{'qualified':False,'failed':[]})
    def test_failing_guard_outside_frozen_corpus_is_unknown(self):
        log='Audit.lean:500:0: error: Expression\n  x\ndid not evaluate to `true`\n'
        self.assertEqual(getattr(mod,'chunk_result',lambda *_:None)(1,log,2),{'qualified':False,'failed':[]})
    def test_zero_exit_with_an_error_message_is_unknown(self):
        self.assertEqual(mod.chunk_result(0,'Other.lean:1:0: error: hidden failure',2),{'qualified':False,'failed':[]})
    def test_unknown_final_module_is_persisted(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'result.json';rows=[]
            record=getattr(mod,'record_result',lambda *_:None)
            record(p,{'controller_sha':'frozen'},rows,{'pr':1,'status':'NO_DIFFERENCE_IN_FINITE_CORPUS'})
            record(p,{'controller_sha':'frozen'},rows,{'pr':2,'status':'UNKNOWN'})
            self.assertTrue(p.exists())
            if p.exists(): self.assertEqual([x['status'] for x in json.loads(p.read_text())['modules']],['NO_DIFFERENCE_IN_FINITE_CORPUS','UNKNOWN'])

if __name__=='__main__':unittest.main()
