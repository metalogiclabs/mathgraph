import test from 'node:test';
import assert from 'node:assert/strict';
import {auditArtinAxioms} from './proofnet-artin-axioms-v1.mjs';

const report=axioms=>`'Artin_exercise_2_2_9' depends on axioms: [${axioms}]\n`;

test('Lean axiom output is bounded to the known classical kernel axioms',()=>{
  const r=auditArtinAxioms(report('propext, Classical.choice, Quot.sound'));
  assert.equal(r.verdict,'AXIOMS_WITHIN_CLASSICAL_LEAN_ALLOWLIST');
  assert.equal(r.intent_verification,'NOT_ESTABLISHED');
  assert.equal(r.source_review,'UNKNOWN');
  assert.equal(r.permission,'ADVISORY_ONLY');
  assert.equal(auditArtinAxioms(report('')).observed_axioms.length,0);
});

test('sorry, native_decide, custom axioms, duplicate or absent output all fail',()=>{
  for(const bad of ['sorryAx','Lean.ofReduceBool','Custom.axiom',
    'propext, propext','propext, Classical.choice, sorryAx']){
    assert.throws(()=>auditArtinAxioms(report(bad)),/UNAPPROVED_OR_DUPLICATE_AXIOM/);
  }
  for(const bad of ['',report('propext')+report('propext'),
    "'Other' depends on axioms: [propext]",'Artin_exercise_2_2_9: []']){
    assert.throws(()=>auditArtinAxioms(bad),/EXACT_AXIOM_REPORT_REQUIRED/);
  }
});
