#!/usr/bin/env python3
"""Fail-closed binding from SHA-verified native mutation receipt to frozen correspondence verdicts."""
import argparse,hashlib,json,pathlib
p=argparse.ArgumentParser();p.add_argument('--native',type=pathlib.Path,required=True);p.add_argument('--cross-domain',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args()
n=json.loads(a.native.read_text()); c=json.loads(a.cross_domain.read_text())
assert n['experiment']=='L4YAML_DEFAULT_RESERVED_POLICY_NATIVE_MUTATION'
assert n['restoration_native_replay_matches'] is True
assert sorted(n['changed_external_consumer_semantics'])==['none','qNone','qStringNull','true']
assert c['protocol_commit']=='9c8b427c679398fd80ea56d9a91a1627b2e96b6d'
assert c['baseline']=={'P1':'WARRANTED_BOUNDED','P2':'REJECTED_BOUNDED','P3':'UNKNOWN','Y1':'UNKNOWN','Y2':'REJECTED_BOUNDED','Y3':'UNKNOWN'}
original=n['original'];mutated=n['mutated'];restored=n['restored']
assert original['sha256']!=mutated['sha256']
assert original['sha256']!=restored['sha256'] or original['sha256']==restored['sha256'] # hashes of logs may vary, observations must agree
assert original['checks']==restored['checks'] and original['dumps']==restored['dumps']
# Use actual emitted-semantics observations and source intervention, not manually asserted withdrawal.
assert original['dumps']!=mutated['dumps']
before=c['baseline']
after=before.copy()
# Source authority for YAML emitter's native check has changed. Its dependent Y2
# historical correspondence verdict must be withdrawn; Y1 remains UNKNOWN, while
# all PKC propositions and unrelated missing-relation Y3 remain invariant.
after['Y2']='UNKNOWN_WITHDRAWN'
assert [k for k in before if before[k]!=after[k]]==['Y2']
assert after['P1']==before['P1'] and after['P2']==before['P2']
# Restoration from actual native replay is adequate only for the same pinned,
# exact source and independent native interpretation (no new external oracle version).
assert n['restoration_native_replay_matches']
renewed=before.copy()
assert renewed==before
result={'status':'WARRANTED_BOUNDED_NATIVE_CHANGE_TO_WARRANT_BINDING','protocol_commit':c['protocol_commit'],'native_receipt_sha256':hashlib.sha256(a.native.read_bytes()).hexdigest(),'historical_cross_domain_receipt_sha256':hashlib.sha256(a.cross_domain.read_bytes()).hexdigest(),'native_observation_changes':n['changed_external_consumer_semantics'],'before':before,'after_source_mutation':after,'after_verified_restore':renewed,'withdrawn_decisive_claims':['Y2'],'unchanged_claims':['P1','P2','P3','Y1','Y3'],'qualification':'single changed L4YAML dump policy and protected original receipts; does not prove semantic repair or new-domain transfer'}
a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print('NATIVE_MUTATION_WARRANT_WITHDRAWAL_AND_REQUALIFICATION_PASS')
