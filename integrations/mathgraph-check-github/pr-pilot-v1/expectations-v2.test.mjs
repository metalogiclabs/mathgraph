import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {subject,receiptFor} from './expectations.test.mjs';
import {reviewedPlan,admitExpectations,LEADING_REFERENCE_IDENTITY} from './expectations.mjs';
import {admitLeanPlan} from '../lean-investigator-v1/contracts.mjs';
const context={verifier_sha:'a'.repeat(40),run_id:42,attempt:1};
const cohort=JSON.parse(readFileSync(new URL('../../../experiments/check-leading-redirection-v1/cohort.json',import.meta.url)));
function fixture(){
 const receipt=receiptFor(subject,context),good=calls=>({status:'OK',calls,exit:0});
 receipt.expectation_set='ledger-shell-v2';receipt.leading_reference={records:cohort.cases.slice(0,3).map(c=>({Obligation:c,Conclusion:{status:'SUPPORTED'},Dependencies:{...LEADING_REFERENCE_IDENTITY,bash_sha256:'b'.repeat(64)},Verification:{execution:good(c.expected_calls),repeat:good(c.expected_calls),controls:{positive:good([['guard.py']]),negative:good([])}}}))};
 return {subject:structuredClone(subject),plan:reviewedPlan(subject,undefined,'ledger-shell-v2'),receipt};
}
test('v2 retains both old probes and adds one exact three-case guard within hosted limit',()=>{
 const x=fixture();assert.equal(x.plan.tests.length,3);assert.equal(admitLeanPlan(x.plan).tests.length,3);
 assert.deepEqual(x.plan.tests.slice(0,2),reviewedPlan(subject).tests);
 const a=admitExpectations(x.subject,x.plan,x.receipt,context,undefined,'ledger-shell-v2');assert.equal(a.status,'ADMITTED');assert.equal(a.input_count,5);assert.equal(a.requirement_count,3);
});
test('old admission stays two-case and cannot silently authorize the new set',()=>{
 const x=fixture();assert.equal(reviewedPlan(subject).tests.length,2);
 assert.equal(admitExpectations(subject,reviewedPlan(subject),receiptFor(subject,context),context).status,'ADMITTED');
 assert.equal(admitExpectations(subject,x.plan,x.receipt,context).status,'UNKNOWN');
 assert.equal(admitExpectations(subject,reviewedPlan(subject),receiptFor(subject,context),context,undefined,'ledger-shell-v2').status,'UNKNOWN');
});
for(const [name,mutate]of [
 ['set version',x=>x.receipt.expectation_set='ledger-shell-v1'],
 ['omitted case',x=>x.receipt.leading_reference.records.pop()],
 ['missing reference',x=>delete x.receipt.leading_reference],
 ['weak expression',x=>x.plan.tests[2].expression='true'],
 ['wrong argv',x=>x.receipt.leading_reference.records[0].Verification.execution.calls=[]],
 ['runner',x=>x.receipt.leading_reference.records[0].Dependencies.runner_sha256='c'.repeat(64)],
 ['adapter',x=>x.receipt.leading_reference.records[0].Dependencies.adapter_sha256='c'.repeat(64)],
 ['cohort',x=>x.receipt.leading_reference.records[0].Dependencies.cohort_sha256='c'.repeat(64)],
 ['authority',x=>x.receipt.leading_reference.records[0].Obligation.authority.state='HYPOTHESIS'],
 ['authority reference',x=>x.receipt.leading_reference.records[0].Obligation.authority.reference='unreviewed'],
 ['repeat',x=>x.receipt.leading_reference.records[0].Verification.repeat.calls=[]],
 ['positive control',x=>x.receipt.leading_reference.records[0].Verification.controls.positive.calls=[]],
 ['context',x=>x.receipt.context.run_id=43],
 ['source',x=>x.subject.sha256='c'.repeat(64)]
])test('v2 '+name+' cannot authorize repair',()=>{const x=fixture();mutate(x);assert.equal(admitExpectations(x.subject,x.plan,x.receipt,context,undefined,'ledger-shell-v2').repair_eligible,false);});
