import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {freezeTheorem} from './mention-fresh-proof-v1.mjs';
const api=await import('./mention-transfer-proof-v1.mjs').catch(()=>({}));
const frozen=freezeTheorem('import Mathlib\ntheorem probe (n : Nat) : n = n := by\n sorry\n');
const ok={status:'ORIGINAL_TARGET_VERIFIED',axioms:[]},bad={status:'UNKNOWN',diagnostic:'unsolved goals\n⊢ n ^ 2 = n ^ 2'};
const generate=async()=>({proof_body:'by group',usage:{input_tokens:20,output_tokens:10}});

test('transfer preserves a shared-first tie and spends no extra model call',async()=>{
 assert.equal(typeof api.runTransferComparison,'function');let count=0;
 const r=await api.runTransferComparison({frozen,generate:async()=>{count++;return generate();},verify:async()=>ok});
 assert.equal(count,1);assert.equal(r.transfer,'SHARED_FIRST_PASSED_NO_TRANSFER_EVIDENCE');assert.equal(r.native_attempts,0);
});
test('frozen variants may repair guided failure without rewriting the raw negative result',async()=>{
 assert.equal(typeof api.runTransferComparison,'function');let count=0,checks=0;
 const r=await api.runTransferComparison({frozen,generate:async()=>{count++;return generate();},verify:async proof=>{checks++;return proof.includes('simp only [pow_succ, pow_zero, mul_one]')?ok:bad;}});
 assert.equal(count,3);assert.equal(checks,4);assert.equal(r.raw.comparison,'NO_NATIVE_FEEDBACK_ADVANTAGE_SHOWN');
 assert.equal(r.transfer,'FROZEN_NATIVE_REPAIR_TRANSFERRED_ON_ONE_CASE');assert.equal(r.mathgraph.status,'ORIGINAL_TARGET_VERIFIED');assert.equal(r.mathgraph.post_hoc,false);assert.equal(r.native_attempts,1);
});
test('ineligible diagnostics cannot invent a transfer success',async()=>{
 assert.equal(typeof api.runTransferComparison,'function');let checks=0;
 const r=await api.runTransferComparison({frozen,generate,verify:async()=>{checks++;return {status:'UNKNOWN',diagnostic:'unknown identifier missing'};}});
 assert.equal(checks,3);assert.equal(r.transfer,'NO_FROZEN_NATIVE_REPAIR_TRANSFER_SHOWN');assert.equal(r.native_attempts,0);
});
test('eligible failures stop after two frozen native variants',async()=>{
 assert.equal(typeof api.runTransferComparison,'function');let checks=0;
 const r=await api.runTransferComparison({frozen,generate,verify:async()=>{checks++;return bad;}});
 assert.equal(checks,5);assert.equal(r.native_attempts,2);assert.equal(r.mathgraph.status,'UNKNOWN');
});
test('an already accepted guided revision is not counted as native tactic transfer',async()=>{
 assert.equal(typeof api.runTransferComparison,'function');let n=0;
 const r=await api.runTransferComparison({frozen,generate,verify:async()=>++n===3?ok:bad});
 assert.equal(n,3);assert.equal(r.transfer,'MODEL_FEEDBACK_SUCCESS_NATIVE_REPAIR_UNTESTED');assert.equal(r.native_attempts,0);
});
test('cleanup uncertainty propagates rather than continuing a portfolio',async()=>{
 assert.equal(typeof api.runTransferComparison,'function');let n=0,saved;
 await assert.rejects(api.runTransferComparison({frozen,generate,onRaw:async r=>{saved=structuredClone(r);},verify:async()=>{if(++n===4)throw Error('NATIVE_CLEANUP_UNCONFIRMED');return bad;}}),/NATIVE_CLEANUP_UNCONFIRMED/);assert.equal(n,4);
 assert.equal(saved?.comparison,'NO_NATIVE_FEEDBACK_ADVANTAGE_SHOWN');assert.equal(saved?.unique_api_calls,3);
});
const current={id:100,event:'push',run_attempt:1,actor:{id:32909488},head_branch:'research/mathgraph-proof-transfer-v1-20261102',path:'.github/workflows/mathgraph-fresh-transfer-v1.yml'};
test('new epoch accepts only first owner push with complete history',()=>{
 assert.equal(typeof api.authorizeTransferRun,'function');assert.equal(api.authorizeTransferRun(current,{total_count:1,workflow_runs:[current]}),true);
 for(const c of [{...current,run_attempt:2},{...current,actor:{id:1}},{...current,path:'.github/workflows/mathgraph-fresh-proof-v1.yml'},{...current,head_branch:'main'}])assert.throws(()=>api.authorizeTransferRun(c,{total_count:1,workflow_runs:[c]}),/TRANSFER_EPOCH_REFUSED/);
 for(const h of [{total_count:2,workflow_runs:[current]},{total_count:2,workflow_runs:[{id:99},current]},{total_count:0,workflow_runs:[]}])assert.throws(()=>api.authorizeTransferRun(current,h),/TRANSFER_EPOCH_REFUSED/);
});
test('changed engine or source bytes cannot begin a transfer comparison',async()=>{
 assert.equal(typeof api.bindTransferInputs,'function');const protocolBytes=await readFile(new URL('./fixtures/fresh-transfer-protocol-v1.json',import.meta.url));
 const engine=await readFile(new URL('./mention-fresh-proof-v1.mjs',import.meta.url)),source=await readFile(new URL('./fixtures/proofnet-heldout-3.lean',import.meta.url));
 const binding=JSON.parse(await readFile(new URL('./fixtures/fresh-transfer-binding-v1.json',import.meta.url)));
 assert.equal(api.bindTransferInputs({protocolBytes,binding,engine,source}).name,'Artin_exercise_2_11_3');
 assert.throws(()=>api.bindTransferInputs({protocolBytes:Buffer.concat([protocolBytes,Buffer.from(' ')]),binding,engine,source}),/FROZEN_PROTOCOL_CHANGED/);
 assert.throws(()=>api.bindTransferInputs({protocolBytes,binding:{...binding,target_sha256:'f'.repeat(64)},engine,source}),/TRANSFER_TARGET_CHANGED/);
 assert.throws(()=>api.bindTransferInputs({protocolBytes,binding,engine:Buffer.concat([engine,Buffer.from(' ')]),source}),/FROZEN_ENGINE_CHANGED/);
 assert.throws(()=>api.bindTransferInputs({protocolBytes,binding,engine,source:Buffer.concat([source,Buffer.from(' ')])}),/TRANSFER_SOURCE_CHANGED/);
});
test('missing preregistration or target pins cannot certify prospectivity',async()=>{
 const protocolBytes=await readFile(new URL('./fixtures/fresh-transfer-protocol-v1.json',import.meta.url));
 const engine=await readFile(new URL('./mention-fresh-proof-v1.mjs',import.meta.url)),source=await readFile(new URL('./fixtures/proofnet-heldout-3.lean',import.meta.url));
 const binding={source_sha256:createHash('sha256').update(source).digest('hex')};
 assert.throws(()=>api.bindTransferInputs({protocolBytes,binding,engine,source}),/TRANSFER_PREREGISTRATION_REFUSED/);
});
