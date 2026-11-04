import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {buildOmmAppCheckPreview} from './app-check.mjs';

const hash=s=>createHash('sha256').update(s).digest('hex');
const request={schema:'mathgraph.omm.request.v1',repository:'metalogiclabs/mathgraph',
  number:239,head_sha:'a'.repeat(40),base_sha:'b'.repeat(40),candidate_source_sha256:'c'.repeat(64),command:'check'};
const contract={schema:'mathgraph.omm.claim-contract.v1',repository:request.repository,number:request.number,
  head_sha:request.head_sha,base_sha:request.base_sha,reference_sha256:'d'.repeat(64),
  candidate_sha256:request.candidate_source_sha256,consumer_sha256:'e'.repeat(64),
  consumer_name:'Original.target',candidate_name:'Candidate.theorem',mathlib_git:'f'.repeat(40),lean_toolchain_sha256:'1'.repeat(64)};
const receipt={schema:'mathgraph.omm.native-receipt.v1',repository:request.repository,number:request.number,
  head_sha:request.head_sha,base_sha:request.base_sha,native:{execution_status:'EXECUTED',
    source_reference_sha256:contract.reference_sha256,candidate_sha256:contract.candidate_sha256,
    consumer_sha256:contract.consumer_sha256,consumer_name:contract.consumer_name,
    candidate_declaration_name:contract.candidate_name,mathlib_git:contract.mathlib_git,
    lean_toolchain_sha256:contract.lean_toolchain_sha256,candidate_source_build:'LEAN_ACCEPTED',
    original_target_status:'NATIVE_CONSUMER_ACCEPTED',candidate_axioms:['propext'],axioms:['propext'],
    trace:[{unit:'Candidate',exit_code:0},{unit:'Consumer',exit_code:0},{unit:'Audit',exit_code:0}]}};
function input(r=receipt){const contractBytes=JSON.stringify(contract),receiptBytes=JSON.stringify(r);return {
  request,contractBytes,receiptBytes,expectedContractSha256:hash(contractBytes),expectedReceiptSha256:hash(receiptBytes),
  expectedHeadSha:request.head_sha,runUrl:'https://github.com/metalogiclabs/mathgraph/actions/runs/41914046962'};}

test('OMM Check shares neutral GitHub App formatting and never means a mathematical warrant',()=>{
 const {payload,assessment}=buildOmmAppCheckPreview(input());
 assert.equal(assessment.original_target,'CONSUMER_ACCEPTED');
 assert.equal(payload.head_sha,request.head_sha);
 assert.equal(payload.conclusion,'neutral');
 assert.equal(payload.status,'completed');
 assert.match(payload.name,/MathGraph Check.*OMM/);
 assert.match(payload.output.summary,/Original.target consumer.*Accepted by native Lean replay/i);
 assert.match(payload.output.summary,/Human mathematical intent.*UNKNOWN/i);
 assert.match(payload.output.summary,/Independent evidence warrant.*UNKNOWN/i);
 assert.equal(payload.output.title.includes('success'),false);
});

test('strengthened premise reports bounded failure without converting it to unsound proof rejection',()=>{
 const r=structuredClone(receipt);r.native.trace=r.native.trace.slice(0,2);
 r.native.trace[1].exit_code=1;r.native.axioms=null;r.native.original_target_status='UNKNOWN';
 const {payload,assessment}=buildOmmAppCheckPreview(input(r));
 assert.equal(assessment.candidate_proof,'LEAN_COMPILED');
 assert.equal(assessment.original_target,'NOT_ESTABLISHED_IN_THIS_REPLAY');
 assert.equal(payload.conclusion,'neutral');
 assert.match(payload.output.summary,/NOT mathematical inequivalence/);
});

test('source staleness and falsified receipt keep an informational UNKNOWN, not a green Check',()=>{
 const unknown=buildOmmAppCheckPreview({...input(),expectedReceiptSha256:'0'.repeat(64)});
 assert.equal(unknown.assessment.status,'UNKNOWN');
 assert.equal(unknown.payload.conclusion,'neutral');
 assert.match(unknown.payload.output.summary,/Check incomplete/);
 assert.throws(()=>buildOmmAppCheckPreview({...input(),expectedHeadSha:'2'.repeat(40)}),/STALE_SOURCE_REFUSED/);
 assert.throws(()=>buildOmmAppCheckPreview({...input(),request:{...request,command:'fix'}}),/OMM_CHECK_ONLY/);
});
