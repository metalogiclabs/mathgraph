import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {prepareP11Audit,assessP11Native} from './typed-p11.mjs';

const originalRequirementBytes=readFileSync(new URL('./P11.original.md',import.meta.url),'utf8');
const sourceBytes=readFileSync(new URL('./P11.source.lean',import.meta.url),'utf8');
const type=`CollatzPositiveDensity.exists_positive_density :
  ∃ c, 0 < c ∧ ∃ X₀, ∀ (X : ℕ), X₀ ≤ X → c * ↑X ≤ ↑(CollatzPositiveDensity.countBelow (523 / 50) X)`;
const nativeOutput=`P11.Audit.lean:30:8: warning: declaration uses \`sorry\`
MATHGRAPH_P11_TYPE_BEGIN
${type}
MATHGRAPH_P11_TYPE_END
MATHGRAPH_P11_AXIOMS_BEGIN
'CollatzPositiveDensity.exists_positive_density' depends on axioms: [propext, sorryAx, Classical.choice, Quot.sound]
MATHGRAPH_P11_AXIOMS_END
`;
const context={originalRequirementBytes,sourceBytes,nativeOutput,exitCode:0,
  mathlibGit:'56a005855ea17e0b0958f73ec801ae140b0a1679',
  toolchainDigest:'7289597a44543246c9227b8cae501767e095ce17f6d448b95fc4a8dc97268f6d'};

test('frozen native P11 probe prints the theorem type and its axioms',()=>{
  const audit=prepareP11Audit(sourceBytes);
  assert.ok(audit.startsWith(sourceBytes));
  assert.match(audit.slice(sourceBytes.length),/#check CollatzPositiveDensity\.exists_positive_density/);
  assert.match(audit.slice(sourceBytes.length),/#print axioms CollatzPositiveDensity\.exists_positive_density/);
  assert.doesNotMatch(audit.slice(sourceBytes.length),/#print CollatzPositiveDensity\.exists_positive_density\n/);
});

test('published P11 paper request is not fulfilled by an existential theorem type',()=>{
  const result=assessP11Native(context);
  assert.equal(result.status,'PINNED_NATIVE_TYPE_TEXT_OBSERVED');
  assert.equal(result.original_scope.schema,'mathgraph.omm.declared-scope-assessment.research.v2');
  assert.equal(result.original_requirement_source.path,'problems_original/011-mazurs-collatz-paper.md');
  assert.equal(result.original_requirement_source.sha256,
    '77f73762bd92303e43a2af8a28c216c3bc245a6d4178a815641bd374ac2193d6');
  assert.deepEqual(result.original_scope.uncovered_requirement_ids,['human-readable-exposition']);
  assert.equal(result.original_scope.declared_scope,'DECLARED_GAP');
  assert.equal(result.narrowed_scope.declared_scope,'NO_DECLARED_GAP');
  assert.equal(result.proof_status,'NOT_ESTABLISHED_SORRY');
  assert.equal(result.type_sha256,createHash('sha256').update(type).digest('hex'));
  assert.equal(result.type_sha256,'2c4e2b2a362f466c184d2214192ee4d76bc510fb2804012f8078293747682e58');
  assert.equal(result.intent_fidelity,'UNKNOWN');
  assert.equal(result.evidence_warrant,'UNKNOWN');
});

test('preferred conceptual restatement is not misclassified as a mandatory unmet obligation',()=>{
  const result=assessP11Native(context);
  assert.deepEqual(result.original_scope.uncovered_requirement_ids,['human-readable-exposition']);
  assert.deepEqual(result.original_scope.uncovered_preference_ids,['conceptual-rephrasing']);
  assert.deepEqual(result.preference_ids,['conceptual-rephrasing']);
  assert.equal(result.preference_warrant,'UNKNOWN');
  assert.equal(result.scope_annotation_authority,'CURATOR_LABELS_ONLY');
});

test('the original source cannot be omitted or edited while retaining a gap claim',()=>{
  for(const original of [undefined,'',sourceBytes,
    originalRequirementBytes.replace('Preferably,','Required:'),
    originalRequirementBytes.replace('human-readable paper','Lean theorem')]){
    const r=assessP11Native({...context,originalRequirementBytes:original});
    assert.equal(r.status,'UNKNOWN');
    assert.equal(r.original_scope,undefined);
    assert.equal(r.intent_fidelity,'UNKNOWN');
  }
});

test('the Lean source cannot be altered while retaining a native type receipt',()=>{
  const changed=sourceBytes.replace('without the explicit values','with the explicit values');
  assert.notEqual(changed,sourceBytes);
  assert.equal(assessP11Native({...context,sourceBytes:changed}).status,'UNKNOWN');
  assert.throws(()=>prepareP11Audit(changed),/SOURCE_BYTES_CHANGED/);
});

test('proof body is not type-only evidence',()=>{
  const changed=nativeOutput.replace(type,type+' := by sorry');
  assert.equal(assessP11Native({...context,nativeOutput:changed}).status,'UNKNOWN');
});

test('changed theorem type and malformed marker sequences fail closed',()=>{
  for(const output of ['',nativeOutput+nativeOutput,
    nativeOutput.replace('∃ c, 0 < c','∀ c, 0 < c'),
    nativeOutput.replace('MATHGRAPH_P11_TYPE_END','')]){
    assert.equal(assessP11Native({...context,nativeOutput:output}).status,'UNKNOWN');
  }
});

test('toolchain, Mathlib, and process failure fail closed',()=>{
  for(const changed of [{exitCode:1},{mathlibGit:'a'.repeat(40)},
    {toolchainDigest:'b'.repeat(64)}]){
    assert.equal(assessP11Native({...context,...changed}).status,'UNKNOWN');
  }
});

test('absence of sorry axiom cannot be called a proved theorem',()=>{
  const changed=nativeOutput.replace('sorryAx','propext');
  assert.equal(assessP11Native({...context,nativeOutput:changed}).proof_status,'UNKNOWN');
});
