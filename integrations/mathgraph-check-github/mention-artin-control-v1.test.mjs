import test from 'node:test';import assert from 'node:assert/strict';
const m=await import('./mention-artin-control-v1.mjs').catch(()=>({}));
test('published target retains Group and only the commuting-generator hypothesis',()=>{
 assert.match(m.artinTarget,/\[Group G\]/);assert.doesNotMatch(m.artinTarget,/CommGroup/);
 assert.match(m.artinStrongSource,/\[CommGroup G\]/);assert.match(m.artinRepairSource,/closureCommGroupOfComm/);
 assert.ok(m.artinRepairSource.includes(m.artinTarget));assert.doesNotMatch(m.artinRepairSource,/sorry|admit|axiom /);
});
test('native Artin control requires rejected strong consumer, accepted original consumer and audited axioms',async()=>{
 const calls=[];const r=await m.qualifyArtin({run:async(name,source)=>{calls.push({name,source});return {code:name==='StrongConsumer'?1:0,output:name==='StrongConsumer'?'failed to synthesize CommGroup G':name==='RepairConsumer'?"'Artin_exercise_2_2_9' depends on axioms: [propext, Classical.choice, Quot.sound]":''};}});
 assert.equal(r.status,'ARTIN_CONTROLS_VERIFIED');assert.equal(calls.length,4);assert.deepEqual(r.axioms,['propext','Classical.choice','Quot.sound']);
});
test('Artin controls never pass on an accepted strong consumer, missing audit or sorry axiom',async()=>{
 for(const mode of ['strong-passes','missing-audit','sorry']){
  const r=await m.qualifyArtin({run:async name=>({code:name==='StrongConsumer'&&mode!=='strong-passes'?1:0,output:name==='StrongConsumer'?'failed to synthesize CommGroup G':name==='RepairConsumer'&&mode==='sorry'?"'Artin_exercise_2_2_9' depends on axioms: [sorryAx]":''})});assert.notEqual(r.status,'ARTIN_CONTROLS_VERIFIED');
 }
});
