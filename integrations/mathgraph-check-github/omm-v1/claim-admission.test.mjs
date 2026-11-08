import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {assessOmmClaim} from './claim-admission.mjs';

const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const original = 'a'.repeat(64), candidate = 'b'.repeat(64), consumer = 'c'.repeat(64);
const head = 'd'.repeat(40), base = 'e'.repeat(40), mathlib = 'f'.repeat(40);
const toolchain = '9'.repeat(64);
const request = {schema: 'mathgraph.omm.request.v1', repository: 'metalogiclabs/mathgraph', number: 300,
  head_sha: head, base_sha: base, candidate_source_sha256: candidate, command: 'check'};
const contract = {schema: 'mathgraph.omm.claim-contract.v1', repository: request.repository,
  number: request.number, head_sha: head, base_sha: base,
  reference_sha256: original, candidate_sha256: candidate, consumer_sha256: consumer,
  consumer_name: 'MathGraphConsumer.original_target',
  candidate_name: 'Proposed.candidate',
  mathlib_git: mathlib, lean_toolchain_sha256: toolchain};
const native = {execution_status: 'EXECUTED', source_reference_sha256: original,
  candidate_sha256: candidate, consumer_sha256: consumer,
  consumer_name: contract.consumer_name, mathlib_git: mathlib,
  candidate_declaration_name: contract.candidate_name,
  lean_toolchain_sha256: toolchain, candidate_source_build: 'LEAN_ACCEPTED',
  original_target_status: 'NATIVE_CONSUMER_ACCEPTED', axioms: ['propext'],
  candidate_axioms: ['propext'],
  trace: [{unit: 'Candidate', exit_code: 0}, {unit: 'Consumer', exit_code: 0},
    {unit: 'Audit', exit_code: 0}]};
const receipt = {schema: 'mathgraph.omm.native-receipt.v1',
  repository: request.repository, number: request.number, head_sha: head, base_sha: base, native};
const args = (c=contract, r=receipt, req=request) => {
  const contractBytes = JSON.stringify(c), receiptBytes = JSON.stringify(r);
  return {request: req, contractBytes, expectedContractSha256: hash(contractBytes),
    receiptBytes, expectedReceiptSha256: hash(receiptBytes)};
};

test('native compilation and an original-target consumer are separate, bounded observations', () => {
  const result = assessOmmClaim(args());
  assert.equal(result.status, 'NATIVE_RECEIPT_BOUND');
  assert.equal(result.candidate_proof, 'LEAN_COMPILED');
  assert.equal(result.original_target, 'CONSUMER_ACCEPTED');
  assert.equal(result.formal_statement_relation, 'UNKNOWN');
  assert.equal(result.intent_fidelity, 'UNKNOWN');
  assert.equal(result.evidence_warrant, 'UNKNOWN');
  assert.equal(result.candidate_dependence, 'UNKNOWN');
  assert.equal(result.candidate_axiom_status, 'STANDARD_ONLY');
  assert.equal(result.repair_permission, 'DENIED');
  assert.equal(result.head_sha, head);
});

test('a compiling but weakened candidate does not inherit original-target acceptance', () => {
  const failed = structuredClone(receipt);
  failed.native.original_target_status = 'UNKNOWN';
  failed.native.axioms = null;
  failed.native.trace = [{unit:'Candidate',exit_code:0}, {unit:'Consumer',exit_code:1}];
  const result = assessOmmClaim(args(contract, failed));
  assert.equal(result.candidate_proof, 'LEAN_COMPILED');
  assert.equal(result.original_target, 'NOT_ESTABLISHED_IN_THIS_REPLAY');
  assert.equal(result.formal_statement_relation, 'UNKNOWN');
  assert.equal(result.intent_fidelity, 'UNKNOWN');
  assert.equal(result.repair_permission, 'DENIED');
});

test('stale GitHub head or changed source sha invalidates native admission', () => {
  for (const change of [{head_sha:'1'.repeat(40)}, {candidate_source_sha256:'2'.repeat(64)}]) {
    const result = assessOmmClaim(args(contract, receipt, {...request, ...change}));
    assert.equal(result.status, 'UNKNOWN');
    assert.equal(result.candidate_proof, 'UNKNOWN');
    assert.equal(result.original_target, 'UNKNOWN');
  }
});

test('no trusted contract or independently pinned artifact means UNKNOWN, even if payload says PASS', () => {
  const a = args();
  for (const patch of [
    {expectedContractSha256: '0'.repeat(64)},
    {expectedReceiptSha256: '0'.repeat(64)},
    {expectedContractSha256: null},
    {receiptBytes: '{not json'},
  ]) {
    const result = assessOmmClaim({...a, ...patch});
    assert.equal(result.status, 'UNKNOWN');
    assert.equal(result.evidence_warrant, 'UNKNOWN');
  }
});

test('native tool/environment errors never become Lean proof rejection or original-target failures', () => {
  const failed = structuredClone(receipt);
  failed.native.execution_status = 'ENVIRONMENT_UNAVAILABLE';
  failed.native.trace = [{unit:'Candidate',exit_code:null,execution_failed:true}];
  const result = assessOmmClaim(args(contract, failed));
  assert.equal(result.candidate_proof, 'UNKNOWN');
  assert.equal(result.original_target, 'UNKNOWN');
  assert.equal(result.status, 'UNKNOWN');
});

test('a clean consumer must have the expected separate axiom audit', () => {
  for (const change of [{trace:native.trace.slice(0,2)},
    {axioms:['sorryAx']}, {candidate_axioms:['uncheckedAx']},
    {consumer_name:'Other.consumer'}, {mathlib_git:'0'.repeat(40)}]) {
    const changed = structuredClone(receipt); Object.assign(changed.native, change);
    const result = assessOmmClaim(args(contract, changed));
    assert.notEqual(result.original_target, 'CONSUMER_ACCEPTED');
    assert.equal(result.evidence_warrant, 'UNKNOWN');
  }
});

test('a native consumer without a bound candidate theorem or candidate axiom audit cannot be promoted', () => {
  for (const change of [{candidate_declaration_name:'Imported.unrelated'},
    {candidate_axioms:null}, {candidate_axioms:['sorryAx']}]) {
    const changed = structuredClone(receipt); Object.assign(changed.native, change);
    const result = assessOmmClaim(args(contract, changed));
    assert.notEqual(result.original_target, 'CONSUMER_ACCEPTED');
    assert.equal(result.candidate_dependence, 'UNKNOWN');
  }
});

test('OMM method is read-only: fix commands cannot authorize model repair', () => {
  const result = assessOmmClaim(args(contract, receipt, {...request,command:'fix'}));
  assert.equal(result.status, 'UNKNOWN');
  assert.equal(result.repair_permission, 'DENIED');
});
