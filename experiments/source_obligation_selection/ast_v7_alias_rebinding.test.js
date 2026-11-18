'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict');
const {scan:v7}=require('./mathgraph_ast_obligations_v7');
const {scan:v6}=require('./mathgraph_ast_obligations_v6');
test('local miss-path reassignment is not cache mutation',()=>{
 const s=`export function sub(cache,input){const key=input.replaceAll(' ','');let substitutionInfo=cache.get(key);if(substitutionInfo)return substitutionInfo;substitutionInfo={css:input};cache.set(key,substitutionInfo);return substitutionInfo;}`;
 const a=v6(s).hotspots[0],b=v7(s).hotspots[0];
 assert.equal(a.consumer_demand.classification,'SHARED_EFFECT_RELIANCE');
 assert.equal(b.consumer_demand.classification,'EXPOSED_VALUE_UNKNOWN');
 assert.equal(b.score,b.v5_score);
 assert.ok(b.consumer_demand.evidence.some(e=>e.kind==='LOCAL_REASSIGNMENT'));
 assert.equal(b.contract,'UNKNOWN');
});
test('cache entry property mutation remains shared effect',()=>{
 const s=`class Foo{f(x){const k=x%3;let old=this.cache[k];if(!old)this.cache[k]={value:1};if(old)old.value=x;return old;}}`;
 const a=v7(s).hotspots[0];assert.equal(a.consumer_demand.classification,'SHARED_EFFECT_RELIANCE');assert.equal(a.score,a.v5_score+20);
});
test('callbacks mutation stays high priority',()=>{
 const s=`class X{f(x,cb){const k=x%11;let old=this.cache[k];if(!old)old=this.cache[k]={callbacks:[]};old.callbacks.push(cb);return old;}}`;
 assert.equal(v7(s).hotspots[0].consumer_demand.classification,'SHARED_EFFECT_RELIANCE');
});
test('local reassignment does not issue a warranted defect',()=>{
 const s=`function f(x){const k=x%2;let old=cache[k];if(!old)old=cache[k]={x};return old;}`;
 const h=v7(s).hotspots[0];assert.equal(h.consumer_demand.classification,'EXPOSED_VALUE_UNKNOWN');assert.equal(h.judgment,'CANDIDATE_ONLY');
});
test('v7 preserves v6 detection sites',()=>{
 const s=`function load(x){const k=Math.floor(x/128);const old=cache[k];if(!old)cache[k]={promise:doIt()};return cache[k];}function call(x){const a=load(x);return a.promise;}`;
 assert.deepEqual(v7(s).hotspots.map(x=>x.id),v6(s).hotspots.map(x=>x.id));
});
