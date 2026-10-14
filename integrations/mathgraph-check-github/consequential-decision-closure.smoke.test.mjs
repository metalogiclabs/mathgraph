import test from "node:test";
import assert from "node:assert/strict";
import {VERSION,ROOTS,decide,reclose} from "./consequential-decision-closure.mjs";

test("dual-source historical decision module is importable without secrets or network",()=>{
 assert.equal(VERSION,"mathgraph.check.decision-closure.v1");
 assert.equal(Object.keys(ROOTS).length,2);
 assert.equal(ROOTS.yaml.subject.repository,"goccy/go-yaml");
 assert.equal(ROOTS.gimmes.subject.repository,"allan-mobley-jr/gimmes");
});
test("both original subjects refuse unbound evidence",()=>{
 for(const type of Object.keys(ROOTS)){
   const r=decide(type,{subject:{...ROOTS[type].subject}});
   assert.equal(r.status,"UNKNOWN_EVIDENCE_NOT_QUALIFIED");
   assert.equal(r.authorization,"NONE");
   assert.equal(r.merge,"UNKNOWN");
 }
});
test("changed exact original head cannot reuse historical certificate",()=>{
 for(const type of Object.keys(ROOTS)){
   const r=decide(type,{subject:{...ROOTS[type].subject,head:"0".repeat(40)}});
   assert.equal(r.status,"STALE_SOURCE_HEAD");
   assert.equal(r.claims.length,0);
 }
});
test("untrusted subject and unknown operation cannot claim verified output",()=>{
 assert.equal(decide("yaml",{subject:{...ROOTS.gimmes.subject}}).status,"UNKNOWN_WRONG_SUBJECT");
 assert.equal(decide("bogus",{subject:ROOTS.yaml.subject}).status,"UNKNOWN_UNRECOGNIZED_CAPABILITY");
});
test("one withdrawn source does not force unrelated subject to be treated as withdrawn",()=>{
 const a=reclose([
  {id:"yaml",root:"yaml",input:{subject:{...ROOTS.yaml.subject},withdrawn:true}},
  {id:"python",root:"gimmes",input:{subject:{...ROOTS.gimmes.subject}}}
 ]);
 assert.equal(a.states[0].status,"STALE_SUPPORT_WITHDRAWN");
 assert.equal(a.states[1].status,"UNKNOWN_EVIDENCE_NOT_QUALIFIED");
 assert.equal(a.merge_authority,"UNKNOWN");
 assert.equal(a.autonomous_action,"NONE");
});
test("original qualified scientific assertions remain bounded outside this isolated importer",()=>{
 for(const type of Object.keys(ROOTS)){
  const p=ROOTS[type];
  assert(p.runs.every(([id,sha,path])=>Number.isSafeInteger(id)&&
   /^[0-9a-f]{40}$/.test(sha)&&path.startsWith(".github/workflows/")));
 }
});
