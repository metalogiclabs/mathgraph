import test from 'node:test';
import assert from 'node:assert/strict';
import {hashFiniteUniverse,checkFiniteWarrantQuotient} from './finite-warrant-quotient-v1.mjs';
const a='a'.repeat(40),b='b'.repeat(40);
function example(rows){
 const table={schema:'mathgraph.finite-warrant-quotient.v1',scope:'synthetic-intent-gap',
  rows};
 const policy={expectedUniverseSha256:hashFiniteUniverse(table),allowedSourceShas:[a,b]};
 return {table,policy};
}
test('same green CI but different intent verdict produces a concrete finite collision',()=>{
 const x=example([
  {id:'agent-done',source_sha:a,alpha_key:'ci:green',protected_status:'OBSERVED'},
  {id:'agent-wrong',source_sha:a,alpha_key:'ci:green',protected_status:'BLOCKED'}
 ]);
 const r=checkFiniteWarrantQuotient(x.table,x.policy);
 assert.equal(r.status,'FINITE_COUNTEREXAMPLE');
 assert.deepEqual([r.witness.left.id,r.witness.right.id],['agent-done','agent-wrong']);
 assert.equal(r.witness.alpha_key,'ci:green');
 assert.equal(r.universal_preservation,'NOT_ESTABLISHED');
});
test('same status on different commits cannot be silently carried over',()=>{
 const x=example([
  {id:'a',source_sha:a,alpha_key:'passed',protected_status:'OBSERVED'},
  {id:'b',source_sha:b,alpha_key:'passed',protected_status:'OBSERVED'}
 ]);
 assert.equal(checkFiniteWarrantQuotient(x.table,x.policy).status,'FINITE_COUNTEREXAMPLE');
});
test('merging only equivalent finite decisions is permitted within enumerated scope',()=>{
 const x=example([
  {id:'a',source_sha:a,alpha_key:'pass',protected_status:'OBSERVED'},
  {id:'b',source_sha:a,alpha_key:'pass',protected_status:'OBSERVED'},
  {id:'c',source_sha:a,alpha_key:'missing',protected_status:'UNKNOWN'}
 ]);
 const r=checkFiniteWarrantQuotient(x.table,x.policy);
 assert.equal(r.status,'FINITE_PRESERVED');
 assert.equal(r.checked_states,3);
 assert.equal(r.compared_merges,1);
 assert.equal(r.permission,'ADVISORY_ONLY');
 assert.equal(r.universal_preservation,'NOT_ESTABLISHED');
});
test('self-reported success and edited source tables never authenticate themselves',()=>{
 const x=example([
  {id:'a',source_sha:a,alpha_key:'x',protected_status:'OBSERVED'},
  {id:'b',source_sha:a,alpha_key:'x',protected_status:'OBSERVED'}
 ]);
 assert.equal(checkFiniteWarrantQuotient(x.table).status,'UNKNOWN');
 x.table.rows[1].protected_status='BLOCKED';
 assert.equal(checkFiniteWarrantQuotient(x.table,x.policy).status,'UNKNOWN');
});
test('empty, duplicate and malformed finite universes return UNKNOWN',()=>{
 const x=example([
  {id:'a',source_sha:a,alpha_key:'x',protected_status:'UNKNOWN'},
  {id:'a',source_sha:a,alpha_key:'x',protected_status:'BLOCKED'}
 ]);
 assert.equal(checkFiniteWarrantQuotient(x.table,x.policy).status,'UNKNOWN');
 const y=example([]);
 assert.equal(checkFiniteWarrantQuotient(y.table,y.policy).status,'UNKNOWN');
});
