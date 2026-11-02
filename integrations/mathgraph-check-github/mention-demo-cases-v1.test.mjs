import test from 'node:test';import assert from 'node:assert/strict';
const m=await import('./mention-demo-cases-v1.mjs').catch(()=>({}));
test('only one explicitly supported changed theorem selects a demo adapter',()=>{
 assert.equal(m.selectDemoCase([{filename:'mathgraph-demo/ReverseLength.lean'}]).id,'list-reversal');
 assert.equal(m.selectDemoCase([{filename:'mathgraph-demo/ArtinGenerators.lean'}]).id,'artin-generators');
 for(const files of [[],[{filename:'elsewhere.lean'}],[{filename:'mathgraph-demo/ReverseLength.lean'},{filename:'mathgraph-demo/ArtinGenerators.lean'}]])assert.throws(()=>m.selectDemoCase(files),/DEMO_CASE/);
});
test('Artin registered constructor preserves the published original target',()=>{
 const c=m.selectDemoCase([{filename:'mathgraph-demo/ArtinGenerators.lean'}]);assert.ok(c.accepts(c.brokenSource));assert.ok(c.accepts(c.repair));assert.equal(c.accepts('import Unsafe'),false);assert.ok(c.repair.includes(c.target));assert.match(c.target,/\[Group G\]/);assert.equal(c.needsMathlib,true);
});
