import test from 'node:test';import assert from 'node:assert/strict';import {readFile} from 'node:fs/promises';
import {mkdtemp,rm} from 'node:fs/promises';import {join} from 'node:path';import {tmpdir} from 'node:os';
const api=await import('./native-transfer-matrix-v1.mjs').catch(()=>({}));
const fixture=JSON.parse(await readFile(new URL('./fixtures/native-transfer-matrix-v1.json',import.meta.url)));
const engine=await readFile(new URL('./mention-fresh-proof-v1.mjs',import.meta.url));
const pass={status:'ORIGINAL_TARGET_VERIFIED',axioms:[]},fail={status:'UNKNOWN',diagnostic:'unsolved goals\n⊢ a ^ 2 = 1'};
test('matrix checkpoints baselines and applies at most two frozen variants',async()=>{
 assert.equal(typeof api.runNativeMatrix,'function');const events=[];let checks=0;
 const r=await api.runNativeMatrix({matrix:{...fixture,cases:[fixture.cases[0]]},engine,verify:async(f,p)=>{checks++;return p.includes('simp only')?pass:fail;},onEvidence:async e=>events.push(structuredClone(e))});
 assert.equal(checks,2);assert.equal(r.results[0].outcome,'REPAIRED');assert.equal(r.results[0].expectation_met,true);assert.equal(r.api_calls,0);
 assert.equal(events[0].stage,'BASELINE');assert.equal(events[1].stage,'VARIANT');assert.equal(r.results[0].repair.post_hoc,false);
});
test('false acceptance fails the declared matrix boundary',async()=>{
 assert.equal(typeof api.runNativeMatrix,'function');const r=await api.runNativeMatrix({matrix:{...fixture,cases:[fixture.cases[6]]},engine,verify:async()=>pass});
 assert.equal(r.expectations_met,false);assert.equal(r.results[0].expectation_met,false);
});
test('ineligible and forbidden drafts cannot run a variant',async()=>{
 assert.equal(typeof api.runNativeMatrix,'function');let checks=0;
 const r=await api.runNativeMatrix({matrix:{...fixture,cases:[fixture.cases[9]]},engine,verify:async()=>{checks++;return {status:'UNKNOWN',diagnostic:'unsolved goals\n⊢ False'};}});
 assert.equal(checks,1);assert.equal(r.results[0].outcome,'NOT_ACCEPTED_NO_VARIANTS');assert.equal(r.expectations_met,true);
});
test('false eligible drafts stop after two rejected variants',async()=>{
 assert.equal(typeof api.runNativeMatrix,'function');let checks=0;
 const r=await api.runNativeMatrix({matrix:{...fixture,cases:[fixture.cases[6]]},engine,verify:async()=>{checks++;return fail;}});
 assert.equal(checks,3);assert.equal(r.results[0].outcome,'NOT_ACCEPTED_VARIANTS');assert.equal(r.expectations_met,true);
});
test('engine drift refuses all native work',async()=>{
 assert.equal(typeof api.runNativeMatrix,'function');let checks=0;
 await assert.rejects(api.runNativeMatrix({matrix:fixture,engine:Buffer.concat([engine,Buffer.from(' ')]),verify:async()=>{checks++;return pass;}}),/FROZEN_ENGINE_CHANGED/);assert.equal(checks,0);
});
test('cleanup failure stops the matrix and preserves the earlier baseline',async()=>{
 assert.equal(typeof api.runNativeMatrix,'function');let saved,checks=0;
 await assert.rejects(api.runNativeMatrix({matrix:{...fixture,cases:[fixture.cases[0],fixture.cases[1]]},engine,verify:async()=>{if(++checks===2)throw Error('NATIVE_CLEANUP_UNCONFIRMED');return fail;},onEvidence:async e=>{saved=e;}}),/NATIVE_CLEANUP_UNCONFIRMED/);
 assert.equal(checks,2);assert.equal(saved.stage,'BASELINE');
});
test('resource failure is incomplete execution, never a successful negative control',async()=>{
 const events=[];
 await assert.rejects(api.runNativeMatrix({matrix:{...fixture,cases:[fixture.cases[9]]},engine,verify:async()=>({status:'UNKNOWN',diagnostic:'NATIVE_RESOURCE_LIMIT_OR_EXECUTION_INCOMPLETE'}),onEvidence:async e=>events.push(e)}),/MATRIX_NATIVE_INCOMPLETE/);
 assert.equal(events.at(-1).stage,'INCOMPLETE');
});
test('resource failure during a false-case variant cannot satisfy rejection expectations',async()=>{
 let n=0;
 await assert.rejects(api.runNativeMatrix({matrix:{...fixture,cases:[fixture.cases[6]]},engine,verify:async()=>++n===1?fail:{status:'UNKNOWN',diagnostic:'NATIVE_RESOURCE_LIMIT_OR_EXECUTION_INCOMPLETE'}}),/MATRIX_NATIVE_INCOMPLETE/);
 assert.equal(n,2);
});
test('later checkpoints never overwrite a completed evidence record',async()=>{
 assert.equal(typeof api.writeMatrixEvent,'function');const dir=await mkdtemp(join(tmpdir(),'matrix-evidence-'));
 try{
  await api.writeMatrixEvent(dir,'evidence',1,{stage:'BASELINE'});await api.writeMatrixEvent(dir,'evidence',2,{stage:'VARIANT'});
  await assert.rejects(api.writeMatrixEvent(dir,'evidence',1,{stage:'REPLACED'}),/EEXIST/);
  assert.deepEqual(JSON.parse(await readFile(join(dir,'evidence-1.json'),'utf8')),{stage:'BASELINE'});
 }finally{await rm(dir,{recursive:true,force:true});}
});
