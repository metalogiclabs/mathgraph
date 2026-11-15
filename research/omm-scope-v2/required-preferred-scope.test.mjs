import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {assessDeclaredScope as assess} from './required-preferred-scope.mjs';
const sha = value => createHash('sha256').update(value).digest('hex');

const currentSource = {
  // Synthetic IDs/bytes. These scenarios are inspired by the public Mathathon
  // texts, but do not replay or qualify any of their Lean declarations.
  repository: 'metalogiclabs/synthetic-omm-control',
  head_sha: 'd'.repeat(40),
  source_sha256: 'a'.repeat(64),
  source_path: 'fixtures/example.lean',
};

const requirements = (ids, preferred) => ({
  schema: 'mathgraph.omm.declared-scope-contract.research.v2',
  ...currentSource,
  requirement_ids: ids,
  ...(preferred === undefined ? {} : {preferred_requirement_ids: preferred}),
});
const target = (ids) => ({
  schema: 'mathgraph.omm.type-scope-annotation.research.v2',
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

test('a preferred deliverable stays separate from mandatory declared scope', () => {
  const req = requirements(['human-readable-exposition'], ['conceptual-rephrasing']);
  const result = call(req, target([]));
  assert.equal(result.status, 'PINNED_SCOPE_ANNOTATIONS_COMPARED');
  assert.equal(result.schema,'mathgraph.omm.declared-scope-assessment.research.v2');
  assert.equal(result.declared_scope, 'DECLARED_GAP');
  assert.deepEqual(result.uncovered_requirement_ids, ['human-readable-exposition']);
  assert.deepEqual(result.uncovered_preference_ids, ['conceptual-rephrasing']);
  assert.equal(result.preference_warrant, 'UNKNOWN');
  assert.equal(result.intent_fidelity, 'UNKNOWN');
  const narrow = call(requirements(['positive-density'], ['conceptual-rephrasing']),
    target(['positive-density']));
  assert.equal(narrow.declared_scope, 'NO_DECLARED_GAP');
  assert.deepEqual(narrow.uncovered_requirement_ids, []);
  assert.deepEqual(narrow.uncovered_preference_ids, ['conceptual-rephrasing']);
});

test('a claimed preferred scope may be annotated without certifying preference satisfaction', () => {
  const result = call(requirements(['positive-density'], ['conceptual-rephrasing']),
    target(['positive-density', 'conceptual-rephrasing']));
  assert.equal(result.status, 'PINNED_SCOPE_ANNOTATIONS_COMPARED');
  assert.equal(result.declared_scope, 'NO_DECLARED_GAP');
  assert.deepEqual(result.uncovered_preference_ids, []);
  assert.equal(result.preference_warrant, 'UNKNOWN');
  assert.equal(result.intent_fidelity, 'UNKNOWN');
});

test('malformed or overlapping required/preferred IDs fail closed', () => {
  for (const optional of [['conceptual-rephrasing', 'conceptual-rephrasing'],
    ['positive-density'], ['wrong ID'], null]) {
    const r = call(requirements(['positive-density'], optional), target(['positive-density']));
    assert.equal(r.status, 'UNKNOWN');
    assert.equal(r.declared_scope, 'UNKNOWN');
  }
});

test('unattested preference edits cannot reuse an earlier requirement digest', () => {
  const req = requirements(['positive-density'], ['conceptual-rephrasing']);
  const rec = target(['positive-density']);
  const r = assess({currentSource,
    contractBytes: JSON.stringify({...req, preferred_requirement_ids: ['must-prove-equality']}),
    expectedContractSha256: sha(JSON.stringify(req)),
    typeAnnotationBytes: JSON.stringify(rec),
    expectedTypeAnnotationSha256: sha(JSON.stringify(rec)),
  });
  assert.equal(r.status, 'UNKNOWN');
});
