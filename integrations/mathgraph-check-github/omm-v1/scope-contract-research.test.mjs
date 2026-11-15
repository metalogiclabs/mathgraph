import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {assessDeclaredScope as assess} from './scope-contract-research.mjs';
const sha = value => createHash('sha256').update(value).digest('hex');

const currentSource = {
  // Synthetic IDs/bytes. These scenarios are inspired by the public Mathathon
  // texts, but do not replay or qualify any of their Lean declarations.
  repository: 'metalogiclabs/synthetic-omm-control',
  head_sha: 'd'.repeat(40),
  source_sha256: 'a'.repeat(64),
  source_path: 'fixtures/example.lean',
};

const requirements = (ids) => ({
  schema: 'mathgraph.omm.declared-scope-contract.research.v1',
  ...currentSource,
  requirement_ids: ids,
});
const target = (ids) => ({
  schema: 'mathgraph.omm.type-scope-annotation.research.v1',
  ...currentSource,
  declaration: 'Mathathon.example',
  type_sha256: 'b'.repeat(64),
  attested_scope_ids: ids,
});
const call = (req, typeReceipt, source=currentSource) => {
  const contractBytes = JSON.stringify(req);
  const typeAnnotationBytes = typeReceipt === null ? null : JSON.stringify(typeReceipt);
  return assess({
    currentSource: source,
    contractBytes,
    expectedContractSha256: sha(contractBytes),
    typeAnnotationBytes,
    expectedTypeAnnotationSha256: typeAnnotationBytes === null ? null : sha(typeAnnotationBytes),
  });
};

test('P127-shaped: equality-only target leaves source-requested bijection uncovered', () => {
  const result = call(requirements(['count-equality', 'natural-bijection']), target(['count-equality']));
  assert.equal(result.status, 'PINNED_SCOPE_ANNOTATIONS_COMPARED');
  assert.equal(result.declared_scope, 'DECLARED_GAP');
  assert.deepEqual(result.uncovered_requirement_ids, ['natural-bijection']);
  assert.equal(result.intent_fidelity, 'UNKNOWN');
  assert.equal(result.proof_status, 'UNKNOWN');
});

test('P127-shaped: a separately pinned narrower request no longer declares the bijection gap', () => {
  const result = call(requirements(['count-equality']), target(['count-equality']));
  assert.equal(result.declared_scope, 'NO_DECLARED_GAP');
  assert.deepEqual(result.uncovered_requirement_ids, []);
  assert.equal(result.intent_fidelity, 'UNKNOWN');
});

test('P11-shaped: existential density does not attest explicit c or cutoff', () => {
  const actual = call(requirements(['positive-density', 'explicit-c', 'explicit-cutoff']),
    target(['positive-density']));
  assert.equal(actual.declared_scope, 'DECLARED_GAP');
  assert.deepEqual(actual.uncovered_requirement_ids, ['explicit-c', 'explicit-cutoff']);
  const narrowed = call(requirements(['positive-density']), target(['positive-density']));
  assert.equal(narrowed.declared_scope, 'NO_DECLARED_GAP');
});

test('P123-shaped: a high-level result match is not a proof or intent certificate', () => {
  const result = call(requirements(['schur-five-160']), target(['schur-five-160']));
  assert.equal(result.declared_scope, 'NO_DECLARED_GAP');
  assert.equal(result.intent_fidelity, 'UNKNOWN');
  assert.equal(result.proof_status, 'UNKNOWN');
});

test('missing type annotation is UNKNOWN, not a proven mismatch', () => {
  const result = call(requirements(['count-equality']), null);
  assert.equal(result.status, 'UNKNOWN');
  assert.equal(result.declared_scope, 'UNKNOWN');
});

test('source movement or comment-only edits invalidate an old receipt', () => {
  const req = requirements(['count-equality']);
  const rec = target(['count-equality']);
  for (const source of [
    {...currentSource, head_sha: 'c'.repeat(40)},
    {...currentSource, source_sha256: sha('same theorem; edited comment')},
    {...currentSource, source_path: 'fixtures/shadowed.lean'},
  ]) {
    const result = call(req, rec, source);
    assert.equal(result.status, 'UNKNOWN');
    assert.equal(result.declared_scope, 'UNKNOWN');
  }
});

test('changed type annotations with old externally held pin are not admitted', () => {
  const req = requirements(['natural-bijection']);
  const rec = target(['count-equality']);
  const args = {
    currentSource,
    contractBytes: JSON.stringify(req),
    expectedContractSha256: sha(JSON.stringify(req)),
    typeAnnotationBytes: JSON.stringify({...rec, attested_scope_ids: ['natural-bijection']}),
    expectedTypeAnnotationSha256: sha(JSON.stringify(rec)),
  };
  const result = assess(args);
  assert.equal(result.status, 'UNKNOWN');
  assert.equal(result.declared_scope, 'UNKNOWN');
});

test('duplicate or ill-formed requirement IDs fail closed', () => {
  for (const ids of [['count-equality', 'count-equality'], ['count equality'], []]) {
    const result = call(requirements(ids), target(['count-equality']));
    assert.equal(result.status, 'UNKNOWN');
  }
});

test('ambiguous or traversing source paths fail closed', () => {
  const req = requirements(['count-equality']);
  const rec = target(['count-equality']);
  for (const source_path of ['../example.lean', '/fixtures/example.lean', 'fixtures//example.lean']) {
    assert.equal(call({...req, source_path}, {...rec, source_path},
      {...currentSource, source_path}).status, 'UNKNOWN');
  }
});

test('a fully claimed type scope still cannot be promoted to human-intent verified', () => {
  const result = call(requirements(['a', 'b']), target(['a', 'b']));
  assert.equal(result.declared_scope, 'NO_DECLARED_GAP');
  assert.equal(result.intent_fidelity, 'UNKNOWN');
  assert.equal(result.proof_status, 'UNKNOWN');
});
