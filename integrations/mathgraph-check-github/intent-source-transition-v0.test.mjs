import test from 'node:test';
import assert from 'node:assert/strict';
import {qualifyIntentSourceTransition} from './intent-source-transition-v0.mjs';
import {SCHEMA,digestContract,auditIntent} from './intent-contract-v1.mjs';

const sha=x=>x.repeat(40),digest=x=>x.repeat(64);
const repository='metalogiclabs/mathgraph',pr=195,token='synthetic-token';

function fixture(head,base='a') {
 const contract={schema:SCHEMA,
  subject:{repository,pr,base_sha:sha(base),head_sha:sha(head)},
  claims:[{id:'safe',statement:'The pinned input has the expected behavior.',requires:['probe']}],
  probes:[{id:'probe',input_sha256:digest('1'),oracle_sha256:digest('2'),verifier_sha:sha('c')}]};
 const receipt={id:'qualified-'+head,probe_id:'probe',subject_sha:sha(head),
  contract_sha256:digestContract(contract),input_sha256:digest('1'),oracle_sha256:digest('2'),
  verifier_sha:sha('c'),result:'PASS',exit_code:0,log_sha256:digest('3'),witness_sha256:null};
 const authority={allowedRepositories:[repository],expectedHeadSha:sha(head),
  expectedContractSha256:digestContract(contract),authenticatedReceiptIds:[receipt.id],
  qualifiedVerifierShas:[sha('c')],qualifiedOracleShas:[digest('2')]};
 return {contract,receipts:[receipt],authority};
}

function api({heads=['b','b'],bases=['a','a'],check='success'}={}) {
 let read=0;
 const fetcher=async url=>{
  if(url.includes('/pulls/')){
   const i=Math.min(read++,heads.length-1);
   return {ok:true,json:async()=>({base:{sha:sha(bases[i]),repo:{full_name:repository}},
    head:{sha:sha(heads[i]),repo:{full_name:repository}}})};
  }
  assert.match(url,/\/commits\/b{40}\/check-runs/);
  return {ok:true,json:async()=>({total_count:1,check_runs:[{id:11,name:'trusted-ci',
   head_sha:sha('b'),status:check==='pending'?'in_progress':'completed',
   conclusion:check==='pending'?'success':check,started_at:'2026-10-29T00:00:00Z',
   app:{slug:'github-actions'}}]})};
 };
 return {fetcher,reads:()=>read};
}

const old=fixture('a'),fresh=fixture('b');
const invoke=({before=old,after=fresh,github=api(),
 trustedAuthorities={before:before.authority,after:after.authority}}={})=>
 qualifyIntentSourceTransition({repository,pr,token,before,after,
  trustedAuthorities,fetcher:github.fetcher});

function requalifyChangedContract(change){
 const changed=structuredClone(fresh);
 change(changed.contract);
 changed.receipts[0].contract_sha256=digestContract(changed.contract);
 changed.receipts[0].input_sha256=changed.contract.probes[0].input_sha256;
 changed.receipts[0].oracle_sha256=changed.contract.probes[0].oracle_sha256;
 changed.authority.expectedContractSha256=digestContract(changed.contract);
 changed.authority.qualifiedOracleShas=[changed.contract.probes[0].oracle_sha256];
 assert.equal(auditIntent(changed.contract,changed.receipts,changed.authority).status,'OBSERVED');
 return changed;
}

test('fresh B qualified probes and authenticated current B yield only a bounded observed transition',async()=>{
 const github=api();
 const out=await invoke({github});
 assert.equal(github.reads(),2);
 assert.equal(out.status,'OBSERVED');
 assert.equal(out.permission,'ADVISORY_ONLY');
 assert.equal(out.intent_verification,'NOT_ESTABLISHED');
 assert.equal(out.checked_scope,'DECLARED_PINNED_PROBES_ONLY');
 assert.equal(out.source.head_sha,sha('b'));
 assert.equal(out.transitions[0].to,'OBSERVED');
 assert.equal(out.transitions[0].reason,'RECHECKED_OR_WITHDRAWN');
});

test('an A receipt cannot requalify B, even with in-band true',async()=>{
 const after={...fresh,receipts:old.receipts,independent_requalification:true};
 const out=await invoke({after});
 assert.equal(out.status,'UNKNOWN');
 assert.equal(out.transitions[0].to,'UNKNOWN');
});

test('no host-authenticated B receipt cannot be promoted',async()=>{
 const after={...fresh,authority:{...fresh.authority,authenticatedReceiptIds:[]}};
 const out=await invoke({after});
 assert.equal(out.status,'UNKNOWN');
 assert.equal(out.transitions[0].to,'UNKNOWN');
});

test('in-band forged authority does not substitute for missing host authority',async()=>{
 const attacker={...fresh,independent_requalification:true,
  authority:{...fresh.authority,authenticatedReceiptIds:[fresh.receipts[0].id]}};
 const trustedAuthorities={before:old.authority,
  after:{...fresh.authority,authenticatedReceiptIds:[]}};
 const out=await invoke({after:attacker,trustedAuthorities});
 assert.equal(out.status,'UNKNOWN');
 assert.equal(out.transitions[0].to,'UNKNOWN');
});

test('changing the meaning of a named claim cannot inherit A intent without owner approval',async()=>{
 const after=requalifyChangedContract(c=>{
  c.claims[0].statement='A refund is approved for every order.';
 });
 const out=await invoke({after});
 assert.equal(out.status,'UNKNOWN');
 assert.equal(out.reason,'INTENT_BASIS_CHANGED_WITHOUT_OWNER_APPROVAL');
});

test('changing the oracle behavior cannot silently replace the original intent basis',async()=>{
 const after=requalifyChangedContract(c=>{
  c.probes[0].oracle_sha256=digest('f');
 });
 const out=await invoke({after});
 assert.equal(out.status,'UNKNOWN');
 assert.equal(out.reason,'INTENT_BASIS_CHANGED_WITHOUT_OWNER_APPROVAL');
});

test('wrong verifier and oracle authorities cannot requalify',async()=>{
 for(const field of ['qualifiedVerifierShas','qualifiedOracleShas']){
  const after={...fresh,authority:{...fresh.authority,[field]:[]}};
  const out=await invoke({after});
  assert.equal(out.status,'UNKNOWN');
 }
});

test('GitHub head mismatch rejects a fresh-looking but source-C bound contract',async()=>{
 const out=await invoke({after:fixture('c')});
 assert.equal(out.status,'UNKNOWN');
 assert.equal(out.reason,'AUDIT_SOURCE_NOT_CURRENT_GITHUB_PR');
});

test('GitHub base mismatch rejects an otherwise qualified B receipt',async()=>{
 const out=await invoke({after:fixture('b','d')});
 assert.equal(out.status,'UNKNOWN');
 assert.equal(out.reason,'AUDIT_SOURCE_NOT_CURRENT_GITHUB_PR');
});

test('pending same-head latest CI prevents fresh monitor promotion',async()=>{
 const out=await invoke({github:api({check:'pending'})});
 assert.equal(out.status,'UNKNOWN');
 assert.equal(out.reason,'EXACT_HEAD_CHECKS_NOT_OBSERVED');
});

test('head check failure is not confused with an intent counterexample',async()=>{
 const out=await invoke({github:api({check:'failure'})});
 assert.equal(out.status,'UNKNOWN');
 assert.equal(out.reason,'EXACT_HEAD_CHECKS_NOT_OBSERVED');
});

test('qualified B intent counterexample remains BLOCKED and carries its witness',async()=>{
 const after=structuredClone(fresh);
 after.receipts[0].result='COUNTEREXAMPLE';after.receipts[0].exit_code=1;
 after.receipts[0].witness_sha256=digest('f');
 assert.equal(auditIntent(after.contract,after.receipts,after.authority).status,'BLOCKED');
 const out=await invoke({after});
 assert.equal(out.status,'BLOCKED');
 assert.equal(out.transitions[0].to,'BLOCKED');
 assert.equal(out.permission,'ADVISORY_ONLY');
});

test('GitHub source B moving to C during readback cannot requalify B',async()=>{
 await assert.rejects(invoke({github:api({heads:['b','c']})}),
  /PR_SOURCE_MOVED_DURING_CHECKS/);
});

test('GitHub base changing during readback cannot requalify B',async()=>{
 await assert.rejects(invoke({github:api({bases:['a','c']})}),
  /PR_SOURCE_MOVED_DURING_CHECKS/);
});
