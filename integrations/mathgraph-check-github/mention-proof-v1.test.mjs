import test from 'node:test';
import assert from 'node:assert/strict';
const m=await import('./mention-proof-v1.mjs').catch(()=>({}));
const head='a'.repeat(40),repo='metalogiclabs/mathgraph';
const snapshot={repository:repo,number:228,sha:head};
const manifest={repository:repo,pr:228,runId:100,trusted:{headSha:head}};
const collected={schema:'mathgraph.artin-environment-correlation.v1',status:'ENVIRONMENT_AND_REPLAY_CORRELATED',permission:'ADVISORY_ONLY',intent_verification:'NOT_ESTABLISHED',conclusion:'neutral',subject:{repository:repo,pr:228,head_sha:head},replay:{status:'PINNED_REPLAY_OBSERVED',run_id:100,run_attempt:1,artifact_id:200},environment_artifact_id:201};
test('proof observer module is available',()=>assert.equal(typeof m.proofObserver,'function'));
test('only administrator-pinned exact subject can invoke native collector',async()=>{
 let calls=0;const observe=m.proofObserver({manifests:[manifest],token:'fixture-token',collect:async()=>{calls++;return collected;}});
 assert.equal((await observe({...snapshot,sha:'b'.repeat(40)})).status,'NOT_CONFIGURED_FOR_SOURCE');assert.equal(calls,0);
 const r=await observe(snapshot);assert.equal(calls,1);assert.equal(r.status,'NATIVE_REPLAY_OBSERVED');assert.equal(r.theorem,'Artin_exercise_2_2_9');assert.equal(r.meaning,'UNVERIFIED');assert.equal(r.run_url,'https://github.com/'+repo+'/actions/runs/100');
});
test('wrong subject, run, expiry result and unqualified collector cannot promote',async()=>{
 for(const changed of [{...collected,subject:{...collected.subject,head_sha:'b'.repeat(40)}},{...collected,replay:{...collected.replay,run_id:101}},{...collected,status:'UNKNOWN'},{...collected,intent_verification:'VERIFIED'},{...collected,conclusion:'success'}]){
 const observe=m.proofObserver({manifests:[manifest],token:'fixture-token',collect:async()=>changed});assert.equal((await observe(snapshot)).status,'UNKNOWN');
 }
});
test('duplicate admin manifests are ambiguous and fail closed',async()=>{
 const observe=m.proofObserver({manifests:[manifest,manifest],token:'fixture-token',collect:async()=>{throw Error('must not execute');}});assert.equal((await observe(snapshot)).status,'UNKNOWN');
});
test('native transport failure remains unknown',async()=>{
 const observe=m.proofObserver({manifests:[manifest],token:'fixture-token',collect:async()=>{throw Error('secret');}});assert.deepEqual(await observe(snapshot),{status:'UNKNOWN',meaning:'UNVERIFIED'});
});
