import test from 'node:test';import assert from 'node:assert/strict';
const m=await import('./mention-group-native-v1.mjs').catch(()=>({}));
test('group adapter accepts restricted drafts only for the frozen qualified statements',()=>{
 assert.equal(typeof m.bindGroupSource,'function');const f=m.bindGroupSource(m.groupBrokenSource);assert.equal(f.proof,'by group');
 for(const source of [m.groupBrokenSource.replace('^ 2 =','^ 5 ='),'import Unsafe\n'+m.groupBrokenSource,m.groupBrokenSource+'\ntheorem extra : True := by trivial',m.groupBrokenSource.replace('by group','by sorry'),m.groupBrokenSource+'\nlemma extra : True := by trivial\n',m.groupBrokenSource+'\ninductive Extra where | x\n',m.groupBrokenSource+'\nrun_cmd pure ()\n'])assert.throws(()=>m.bindGroupSource(source),/UNSUPPORTED_GROUP_SOURCE/);
});
test('completed proof failure is distinguished from incomplete native execution',async()=>{
 assert.equal(typeof m.nativeGroup,'function');const r=await m.nativeGroup({source:m.groupBrokenSource,run:async()=>({code:1,output:'Candidate.lean: error: unsolved goals\n⊢ a ^ 2 = a ^ 2'})});assert.equal(r.status,'CLAIM_NOT_ESTABLISHED');assert.equal(r.source_compiles,false);
 const incomplete=await m.nativeGroup({source:m.groupBrokenSource,run:async()=>{throw Error('NATIVE_RESOURCE_LIMIT');}});assert.equal(incomplete.status,'UNKNOWN');
});
test('group repair uses actual diagnostic and frozen variants under the same original target',async()=>{
 assert.equal(typeof m.repairGroup,'function');const seen=[];
 const r=await m.repairGroup({source:m.groupBrokenSource,initial:{diagnostic:'error: unsolved goals\n⊢ a ^ 2 = b ^ 2'},run:async(name,source)=>{seen.push({name,source});return {code:0,output:name==='Consumer'?"'conjugate_power_2' depends on axioms: [propext]\n":''};}});
 assert.ok(r.source.includes('simp only [pow_succ, pow_zero, mul_one]; group'));assert.equal(r.receipt.status,'ORIGINAL_TARGET_VERIFIED');assert.equal(m.bindGroupSource(r.source).frozen.target_sha256,m.bindGroupSource(m.groupBrokenSource).frozen.target_sha256);assert.equal(seen.length,2);
});
test('failed or ineligible group repair never returns a publishable patch',async()=>{
 assert.equal(typeof m.repairGroup,'function');let runs=0;
 const r=await m.repairGroup({source:m.groupBrokenSource,initial:{diagnostic:'unknown identifier'},run:async()=>{runs++;return {code:0,output:''};}});assert.equal(r.source,null);assert.equal(r.receipt.native_attempts,0);assert.equal(runs,0);
});
test('missing dependencies and failed consumers remain incomplete with accurate compilation state',async()=>{
 const missing=await m.nativeGroup({source:m.groupBrokenSource,run:async()=>({code:1,output:'error: object file of module Mathlib does not exist'})});assert.equal(missing.status,'UNKNOWN');assert.equal(missing.source_compiles,null);
 const consumer=await m.nativeGroup({source:m.groupBrokenSource,run:async name=>name==='Candidate'?{code:0,output:''}:{code:1,output:'error: unsolved goals\n⊢ a ^ 2 = b ^ 2'}});assert.equal(consumer.status,'UNKNOWN');assert.equal(consumer.source_compiles,true);
});
test('repair receipts retain the attempt and winning transformation',async()=>{
 const events=[];
 const r=await m.repairGroup({source:m.groupBrokenSource,initial:{diagnostic:'error: unsolved goals\n⊢ a ^ 2 = b ^ 2'},onAttempt:async item=>events.push(item),run:async name=>({code:0,output:name==='Consumer'?"'conjugate_power_2' depends on axioms: [propext]\n":''})});
 assert.equal(events.length,1);assert.equal(r.receipt.native_attempts,1);assert.equal(r.receipt.method,'NORMALIZE_NATURAL_POWERS_BEFORE_GROUP_SIMPLIFICATION');assert.equal(r.receipt.attempts.length,1);
});
test('resource-limited repair stops as incomplete instead of trying another variant',async()=>{
 let runs=0;
 await assert.rejects(m.repairGroup({source:m.groupBrokenSource,initial:{diagnostic:'error: unsolved goals\n⊢ a ^ 2 = b ^ 2'},run:async()=>{runs++;throw Error('NATIVE_RESOURCE_LIMIT');}}),/GROUP_NATIVE_EXECUTION_INCOMPLETE/);assert.equal(runs,1);
});
