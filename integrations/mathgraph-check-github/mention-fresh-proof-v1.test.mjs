import test from 'node:test';import assert from 'node:assert/strict';
const m=await import('./mention-fresh-proof-v1.mjs').catch(()=>({}));
const source='import Mathlib\n\ntheorem fresh_identity (n : Nat) : n = n := by\n  sorry\n';
test('fresh engine freezes statement bytes and cannot accept a replacement theorem',()=>{
 const f=m.freezeTheorem(source,{repository:'example/corpus',commit:'a'.repeat(40),path:'fresh.lean'});
 assert.equal(f.name,'fresh_identity');assert.match(m.renderCandidate(f,'by\n  rfl'),/theorem fresh_identity \(n : Nat\) : n = n := by\n  rfl/);
 assert.throws(()=>m.freezeTheorem(source+'\ntheorem second : True := by trivial',{}),/SOURCE_TEMPLATE/);
 for(const p of ['by sorry','by admit','by\n  set_option debug.skipKernelTC true in trivial','by\n  run_tac pure ()','by\n  exact (unsafeCast True.intro)','by rfl\ntheorem forged : False := by sorry','by\n  #eval IO.println "x"'])assert.throws(()=>m.renderCandidate(f,p),/UNSUPPORTED_PROOF_BODY/);
});
test('fresh verification requires the unchanged consumer and a clean axiom audit',async()=>{
 const f=m.freezeTheorem(source,{});
 const result=await m.verifyFresh({frozen:f,proof:'by rfl',run:async name=>({code:0,output:name==='Consumer'?"'fresh_identity' does not depend on any axioms":''})});assert.equal(result.status,'ORIGINAL_TARGET_VERIFIED');
 for(const output of ['',"'fresh_identity' depends on axioms: [sorryAx]","'fresh_identity' depends on axioms: [custom_axiom]"]){const r=await m.verifyFresh({frozen:f,proof:'by rfl',run:async()=>({code:0,output})});assert.equal(r.status,'UNKNOWN');}
});
test('comparison shares a first candidate, reports a tie, and never asks for a registered answer',async()=>{
 const calls=[];const f=m.freezeTheorem(source,{});
 const r=await m.runFreshComparison({frozen:f,generate:async x=>{calls.push(x);return {proof_body:'by rfl',usage:{input_tokens:10,output_tokens:10}};},verify:async()=>({status:'ORIGINAL_TARGET_VERIFIED',axioms:[]})});assert.equal(calls.length,1);assert.equal(r.comparison,'SHARED_FIRST_CANDIDATE_PASSED_NO_ADVANTAGE_SHOWN');assert.equal(r.registered_repair_used,false);
});
test('a failed first candidate gets equal-call revisions with feedback isolated to MathGraph arm',async()=>{
 const calls=[];const f=m.freezeTheorem(source,{});let n=0;
 const r=await m.runFreshComparison({frozen:f,generate:async x=>{calls.push(x);return {proof_body:'by rfl',usage:{input_tokens:10,output_tokens:10}};},verify:async()=>++n===3?{status:'ORIGINAL_TARGET_VERIFIED',axioms:[]}:{status:'UNKNOWN',diagnostic:'type mismatch'}});
 assert.equal(calls.length,3);assert.equal(calls[1].native_feedback,undefined);assert.match(calls[2].native_feedback,/type mismatch/);assert.equal(r.llm_alone.status,'UNKNOWN');assert.equal(r.mathgraph.status,'ORIGINAL_TARGET_VERIFIED');assert.equal(r.unique_api_calls,3);
});
test('generation failure is not automatically retried and malformed usage is refused',async()=>{
 const f=m.freezeTheorem(source,{});let calls=0;
 await assert.rejects(m.runFreshComparison({frozen:f,generate:async()=>{calls++;throw Error('MODEL_FAILED');},verify:async()=>({})}),/MODEL_FAILED/);assert.equal(calls,1);
 await assert.rejects(m.runFreshComparison({frozen:f,generate:async()=>({proof_body:'by rfl',usage:{input_tokens:-1,output_tokens:10}}),verify:async()=>({})}),/MODEL_USAGE/);
});

test('unsupported declaration context is refused rather than silently erased',()=>{
 assert.throws(()=>m.freezeTheorem(source.replace('import Mathlib','import Mathlib\naxiom secret_oracle : False'),{}),/SOURCE_CONTEXT/);
 assert.throws(()=>m.freezeTheorem(source.replace('import Mathlib','import Mathlib\nimport Unpinned'),{}),/SOURCE_CONTEXT/);
});

test('the paid epoch accepts only the first owner push on its fixed workflow',()=>{
 const c={id:1,event:'push',run_attempt:1,actor:{id:32909488},head_branch:'feat/mathgraph-mention-agent-v1-20261102',path:'.github/workflows/mathgraph-fresh-proof-v1.yml'},h={total_count:1,workflow_runs:[{id:1}]};
 assert.equal(m.authorizeProspectiveRun(c,h),true);
 for(const [run,history] of [[{...c,run_attempt:2},h],[{...c,actor:{id:2}},h],[{...c,event:'pull_request'},h],[{...c,id:2},{total_count:2,workflow_runs:[{id:1},{id:2}]}],[c,{total_count:2,workflow_runs:[{id:1}]}]])assert.throws(()=>m.authorizeProspectiveRun(run,history),/PROSPECTIVE_EPOCH/);
});
test('a resource-limited candidate remains UNKNOWN',async()=>{
 const f=m.freezeTheorem(source,{});const r=await m.verifyFresh({frozen:f,proof:'by rfl',run:async()=>{throw Error('NATIVE_RESOURCE_LIMIT');}});assert.equal(r.status,'UNKNOWN');assert.match(r.diagnostic,/NATIVE_RESOURCE_LIMIT/);
});

test('unconfirmed native cleanup stops comparison before another paid call',async()=>{
 const frozen=m.freezeTheorem(source,{});let calls=0;
 await assert.rejects(m.runFreshComparison({frozen,generate:async()=>{calls++;return {proof_body:'by rfl',usage:{input_tokens:1,output_tokens:1}};},verify:proof=>m.verifyFresh({frozen,proof,run:async()=>{throw Error('NATIVE_CLEANUP_UNCONFIRMED');}})}),/NATIVE_CLEANUP_UNCONFIRMED/);assert.equal(calls,1);
});
