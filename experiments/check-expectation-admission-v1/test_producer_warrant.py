import importlib.util,unittest
from pathlib import Path
p=Path(__file__).resolve().parents[2]/'integrations/mathgraph-check-github/pr-pilot-v1/producer-warrant.py'
s=importlib.util.spec_from_file_location('producer_warrant',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

class ProducerWarrantTests(unittest.TestCase):
    def facts(self):
        return {'subject':{'repository':'fixture/repo','head_sha':'a'*40,'sha256':'b'*64},
            'artifact_sha256':'c'*64,'requirement_sha256':'d'*64,'plan_sha256':'e'*64,
            'producer_parent':'f'*40,'producer_controller':'1'*40,'consumer_controller':'2'*40,
            'policy_sha256':'3'*64,'assumptions':['finite test fixture, not externally admitted evidence'],
            'request':{'number':1,'state':'open'}}
    def test_native_result_never_becomes_formal(self):
        r=m.project(self.facts());self.assertEqual(r['status'],'WARRANTED_BOUNDED_NATIVE');self.assertEqual(r['native_status'],'WARRANTED_BOUNDED_NATIVE')
    def test_current_request_withdrawal_preserves_physical_native_observation(self):
        f=self.facts();before=m.project(f);current=before['current_dependencies'].copy();current['consumer-request']='0'*64
        after=m.project(f,current);self.assertEqual(after['status'],'UNKNOWN');self.assertEqual(after['native_status'],'WARRANTED_BOUNDED_NATIVE');self.assertEqual(m.project(f)['states'],before['states'])
    def test_producer_evidence_withdrawal_disables_both_uses(self):
        f=self.facts();r=m.project(f);current=r['current_dependencies'].copy();current['producer-artifact:'+f['artifact_sha256']]='0'*64
        self.assertEqual(set(m.project(f,current)['states'].values()),{'UNKNOWN'})
    def test_status_and_self_hash_cannot_supply_missing_identities(self):
        with self.assertRaises(KeyError):m.project({'status':'WARRANTED_BOUNDED_NATIVE','sha256':'a'*64})

if __name__=='__main__':unittest.main()
