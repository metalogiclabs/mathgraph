import test from 'node:test';
import assert from 'node:assert/strict';
import {formatOmmClaimReport,ommClaimView} from './report.mjs';

const request = {repository:'metalogiclabs/mathgraph',number:300,command:'check',head_sha:'a'.repeat(40),base_sha:'b'.repeat(40)};
const receipt = {status:'NATIVE_RECEIPT_BOUND',head_sha:request.head_sha,base_sha:request.base_sha,candidate_proof:'LEAN_COMPILED',
  original_target:'NOT_ESTABLISHED_IN_THIS_REPLAY',formal_statement_relation:'UNKNOWN',
  intent_fidelity:'UNKNOWN',evidence_warrant:'UNKNOWN',candidate_dependence:'UNKNOWN',candidate_axiom_status:'STANDARD_ONLY',repair_permission:'DENIED',
  reference_sha256:'c'.repeat(64),candidate_sha256:'d'.repeat(64),consumer_sha256:'e'.repeat(64),
  contract_sha256:'f'.repeat(64),native_receipt_sha256:'1'.repeat(64)};
const url='https://github.com/metalogiclabs/mathgraph/actions/runs/123';

test('accepted Lean proof and rejected original target appear as distinct scoped observations',()=>{
  const report=formatOmmClaimReport(receipt,request,url);
  assert.match(report,/Lean candidate.*Compiled/i);
  assert.match(report,/original.target.*not established in this replay/i);
  assert.match(report,/Formal.statement.*UNKNOWN/i);
  assert.match(report,/Human.*intent.*UNKNOWN/i);
  assert.match(report,/Candidate axioms.*Standard only/i);
  assert.match(report,/Candidate proof necessity.*UNKNOWN/i);
  assert.match(report,/NOT.*mathematical inequivalence/i);
  assert.match(report,/No automatic repair/i);
  assert.match(report,/metalogiclabs\/mathgraph#300/);
  assert.match(report,/c{64}/);
  assert.match(report,/1{64}/);
});

test('native consumer accepted never implies the paper meaning is verified',()=>{
  const v=ommClaimView({...receipt,original_target:'CONSUMER_ACCEPTED'},request);
  assert.match(v.title,/original.target consumer accepted/i);
  assert.match(v.scope,/intent.*UNKNOWN/i);
  assert.equal(v.fix.available,false);
});

test('missing evidence yields neutral UNKNOWN without a green headline or repair action',()=>{
  const assessment={status:'UNKNOWN',reason:'TRUSTED_CLAIM_CONTRACT_MISSING_OR_SOURCE_CHANGED',
    candidate_proof:'UNKNOWN',original_target:'UNKNOWN',intent_fidelity:'UNKNOWN',
    formal_statement_relation:'UNKNOWN',evidence_warrant:'UNKNOWN'};
  const report=formatOmmClaimReport(assessment,request,url);
  assert.match(report,/Check incomplete/);
  assert.doesNotMatch(report,/Original.target consumer accepted/);
  assert.doesNotMatch(report,/use .*fix/i);
  assert.match(report,/current revision/i);
});

test('report fails closed on unsafe repository identities and artifact URLs',()=>{
  assert.throws(()=>formatOmmClaimReport(receipt,{...request,repository:'bad/owner\n@everyone'},url));
  assert.throws(()=>formatOmmClaimReport(receipt,request,'javascript:alert(1)'));
});
