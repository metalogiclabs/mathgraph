import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {bindFormalPair,assessSemantEq,qualifyOriginalRepair} from './generic-claim-audit-v1.mjs';

const sha=s=>createHash('sha256').update(s).digest('hex');
const reference={path:'Original.lean',source:'import Init\ntheorem original (n : Nat) : n + 0 = n := by simp\n'};
const candidate={path:'Candidate.lean',source:'import Init\ntheorem proposed (n : Nat) : n = n := by rfl\n'};
const bound=()=>bindFormalPair({reference,candidate,expectedReferenceSha:sha(reference.source)});
const result=(binding,verdict='EquivalentRestricted')=>({id:binding.case_id,verdict,reference:{ok:true},candidate:{ok:true}});
const meta={tool:'semanteq',version:'v1.4.0',git:'f927670',dirty:false};
const execution=b=>({kind:'LOCAL_NATIVE_SEMANTEQ',exitCode:0,referenceSha256:b.reference_sha256,candidateSha256:b.candidate_sha256,toolGit:'f927670',outputSha256:sha('native-result'),command:['lake','env','.lake/build/bin/semanteq']});

test('binds exact trusted reference and candidate bytes without treating diffs as semantic changes',()=>{
 const b=bound();
 assert.equal(b.reference_sha256,sha(reference.source));
 assert.equal(b.candidate_sha256,sha(candidate.source));
 assert.notEqual(b.reference_sha256,b.candidate_sha256);
 assert.equal(b.reference_path,'Original.lean');
 assert.match(b.case_id,/^formal:/);
 assert.equal(b.intent_fidelity,'UNKNOWN');
 assert.equal(b.evidence_warrant,'UNKNOWN');
});
test('rejects stale or missing original-claim trust anchor',()=>{
 assert.throws(()=>bindFormalPair({reference,candidate,expectedReferenceSha:sha('another theorem')}),/REFERENCE_SHA_MISMATCH/);
 assert.throws(()=>bindFormalPair({reference,candidate}),/EXPECTED_REFERENCE_SHA_REQUIRED/);
 assert.throws(()=>bindFormalPair({reference:{path:'x',source:''},candidate,expectedReferenceSha:sha('')}),/SOURCE_REQUIRED/);
});
test('only clean locally executed equivalence results certify a formal-statement relation',()=>{
 const b=bound();
 for(const verdict of ['ExactMatch','DefEq','EquivalentRestricted']){
  const a=assessSemantEq({binding:b,record:result(b,verdict),metadata:meta,execution:execution(b)});
  assert.equal(a.formal_statement_relation,'NATIVE_CERTIFIED_EQUIVALENT');
  assert.equal(a.intent_fidelity,'UNKNOWN');
  assert.equal(a.evidence_warrant,'UNKNOWN');
  assert.equal(a.candidate_source_build,'NOT_RUN');
 }
});
test('directional, negative, timeout, error, and unknown records abstain',()=>{
 const b=bound();
 for(const verdict of ['LikelyTooStrong','LikelyTooWeak','Inconclusive','Timeout','ElabError','False','NotEquivalent']){
  const a=assessSemantEq({binding:b,record:result(b,verdict),metadata:meta,execution:execution(b)});
  assert.equal(a.formal_statement_relation,'UNKNOWN',verdict);
  assert.equal(a.diagnostic_verdict,verdict);
 }
});
test('rejects wrong case, tool, toolchain, missing native execution, bad exit, or failed elaboration',()=>{
 const b=bound();
 const args={binding:b,record:result(b),metadata:meta,execution:execution(b)};
 const variants=[
  {...args,record:{...result(b),id:'formal:another'}},
  {...args,metadata:{...meta,git:'bad1234'}},
  {...args,metadata:{...meta,dirty:true}},
  {...args,metadata:{...meta,tool:'pretend-checker'}},
  {...args,execution:{...execution(b),exitCode:1}},
  {...args,execution:{...execution(b),referenceSha256:sha('stale')}},
  {...args,execution:null},
  {...args,record:{...result(b),candidate:{ok:false}}}
 ];
 for(const v of variants){
  const a=assessSemantEq(v);
  assert.equal(a.formal_statement_relation,'UNKNOWN');
  assert.equal(a.evidence_warrant,'UNKNOWN');
 }
});
test('original-target repair only advances with matching native source and consumer replay and standard axiom audit',()=>{
 const b=bound();
 const sourceReplay={exitCode:0,candidateSha256:b.candidate_sha256,kind:'NATIVE_LEAN'};
 const consumerReplay={exitCode:0,referenceSha256:b.reference_sha256,kind:'NATIVE_LEAN',axioms:['propext','Classical.choice']};
 const accepted=qualifyOriginalRepair({binding:b,sourceReplay,consumerReplay});
 assert.equal(accepted.original_target_status,'NATIVE_CONSUMER_ACCEPTED');
 assert.equal(accepted.intent_fidelity,'UNKNOWN');
 assert.equal(accepted.evidence_warrant,'UNKNOWN');
 for(const invalid of [
  {...consumerReplay,exitCode:1},
  {...consumerReplay,axioms:null},
  {...consumerReplay,axioms:['sorryAx']},
  {...consumerReplay,referenceSha256:sha('wrong')},
  {...consumerReplay,kind:'SYNTHETIC_CI'}
 ]) assert.equal(qualifyOriginalRepair({binding:b,sourceReplay,consumerReplay:invalid}).original_target_status,'UNKNOWN');
 assert.equal(qualifyOriginalRepair({binding:b,sourceReplay:{...sourceReplay,candidateSha256:sha('wrong')},consumerReplay}).original_target_status,'UNKNOWN');
});
