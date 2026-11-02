import test from 'node:test';import assert from 'node:assert/strict';
const m=await import('./mention-native-demo-v1.mjs').catch(()=>({}));
test('bounded native demo module exists',()=>assert.equal(typeof m.nativeDemo,'function'));
test('frozen claim cannot be weakened by candidate proof',()=>{
 assert.match(m.originalTarget,/\(xs : List Nat\) : xs.reverse.length = xs.length/);
 assert.match(m.brokenSource,/\(h : xs.reverse.length = xs.length\)/);
 for(const p of ['by simp','by simpa','by exact List.length_reverse xs'])assert.match(m.repairedSource(p),/theorem mathgraph_reverse_length \(xs : List Nat\) : xs.reverse.length = xs.length :=/);
 for(const p of ['by sorry','by admit','by\n exact False.elim (by sorry)','by simp\naxiom x : False','by run_tac IO.println "x"'])assert.throws(()=>m.repairedSource(p),/UNSUPPORTED_PROOF/);
});
test('native compiler success does not conceal a rejected consumer',async()=>{
 const calls=[];const r=await m.nativeDemo({source:m.brokenSource,run:async(name,source)=>{calls.push({name,source});return {code:name==='Consumer'?1:0,output:name==='Consumer'?'type mismatch':''};}});
 assert.equal(r.source_compiles,true);assert.equal(r.original_claim_satisfied,false);assert.equal(r.status,'CLAIM_NOT_ESTABLISHED');assert.ok(calls.some(x=>x.name==='Consumer'));
});
test('repair satisfies the original consumer and zero-axiom audit',async()=>{
 const r=await m.nativeDemo({source:m.repairedSource('by simp'),run:async name=>({code:0,output:name==='Consumer'?"'mathgraph_reverse_length' does not depend on any axioms":''})});assert.equal(r.status,'ORIGINAL_TARGET_VERIFIED');
});
test('missing axiom audit or compile failure cannot pass',async()=>{
 for(const run of [async()=>({code:0,output:''}),async()=>({code:1,output:'error'})])assert.notEqual((await m.nativeDemo({source:m.repairedSource('by simp'),run})).status,'ORIGINAL_TARGET_VERIFIED');
});
test('unrecognized source is never executed',async()=>{
 let calls=0;await assert.rejects(m.nativeDemo({source:'import Unsafe\n#eval IO.println "x"',run:async()=>{calls++;}}),/UNSUPPORTED_DEMO_SOURCE/);assert.equal(calls,0);
});
test('actual Lean propext dependency is reported without claiming zero axioms',async()=>{
 const result=await m.nativeDemo({source:m.repairedSource('by simp'),run:async name=>({code:0,output:name==='Consumer'?"'mathgraph_reverse_length' depends on axioms: [propext]\n":''})});assert.equal(result.status,'ORIGINAL_TARGET_VERIFIED');assert.deepEqual(result.axioms,['propext']);
});
test('custom or sorry axioms never pass the native audit',async()=>{
 for(const axiom of ['sorryAx','unproved_claim','propext, sorryAx']){
 const result=await m.nativeDemo({source:m.repairedSource('by simp'),run:async name=>({code:0,output:name==='Consumer'?"'mathgraph_reverse_length' depends on axioms: ["+axiom+"]\n":''})});assert.notEqual(result.status,'ORIGINAL_TARGET_VERIFIED');
 }
});
