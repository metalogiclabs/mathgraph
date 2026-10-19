#!/usr/bin/env python3
import json,hashlib,sys,pathlib
p=pathlib.Path(sys.argv[1]); y=pathlib.Path(sys.argv[2]);out=pathlib.Path(sys.argv[3])
a=json.loads(p.read_text());b=json.loads(y.read_text())
assert a['protocol']=='JPL_PKC_OPENSYSML_FULL_TEXT_V5'
assert a['upstream']=='nasa-jpl/PropertyKindCalculus@e0deb453e05ffa63297d9704ceb47d0855193824'
assert a['status_by_lane']=={'original/no_statement':'ACCEPT','original/false_statement':'ACCEPT','strict/no_statement':'ACCEPT','strict/false_statement':'REJECT','withdrawn/false_statement':'ACCEPT'}
assert a['no_kernel_proof_of_false'] and a['converter_retains_optional_claim'] and a['authentic_SysML_cli']
assert b['protocol']=='L4YAML_STYLE_REPAIR_VERIFY_V2' and b['expectation']=='original-red'
assert b['upstream']=='nasa-jpl/L4YAML@fdef03caf19e8862792034793da11020b39d6110'
assert b['native_correctness_checks']['distinct_dump_option_values'] is False
assert b['independent_checks']['qNone_is_null_in_both'] is False
assert b['independent_checks']['qStringNull_is_string_in_both'] is True
assert len(b['known_original_failures'])==10
rows=[('P1','positive',['pkc-decl','pkc-verifier']),('P2','negative',['pkc-decl','pkc-annotation','pkc-verifier']),('P3',None,['pkc-annotation']),('Y1',None,['yaml-oracle']),('Y2','negative',['yaml-dump','yaml-oracle','yaml-verifier']),('Y3',None,['yaml-source'])]
def evaluate(withdrawn=()):
 return {id:('UNKNOWN_WITHDRAWN' if set(deps)&set(withdrawn) else {'positive':'WARRANTED_BOUNDED','negative':'REJECTED_BOUNDED',None:'UNKNOWN'}[signal]) for id,signal,deps in rows}
baseline=evaluate();assert baseline=={'P1':'WARRANTED_BOUNDED','P2':'REJECTED_BOUNDED','P3':'UNKNOWN','Y1':'UNKNOWN','Y2':'REJECTED_BOUNDED','Y3':'UNKNOWN'}
tests={'M1':('pkc-decl',{'P1','P2'}),'M2':('pkc-annotation',{'P2','P3'}),'M3':('yaml-dump',{'Y2'}),'M4':('yaml-oracle',{'Y1','Y2'})}
results={}
for name,(withdraw,expected) in tests.items():
 after=evaluate([withdraw]);changes={k for k in baseline if baseline[k]!=after[k]}
 assert changes==expected
 assert all(after[k]=='UNKNOWN_WITHDRAWN' for k in changes)
 results[name]={'withdrawn':withdraw,'changed':sorted(changes),'lost_previously_decisive':sorted(k for k in changes if baseline[k]!='UNKNOWN'),'pass':True}
assert evaluate()==baseline
receipt={'protocol_commit':'9c8b427c679398fd80ea56d9a91a1627b2e96b6d','mode':'authenticated archived native verifier replay + modeled dependency withdrawal','new_native_sources_executed':False,'pkc_receipt_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'l4yaml_receipt_sha256':hashlib.sha256(y.read_bytes()).hexdigest(),'baseline':baseline,'tests':results,'M5':'UNKNOWN: requires native verifier re-execution after source revision restoration','cross_domain_semantic_acquisition':'UNKNOWN'}
out.write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n');print(json.dumps(receipt,sort_keys=True))
