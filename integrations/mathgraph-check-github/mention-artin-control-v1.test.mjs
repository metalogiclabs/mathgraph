import test from 'node:test';import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const publishedSource=readFileSync(new URL('./fixtures/proofnet-artin-statement-v1.lean',import.meta.url),'utf8');
const m=await import('./mention-artin-control-v1.mjs').catch(()=>({}));
test('published target retains Group and only the commuting-generator hypothesis',()=>{
 assert.match(m.artinTarget,/\[Group G\]/);assert.doesNotMatch(m.artinTarget,/CommGroup/);
 assert.match(m.artinStrongSource,/\[CommGroup G\]/);assert.match(m.artinRepairSource,/closureCommGroupOfComm/);
 assert.ok(m.artinRepairSource.includes(m.artinTarget));assert.doesNotMatch(m.artinRepairSource,/sorry|admit|axiom /);
});
test('native Artin control requires rejected strong consumer, accepted original consumer and audited axioms',async()=>{
 const calls=[];const r=await m.qualifyArtin({publishedSource,run:async(name,source)=>{calls.push({name,source});return {code:name==='StrongConsumer'?1:0,output:name==='StrongConsumer'?'failed to synthesize CommGroup G':name==='RepairConsumer'?"'Artin_exercise_2_2_9' depends on axioms: [propext, Classical.choice, Quot.sound]":''};}});
 assert.equal(r.status,'ARTIN_CONTROLS_VERIFIED');assert.equal(calls.length,4);assert.deepEqual(r.axioms,['propext','Classical.choice','Quot.sound']);
});
test('Artin controls never pass on an accepted strong consumer, missing audit or sorry axiom',async()=>{
 for(const mode of ['strong-passes','missing-audit','sorry']){
  const r=await m.qualifyArtin({publishedSource,run:async name=>({code:name==='StrongConsumer'&&mode!=='strong-passes'?1:0,output:name==='StrongConsumer'?'failed to synthesize CommGroup G':name==='RepairConsumer'&&mode==='sorry'?"'Artin_exercise_2_2_9' depends on axioms: [sorryAx]":''})});assert.notEqual(r.status,'ARTIN_CONTROLS_VERIFIED');
 }
});

test('published declaration binding rejects changed bytes and a different local target',()=>{
 const bound=m.bindPublishedArtin(publishedSource);assert.equal(bound.source_sha256,'a9ea15e08b984edb0690348b953a11bf0a1c2cd2541131323c26c243f21ee7fc');assert.equal(bound.informal_equivalence,'NOT_CERTIFIED');
 assert.throws(()=>m.bindPublishedArtin(publishedSource+'\n'),/PUBLISHED_SOURCE_CHANGED/);
 assert.throws(()=>m.bindPublishedArtin(publishedSource,{target:m.artinTarget.replace('[Group G]','[CommGroup G]')}),/PUBLISHED_TARGET_MISMATCH/);
});
