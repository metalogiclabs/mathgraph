import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest

# Standalone local synthetic mechanics harness. In CI, the authoritative
# mathgraph_protocol module from the source repository is imported instead.
try:
    import mathgraph_protocol.capability_v1
except ModuleNotFoundError:
    pkg=types.ModuleType('mathgraph_protocol');pkg.__path__=[]
    sys.modules['mathgraph_protocol']=pkg
    j=types.ModuleType('mathgraph_protocol.json_strict')
    def strict_json_loads(data):
        def pairs(ps):
            d={}
            for k,v in ps:
                if k in d:raise ValueError('DUPLICATE_KEY')
                d[k]=v
            return d
        def forbid(_):raise ValueError('NONFINITE')
        return json.loads(data,object_pairs_hook=pairs,parse_constant=forbid)
    j.strict_json_loads=strict_json_loads;sys.modules[j.__name__]=j
    c=types.ModuleType('mathgraph_protocol.capability_v1')
    def validate_contract(v):
        expected={'schema_version','id','version','profile','claim','inputs','outputs','preconditions','guarantees','assumptions','boundary','implementation','evidence','limitations','extensions'}
        if not isinstance(v,dict) or set(v)!=expected or v['schema_version']!='mathgraph.capability-contract.v1':raise ValueError('BAD_DESCRIPTOR')
        return None
    def evaluate_contract(v):
        validate_contract(v)
        return {'validation':'VALID','qualification':'UNKNOWN','action_authorization':'NONE'}
    c.validate_contract=validate_contract;c.evaluate_contract=evaluate_contract
    sys.modules[c.__name__]=c

import bridge


def run(*args,cwd):
    p=subprocess.run(args,cwd=cwd,capture_output=True,text=True)
    if p.returncode:raise AssertionError((args,p.stdout,p.stderr))
    return p.stdout.strip()


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.d=tempfile.TemporaryDirectory(prefix='bridge-test-')
        self.addCleanup(self.d.cleanup)
        self.root=Path(self.d.name)
        self.repo=self.root/'src';self.repo.mkdir()
        run('git','init','-q',cwd=self.repo)
        run('git','config','user.email','test@local.invalid',cwd=self.repo)
        run('git','config','user.name','Test',cwd=self.repo)
        (self.repo/'go.mod').write_text('module example.local/fixture\n\ngo 1.23\n')
        (self.repo/'value.go').write_text('package fixture\nfunc Value() int {return 0}\n')
        run('git','add','.',cwd=self.repo);run('git','commit','-qm','base',cwd=self.repo)
        self.base=run('git','rev-parse','HEAD',cwd=self.repo)
        (self.repo/'value.go').write_text('package fixture\nfunc Value() int {return 1}\n')
        run('git','add','.',cwd=self.repo);run('git','commit','-qm','fix',cwd=self.repo)
        self.head=run('git','rev-parse','HEAD',cwd=self.repo)
        run('git','checkout','-q',self.base,cwd=self.repo)
        self.code=b'package fixture\nimport "testing"\nfunc TestMathGraphProposedWitness(t *testing.T) {if Value()!=1 {t.Fatal("not yet fixed")}}\n'
        self.proposal=bridge.canonical({'code':self.code.decode(),'observation_kind':'value comparison'})
        prior={'schema':'mathgraph.g2.go-native-qualification.v1','status':bridge.PREVIOUS_STATUS,
               'base_sha':self.base,'head_sha':self.head,'strict_g2':'UNKNOWN','strict_g3':'UNKNOWN',
               'results':[{'mode':'bridge','status':bridge.EVIDENCE_STATUS,
                            'proposal_sha256':bridge.digest(self.code),
                            **{k:{'status':v[0],'count':v[1]} for k,v in bridge.EXPECTED.items()}}]}
        self.evaluation=bridge.canonical(prior)
        self.pair={'repository':'example/local','package':'fixture','base':self.base,'head':self.head,
                   'mode':'bridge','origin_run':'123456789'}
        self.store=self.root/'store'

    def exp(self):
        return bridge.export(self.proposal,self.evaluation,self.pair,self.store)['root_sha256']

    def test_typed_export_stays_advisory_and_content_addressed(self):
        root=self.exp()
        pair,files=bridge.inspect(self.store,root)
        self.assertEqual(pair,self.pair)
        self.assertEqual(files['candidate.go'],self.code)
        self.assertEqual(root,self.exp())

    def test_prior_warrant_or_wrong_scope_refused(self):
        altered=json.loads(self.evaluation);altered['results'][0]['head']['status']='FAIL_NATIVE_ASSERTION'
        with self.assertRaisesRegex(ValueError,'UNKNOWN_PRIOR_NATIVE_BOUNDARY_head'):
            bridge.export(self.proposal,bridge.canonical(altered),self.pair,self.store)
        altered=json.loads(self.evaluation);altered['results'][0]['proposal_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'UNKNOWN_PRIOR_CODE_MISMATCH'):
            bridge.export(self.proposal,bridge.canonical(altered),self.pair,self.store)
        broken=dict(self.pair,base='0'*40)
        with self.assertRaisesRegex(ValueError,'UNKNOWN_PRIOR_SOURCE_MISMATCH'):
            bridge.export(self.proposal,self.evaluation,broken,self.store)

    def test_mutation_and_missing_object_fail_closed(self):
        root=self.exp();candidate=self.store/'objects'/root/'candidate.go'
        candidate.write_bytes(candidate.read_bytes()+b'// forged\n')
        with self.assertRaisesRegex(ValueError,'UNKNOWN_OBJECT_CONTENT_MISMATCH'):
            bridge.inspect(self.store,root)
        candidate.write_bytes(self.code)
        self.assertEqual(bridge.inspect(self.store,root)[0],self.pair)
        shutil.rmtree(self.store/'objects'/root)
        with self.assertRaisesRegex(ValueError,'UNKNOWN_CAPABILITY_WITHDRAWN'):
            bridge.inspect(self.store,root)

    def test_revocation_does_not_create_authority(self):
        root=self.exp()
        with self.assertRaisesRegex(ValueError,'UNKNOWN_REVOKED_OBJECT'):
            bridge.inspect(self.store,root,{root})
        self.assertEqual(bridge.inspect(self.store,root)[0],self.pair)

    def test_forged_receipt_never_grants_effect_authority(self):
        # The prior evaluation was synthesized by the local fixture itself.
        # Export is only a candidate until a fresh native replay happens.
        result=bridge.export(self.proposal,self.evaluation,self.pair,self.store)
        self.assertEqual(result['status'],'CANDIDATE_COLD_TRANSPORT')
        self.assertEqual(result['qualification'],'UNKNOWN_FRESH_REPLAY_REQUIRED')
        self.assertEqual(result['action_authorization'],'NONE')

    def test_bad_json_duplicate_denied(self):
        with self.assertRaises(ValueError):bridge.parse(b'{"a":1,"a":2}')

    def test_native_test_event_boundary(self):
        def data(events):return '\n'.join(json.dumps(e) for e in events)
        self.assertEqual(bridge.test_summary(data([{'Action':'pass','Package':'p'}]),0)['count'],0)
        self.assertEqual(bridge.test_summary(data([{'Action':'run','Test':bridge.TEST_NAME},{'Action':'fail','Test':bridge.TEST_NAME}]),1)['status'],'FAIL_NATIVE_ASSERTION')

    def test_native_replay_withdraw_restore_on_synthetic_go(self):
        root=self.exp()
        # Minimal local verifier accepts only the fixture. GitHub CI substitutes
        # existing independently qualified Go AST verifier from MathGraph.
        validator=self.root/'validate.go'
        validator.write_text('''package main
import ("encoding/json";"os";"strings")
func main(){s:="UNKNOWN";if len(os.Args)>=4&&os.Args[1]=="--"&&os.Args[2]!=""{s="ADMITTED_TEST_ONLY_CANDIDATE"};if len(os.Args)>=4&&!strings.HasSuffix(os.Args[2],".go"){s="UNKNOWN"};json.NewEncoder(os.Stdout).Encode(map[string]string{"status":s})}
''')
        # A local stub validator is not enough to warrant source-native admission.
        # We test the replay state-machine manually with that qualification caveat.
        receipt=bridge.cold_replay(self.store,root,self.repo,validator)
        self.assertEqual(receipt['status'],'WARRANTED_BOUNDED_COLD_NATIVE_REPLAY',receipt)
        self.assertEqual(receipt['arms']['withdrawn']['status'],'UNKNOWN_ZERO_OR_MULTIPLE_NAMED_TESTS')
        self.assertEqual(bridge.cold_replay(self.store,root,self.repo,validator,{root})['status'],'UNKNOWN_REVOKED_OBJECT')
        shutil.rmtree(self.store/'objects'/root)
        self.assertEqual(bridge.cold_replay(self.store,root,self.repo,validator)['status'],'UNKNOWN_CAPABILITY_WITHDRAWN')
        self.exp()
        self.assertEqual(bridge.cold_replay(self.store,root,self.repo,validator)['status'],'WARRANTED_BOUNDED_COLD_NATIVE_REPLAY')

if __name__=='__main__':unittest.main()
