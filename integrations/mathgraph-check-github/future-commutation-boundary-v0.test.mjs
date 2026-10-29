import test from 'node:test';
import assert from 'node:assert/strict';
import {
  auditIntent, digestContract, SCHEMA,
} from './intent-contract-v1.mjs';
import {
  monitor,
} from './check-resolve-monitor-v1.mjs';
import {
  compareSnapshots,
} from './authenticated-cycle-v1.mjs';

const sha = x => x.repeat(40);
const digest = x => x.repeat(64);
const repo = 'metalogiclabs/future-contract-fixture';

function qualifiedAt(head) {
  const contract = {
    schema: SCHEMA,
    subject: {repository: repo, pr: 7, base_sha: sha('a'), head_sha: sha(head)},
    claims: [{id: 'safe', statement: 'A tested function returns the intended value.', requires: ['probe']}],
    probes: [{id: 'probe', input_sha256: digest('1'), oracle_sha256: digest('2'), verifier_sha: sha('c')}],
  };
  const receipt = {
    id: 'receipt-' + head, probe_id: 'probe', subject_sha: sha(head),
    contract_sha256: digestContract(contract), input_sha256: digest('1'),
    oracle_sha256: digest('2'), verifier_sha: sha('c'), result: 'PASS',
    exit_code: 0, log_sha256: digest('3'), witness_sha256: null,
  };
  const authority = {
    allowedRepositories: [repo], expectedHeadSha: sha(head),
    expectedContractSha256: digestContract(contract),
    authenticatedReceiptIds: [receipt.id], qualifiedVerifierShas: [sha('c')],
    qualifiedOracleShas: [digest('2')],
  };
  return {contract, receipt, authority};
}

const a = qualifiedAt('a');
const b = qualifiedAt('b');

test('a genuinely verified old exact head is only boundedly observed', () => {
  const original = auditIntent(a.contract, [a.receipt], a.authority);
  assert.equal(original.status, 'OBSERVED');
  assert.equal(original.intent_verification, 'NOT_ESTABLISHED');
});

test('new head cannot reuse old exact-source receipt', () => {
  const original = auditIntent(a.contract, [a.receipt], a.authority);
  const stale = auditIntent(b.contract, [a.receipt], b.authority);
  assert.equal(stale.status, 'UNKNOWN');
  assert.equal(monitor(original, stale).transitions[0].to, 'UNKNOWN');
});

test('fresh independent receipt is OBSERVED at audit plane yet UNKNOWN at monitor without bridging attestation', () => {
  const original = auditIntent(a.contract, [a.receipt], a.authority);
  const fresh = auditIntent(b.contract, [b.receipt], b.authority);
  assert.equal(fresh.status, 'OBSERVED');
  assert.equal(monitor(original, fresh).transitions[0].to, 'UNKNOWN');
});

test('caller-supplied unbound requalification bit promotes a claimed new result', () => {
  const original = auditIntent(a.contract, [a.receipt], a.authority);
  const fresh = auditIntent(b.contract, [b.receipt], b.authority);
  assert.equal(Object.hasOwn(fresh, 'independent_requalification'), false);
  const externallyAsserted = monitor(original, {...fresh, independent_requalification: true});
  assert.equal(externallyAsserted.transitions[0].to, 'OBSERVED');
  assert.equal(externallyAsserted.permission, 'ADVISORY_ONLY');
});

test('false in-band requalification bit cannot override an audit UNKNOWN', () => {
  const original = auditIntent(a.contract, [a.receipt], a.authority);
  const stale = auditIntent(b.contract, [a.receipt], b.authority);
  const outcome = monitor(original, {...stale, independent_requalification: true});
  assert.equal(outcome.transitions[0].to, 'UNKNOWN');
});

test('raw fabricated report can impersonate monitor transition without a trusted reporter boundary', () => {
  const original = auditIntent(a.contract, [a.receipt], a.authority);
  const fresh = auditIntent(b.contract, [b.receipt], b.authority);
  const counterfeit = {...fresh, results: [{...fresh.results[0], status: 'OBSERVED'}],
    independent_requalification: true, contract_sha256: digest('f')};
  assert.equal(monitor(original, counterfeit).transitions[0].to, 'OBSERVED');
  // A pure monitor cannot authenticate this untrusted packet. Do not expose it as a warrant.
});

test('authenticated-cycle facade strips a purported requalification bit', () => {
  const original = auditIntent(a.contract, [a.receipt], a.authority);
  const fresh = auditIntent(b.contract, [b.receipt], b.authority);
  const output = compareSnapshots({result: original},
    {result: {...fresh, independent_requalification: true}});
  assert.equal(output.transitions[0].to, 'UNKNOWN');
});
