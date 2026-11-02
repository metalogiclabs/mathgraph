import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {runGenericLeanConsumer} from './generic-lean-consumer-run-v1.mjs';
const sha=s=>createHash('sha256').update(s).digest('hex');
const reference={path:'TrustedArithmetic.lean',source:'import Init\ntheorem trusted (n : Nat) : n + 0 = n := by simp\n'};
const faithfulCandidate={path:'Candidate.lean',source:'import Init\ntheorem candidate (n : Nat) : n = n := by rfl\n'};
const invalidCandidate={path:'Candidate.lean',source:'import Init\ntheorem candidate (n : Nat) : n = 0 := by sorry\n'};
const sorryCandidate={path:'Candidate.lean',source:'import Init\ntheorem candidate (n : Nat) : n + 0 = n := by sorry\n'};
const consumerSource='import Candidate\ntheorem MathGraphConsumer.original_claim (n : Nat) : n + 0 = n := by\n  exact candidate n\n';
const projectDir=process.env.MATHGRAPH_SEMANTEQ_PROJECT;
const inputs=(candidate=faithfulCandidate)=>({reference,candidate,expectedReferenceSha:sha(reference.source),
 consumerSource,expectedConsumerSha:sha(consumerSource),consumerName:'MathGraphConsumer.original_claim',projectDir});

test('consumer replay requires separately anchored consumer bytes',async()=>{
 await assert.rejects(runGenericLeanConsumer({...inputs(),expectedConsumerSha:sha('forged')}),/CONSUMER_SHA_MISMATCH/);
});
test('missing Lean environment is UNKNOWN, not Lean rejection',async()=>{
 const r=await runGenericLeanConsumer({...inputs(),projectDir:'/missing-native-project'});
 assert.equal(r.execution_status,'ENVIRONMENT_UNAVAILABLE');
 assert.equal(r.original_target_status,'UNKNOWN');
 assert.equal(r.evidence_warrant,'UNKNOWN');
});
test('candidate proof reference requires a safe exact theorem name, and missing native tool preserves UNKNOWN',async()=>{
 await assert.rejects(runGenericLeanConsumer({...inputs(),candidateName:'candidate\n#eval IO.println "fake"'}),/CANDIDATE_NAME_INVALID/);
 const r=await runGenericLeanConsumer({...inputs(),candidateName:'candidate',projectDir:'/missing-native-project'});
 assert.equal(r.execution_status,'ENVIRONMENT_UNAVAILABLE');
 assert.equal(r.actual_candidate_proof_term_reference,'UNKNOWN');
 assert.equal(r.normalized_direct_reference,null);
 assert.equal(r.candidate_dependence,'UNKNOWN');
 assert.equal(r.intent_fidelity,'UNKNOWN');
 assert.equal(r.evidence_warrant,'UNKNOWN');
});
test('native replay accepts a separately compiled original-target consumer and audits axioms', {skip:!projectDir},async()=>{
 const r=await runGenericLeanConsumer({...inputs(),timeoutMs:60000});
 assert.equal(r.execution_status,'EXECUTED');
 assert.equal(r.candidate_source_build,'LEAN_ACCEPTED');
 assert.equal(r.original_target_status,'NATIVE_CONSUMER_ACCEPTED');
 assert.deepEqual(r.axioms,[]);
 assert.equal(r.intent_fidelity,'UNKNOWN');
 assert.equal(r.evidence_warrant,'UNKNOWN');
 assert.equal(r.mathlib_git,'0c154d67103f74be3a0f2c509f72ccbf5be9f2a7');
});
test('native replay cannot promote a sorry-based, wrong-target candidate', {skip:!projectDir},async()=>{
 const r=await runGenericLeanConsumer({...inputs(invalidCandidate),timeoutMs:60000});
 assert.equal(r.execution_status,'EXECUTED');
 assert.equal(r.original_target_status,'UNKNOWN');
 assert.equal(r.evidence_warrant,'UNKNOWN');
});
test('native accepted candidate and consumer remain blocked when the axiom audit finds sorryAx', {skip:!projectDir},async()=>{
 const r=await runGenericLeanConsumer({...inputs(sorryCandidate),timeoutMs:60000});
 assert.equal(r.execution_status,'EXECUTED');
 assert.equal(r.candidate_source_build,'LEAN_ACCEPTED');
 assert.equal(r.trace.length,3);
 assert.equal(r.trace[1].exit_code,0);
 assert.equal(r.trace[2].exit_code,0);
 assert.match(r.trace[2].stdout,/sorryAx/);
 assert.equal(r.original_target_status,'UNKNOWN');
 assert.equal(r.evidence_warrant,'UNKNOWN');
});
test('native replay identifies a true direct proof-term reference without promoting semantic necessity',{skip:!projectDir},async()=>{
 const candidate={path:'Candidate.lean',source:'import Init\ntheorem candidate (n : Nat) : n + 0 = n := by simp\n'};
 const result=await runGenericLeanConsumer({...inputs(candidate),candidateName:'candidate',timeoutMs:60000});
 assert.equal(result.execution_status,'EXECUTED');
 assert.equal(result.normalized_direct_reference,true);
 assert.equal(result.actual_candidate_proof_term_reference,'NATIVE_ZETA_NORMALIZED_DIRECT_REFERENCE');
 assert.equal(result.candidate_dependence,'UNKNOWN');
 assert.equal(result.intent_fidelity,'UNKNOWN');
 assert.equal(result.evidence_warrant,'UNKNOWN');
});
