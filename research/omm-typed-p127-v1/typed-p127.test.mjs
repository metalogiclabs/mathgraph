import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {prepareP127Audit,assessP127Native} from './typed-p127.mjs';

const sourceBytes=readFileSync(new URL('./P127_RogersRamanujan.lean',import.meta.url),'utf8');
const type='theorem Mathathon.P127.rogers_ramanujan (n : ℕ) :\n  (Nat.Partition.restricted n fun i => i % 5 = 1 ∨ i % 5 = 4).card = (Mathathon.P127.gapTwoPartitions n).card';
const nativeOutput=`warning: declaration uses 'sorry'\nMATHGRAPH_P127_TYPE_BEGIN\n${type}\nMATHGRAPH_P127_TYPE_END\nMATHGRAPH_P127_AXIOMS_BEGIN\n'Mathathon.P127.rogers_ramanujan' depends on axioms: [sorryAx]\nMATHGRAPH_P127_AXIOMS_END\n`;
const context={sourceBytes,nativeOutput,exitCode:0,
  mathlibGit:'56a005855ea17e0b0958f73ec801ae140b0a1679',
  toolchainDigest:'7289597a44543246c9227b8cae501767e095ce17f6d448b95fc4a8dc97268f6d'};

test('native probe extends the exact official source and prints a declaration, not comments',()=>{
  const generated=prepareP127Audit(sourceBytes);
  assert.ok(generated.startsWith(sourceBytes));
  assert.match(generated.slice(sourceBytes.length),/#print Mathathon\.P127\.rogers_ramanujan/);
  assert.match(generated.slice(sourceBytes.length),/#print axioms Mathathon\.P127\.rogers_ramanujan/);
});

test('the original natural-bijection requirement remains uncovered by typed equality alone',()=>{
  const result=assessP127Native(context);
  assert.equal(result.status,'PINNED_NATIVE_TYPE_TEXT_OBSERVED');
  assert.equal(result.original_scope.declared_scope,'DECLARED_GAP');
  assert.deepEqual(result.original_scope.uncovered_requirement_ids,['natural-bijection']);
  assert.equal(result.narrowed_scope.declared_scope,'NO_DECLARED_GAP');
  assert.equal(result.proof_status,'NOT_ESTABLISHED_SORRY');
  assert.equal(result.intent_fidelity,'UNKNOWN');
  assert.equal(result.evidence_warrant,'UNKNOWN');
  assert.equal(typeof result.type_sha256,'string');
  assert.equal(result.type_sha256.length,64);
});

test('altering only a source comment fails the frozen public-source digest',()=>{
  const changed=sourceBytes.replace('The problem asks for a natural bijection',
    'The problem asks for a simple equality');
  assert.notEqual(changed,sourceBytes);
  assert.equal(assessP127Native({...context,sourceBytes:changed}).status,'UNKNOWN');
  assert.throws(()=>prepareP127Audit(changed),/SOURCE_BYTES_CHANGED/);
});

test('a malformed, missing, or duplicated print boundary fails closed',()=>{
  for(const output of ['',type,nativeOutput.replace('MATHGRAPH_P127_TYPE_END',''),
    nativeOutput+nativeOutput]){
    const result=assessP127Native({...context,nativeOutput:output});
    assert.equal(result.status,'UNKNOWN');
    assert.equal(result.intent_fidelity,'UNKNOWN');
  }
});

test('different toolchain, Mathlib, or native exit cannot attest the pinned type',()=>{
  for(const params of [
    {exitCode:1},{mathlibGit:'f'.repeat(40)},{toolchainDigest:'0'.repeat(64)},
  ]) assert.equal(assessP127Native({...context,...params}).status,'UNKNOWN');
});

test('opaque or non-cardinality text cannot inherit the operator count-equality annotation',()=>{
  const different=nativeOutput.replace(type,'theorem Mathathon.P127.rogers_ramanujan : True');
  assert.equal(assessP127Native({...context,nativeOutput:different}).status,'UNKNOWN');
});

test('an output without an observed sorry axiom cannot be called proved',()=>{
  const different=nativeOutput.replace('sorryAx','Classical.choice');
  const result=assessP127Native({...context,nativeOutput:different});
  assert.equal(result.proof_status,'UNKNOWN');
  assert.equal(result.intent_fidelity,'UNKNOWN');
});
