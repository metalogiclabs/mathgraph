import test from 'node:test';
import assert from 'node:assert/strict';
import {auditIntent,digestContract,renderIntentReport,SCHEMA} from './intent-contract-v1.mjs';
import {resolve,monitor} from './check-resolve-monitor-v1.mjs';
const h=x=>x.repeat(64),g=x=>x.repeat(40);
function setup(){
 const contract={schema:SCHEMA,subject:{repository:'metalogiclabs/demo',pr:7,base_sha:g('a'),head_sha:g('b')},
 claims:[{id:'refunds',statement:'Refunding an unavailable order returns a typed denial.',requires:['refund-case']}],
 probes:[{id:'refund-case',input_sha256:h('1'),oracle_sha256:h('2'),verifier_sha:g('c')}]};
 const sha=digestContract(contract);
 const r={id:'receipt-1',probe_id:'refund-case',subject_sha:g('b'),contract_sha256:sha,
  input_sha256:h('1'),oracle_sha256:h('2'),verifier_sha:g('c'),
  result:'PASS',exit_code:0,log_sha256:h('3'),witness_sha256:null};
 const authority={allowedRepositories:['metalogiclabs/demo'],expectedHeadSha:g('b'),
  expectedContractSha256:sha,authenticatedReceiptIds:['receipt-1'],
  qualifiedVerifierShas:[g('c')],qualifiedOracleShas:[h('2')]};
 return {contract,r,authority};
}
test('pinned probe success never establishes broad intent',()=>{
 const {contract,r,authority}=setup();const x=auditIntent(contract,[r],authority);
 assert.equal(x.status,'OBSERVED');assert.equal(x.results[0].status,'OBSERVED');
 assert.equal(x.intent_verification,'NOT_ESTABLISHED');assert.equal(x.current_applicability,'UNKNOWN');
 assert.equal(x.permission,'ADVISORY_ONLY');assert.equal(x.checked_scope,'DECLARED_PINNED_PROBES_ONLY');
});
test('CI success and in-band authenticated bit cannot qualify evidence',()=>{
 const {contract,r,authority}=setup();r.authenticated=true;
 assert.equal(auditIntent(contract,[r],authority).reason,'INVALID_RECEIPT_SET');
 delete r.authenticated;authority.authenticatedReceiptIds=[];
 assert.equal(auditIntent(contract,[r],authority).results[0].status,'UNKNOWN');
 authority.authenticatedReceiptIds=['receipt-1'];authority.qualifiedOracleShas=[];
 assert.equal(auditIntent(contract,[r],authority).results[0].status,'UNKNOWN');
});
test('qualified counterexample is bounded, carries witness',()=>{
 const {contract,r,authority}=setup();r.result='COUNTEREXAMPLE';r.exit_code=1;r.witness_sha256=h('d');
 const x=auditIntent(contract,[r],authority);
 assert.equal(x.status,'BLOCKED');assert.equal(x.results[0].probes[0].witness_sha256,h('d'));
 assert.equal(x.intent_verification,'NOT_ESTABLISHED');
 assert.equal(x.next_actions[0].action,'INSPECT_QUALIFIED_WITNESS');
});
test('panic timeout missing witness and duplicate probe receipts are UNKNOWN',()=>{
 const {contract,r,authority}=setup();
 for(const exit_code of [101,124,137]){
  r.result='COUNTEREXAMPLE';r.exit_code=exit_code;r.witness_sha256=h('d');
  assert.equal(auditIntent(contract,[r],authority).status,'UNKNOWN');
 }
 r.exit_code=1;r.witness_sha256=null;
 assert.equal(auditIntent(contract,[r],authority).status,'UNKNOWN');
 r.result='PASS';r.exit_code=0;
 const duplicate={...r,id:'receipt-2'};
 assert.equal(auditIntent(contract,[r,duplicate],authority).status,'UNKNOWN');
});
test('changed source, changed intent or untrusted verifier cannot carry old warrant',()=>{
 const x=setup();x.contract.subject.head_sha=g('e');
 assert.equal(auditIntent(x.contract,[x.r],x.authority).reason,'SOURCE_OR_CONTRACT_UNBOUND');
 const y=setup();y.authority.qualifiedVerifierShas=[];
 assert.equal(auditIntent(y.contract,[y.r],y.authority).status,'UNKNOWN');
 const z=setup();z.contract.claims[0].statement='Pay anyone immediately';
 assert.equal(auditIntent(z.contract,[z.r],z.authority).reason,'SOURCE_OR_CONTRACT_UNBOUND');
});
test('invalid universe, duplicate IDs, unauthorized source fail closed',()=>{
 const x=setup();x.contract.claims[0].requires=['surprise'];
 assert.equal(auditIntent(x.contract,[x.r],x.authority).reason,'UNKNOWN_REQUIRED_PROBE');
 const y=setup();y.authority.allowedRepositories=[];
 assert.equal(auditIntent(y.contract,[y.r],y.authority).reason,'REPOSITORY_NOT_AUTHORIZED');
 const z=setup();z.contract.probes.push({...z.contract.probes[0]});
 assert.equal(auditIntent(z.contract,[z.r],z.authority).reason,'DUPLICATE_ID');
});
test('existing Resolve and Monitor never invent authority',()=>{
 const a=setup(),before=auditIntent(a.contract,[a.r],a.authority);
 assert.deepEqual(resolve(before,{refunds:[{id:'check',cost:2,allowed:true,source_authoritative:true}]}),[]);
 const b=setup();b.r.result='ERROR';b.r.exit_code=101;
 const after=auditIntent(b.contract,[b.r],b.authority);
 const next=resolve(after,{refunds:[{id:'rerun',cost:3,allowed:true,source_authoritative:true}]});
 assert.equal(next[0].next.experiment,'rerun');assert.equal(next[0].next.kind,'PROPOSAL_NOT_EXECUTED');
 const transition=monitor(before,{...after,subject:{...after.subject,head_sha:g('f')}});
 assert.equal(transition.transitions[0].to,'UNKNOWN');assert.equal(transition.permission,'ADVISORY_ONLY');
});
test('human report never becomes a proof badge or injects markup',()=>{
 const a=setup();a.contract.claims[0].statement='<script>x</script>';
 a.authority.expectedContractSha256=digestContract(a.contract);a.r.contract_sha256=a.authority.expectedContractSha256;
 const html=renderIntentReport(auditIntent(a.contract,[a.r],a.authority));
 assert.match(html,/Intent fidelity: NOT ESTABLISHED/);
 assert.match(html,/No merge authorization/);
 assert.doesNotMatch(html,/<script>/);
});
