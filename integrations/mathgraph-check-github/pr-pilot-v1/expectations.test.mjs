import test from 'node:test';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';
import {expectationProfileFor,expectationSubject,reviewedPlan,admitExpectations,REFERENCE_IDENTITY} from './expectations.mjs';
const context={verifier_sha:'a'.repeat(40),run_id:42,attempt:1};
export const subject={repository:'metalogiclabs/L4YAML',head_sha:'fba155bf31918f9b03394ae9bfb8cd17c91ecfb8',path:'Scripts/Ledger.lean',sha256:'2e682e47ad98d581f7b075dfb880934ff89a3e3e287ac654d877cf1dee53ced4',cli_sha256:'64bb20331484ef711b6a752af1770959164c82308fd9ae79fbf954678ebbdbcf',toolchain:'leanprover/lean4:v4.35.0'};
export function receiptFor(s=subject,c=context){
 const observation=calls=>({status:'OK',calls,exit:0});
 const record=(id,command,calls)=>({Obligation:{id,command,expected_calls:calls,authority:{state:'DECLARED'}},Conclusion:{status:'SUPPORTED'},Dependencies:{...REFERENCE_IDENTITY,bash_sha256:'b'.repeat(64)},Verification:{execution:observation(calls),repeat:observation(calls),controls:{positive:observation([['guard.py']]),negative:observation([])}}});
 return structuredClone({schema:'mathgraph.expectations.reference.v1',context:c,subject:s,reference:{records:[record('attached_redirect','python3 -c 1>out',[['-c']]),record('argument_keyword','echo if python3 scripts/a.py > /dev/null',[])]}});
}
test('only qualified Ledger revisions select reviewed expectations',()=>{const r={repository:subject.repository,head_sha:subject.head_sha,profile:{mode:'OWNED_FORK_PR_PILOT'}};assert.equal(expectationProfileFor(r),'ledger-shell-v1');assert.equal(expectationProfileFor({...r,head_sha:'0'.repeat(40)}),null);assert.equal(expectationProfileFor({...r,profile:{mode:'OWNED_FORK_CLI_PARITY'}}),null);});
test('source subject hashes actual bytes rather than declared digest',()=>{const s=expectationSubject({...subject,source:'changed',cli_source:'cli',source_sha256:subject.sha256});assert.equal(s.sha256,createHash('sha256').update('changed').digest('hex'));assert.equal(reviewedPlan(s),null);});
test('fresh source/reference binding admits exactly the two reviewed targets',()=>{const plan=reviewedPlan(subject);assert.equal(plan.tests.length,2);const a=admitExpectations(subject,plan,receiptFor(),context);assert.equal(a.status,'ADMITTED');assert.equal(a.repair_eligible,true);assert.deepEqual(a.probes.map(p=>p.status),['ADMITTED','ADMITTED']);});
for(const [name,mutate]of[
 ['head',x=>x.subject.head_sha='f'.repeat(40)],['source',x=>x.subject.sha256='f'.repeat(64)],['CLI',x=>x.subject.cli_sha256='f'.repeat(64)],['toolchain',x=>x.subject.toolchain='other'],
 ['context',x=>x.receipt.context.run_id=99],['receipt source',x=>x.receipt.subject.sha256='f'.repeat(64)],['runner',x=>x.receipt.reference.records[0].Dependencies.runner_sha256='f'.repeat(64)],
 ['cohort',x=>x.receipt.reference.records[0].Dependencies.cohort_sha256='f'.repeat(64)],['oracle calls',x=>x.receipt.reference.records[0].Verification.execution.calls=[['-c','1']]],
 ['repeat',x=>x.receipt.reference.records[0].Verification.repeat.calls=[]],['control',x=>x.receipt.reference.records[0].Verification.controls.positive.calls=[]],
 ['missing reference',x=>x.receipt=null],['True expression',x=>x.plan.tests[0].expression='true'],['omitted positive control',x=>x.plan.tests.shift()]
])test(name+' cannot authorize repair',()=>{const x={subject:structuredClone(subject),plan:reviewedPlan(subject),receipt:receiptFor()};mutate(x);const a=admitExpectations(x.subject,x.plan,x.receipt,context);assert.equal(a.repair_eligible,false);assert.equal(a.status,'UNKNOWN');});
test('known wrong expected value is rejected while arbitrary expressions stay unknown',()=>{const p=reviewedPlan(subject);p.tests[0].expression='pyCallsOfLine "python3 -c 1>out" == [.inline "python3 -c 1"]';const a=admitExpectations(subject,p,receiptFor(),context);assert.equal(a.probes[0].status,'REJECTED');assert.equal(a.repair_eligible,false);});
