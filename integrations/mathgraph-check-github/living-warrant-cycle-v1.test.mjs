import test from "node:test";
import assert from "node:assert/strict";
import {replayLifecycle} from "./living-warrant-cycle-v1.mjs";
const sha="a".repeat(40);
const input=()=>({source:{repository:"metalogiclabs/go-ethereum",sha},
 claims:[{id:"A",requires:["native"]},{id:"B",requires:["separate"]}],
 authenticatedReceipts:["r1","r2","r3","r4","r5","r6"],
 events:[
  {type:"OBSERVE",id:"native",generation:1,source_sha:sha,receipt_id:"r1",conclusion:"success"},
  {type:"OBSERVE",id:"separate",generation:1,source_sha:sha,receipt_id:"r2",conclusion:"success"},
  {type:"WITHDRAW",id:"native",generation:2,source_sha:sha,receipt_id:"r3"},
  {type:"OBSERVE",id:"native",generation:3,source_sha:sha,receipt_id:"r4",conclusion:"pending"},
  {type:"OBSERVE",id:"native",generation:4,source_sha:sha,receipt_id:"r5",conclusion:"success"}
 ]});
test("bounded success -> withdrawal -> pending -> requalification is selective",()=>{
 const r=replayLifecycle(input());
 assert.deepEqual(r.history.map(h=>h.claims.map(c=>c.status)),[
 ["OBSERVED","UNKNOWN"],["OBSERVED","OBSERVED"],["UNKNOWN","OBSERVED"],
 ["UNKNOWN","OBSERVED"],["OBSERVED","OBSERVED"]]);
 assert.equal(r.permission,"ADVISORY_ONLY");
});
test("withdrawal does not invent restoration",()=>{const f=input();f.events.pop();const r=replayLifecycle(f);assert.equal(r.claims[0].status,"UNKNOWN")});
test("failure only blocks dependent claim",()=>{const f=input();f.events[3].conclusion="failure";f.events.pop();const r=replayLifecycle(f);assert.deepEqual(r.claims.map(x=>x.status),["BLOCKED","OBSERVED"])});
test("unauthenticated restoration rejected",()=>{const f=input();f.authenticatedReceipts.pop();f.events[4].receipt_id="r6";assert.equal(replayLifecycle(f).reason,"UNAUTHENTICATED_TRANSITION")});
test("replayed same generation refused",()=>{const f=input();f.events[4].generation=2;assert.equal(replayLifecycle(f).reason,"NON_MONOTONIC_EVIDENCE_GENERATION")});
test("foreign SHA cannot restore claim",()=>{const f=input();f.events[4].source_sha="b".repeat(40);assert.equal(replayLifecycle(f).reason,"WRONG_HEAD_TRANSITION")});
test("fabricated verdict refused",()=>{const f=input();f.events[4].conclusion="proven";assert.equal(replayLifecycle(f).reason,"INVALID_CONCLUSION")});
test("empty dependencies refused",()=>{const f=input();f.claims[0].requires=[];assert.equal(replayLifecycle(f).reason,"BAD_CLAIM_DEPENDENCIES")});
test("missing evidence keeps relevant claims unknown",()=>{const f=input();f.events=[];const r=replayLifecycle(f);assert.equal(r.state,"UNKNOWN")});
test("unrelated evidence cannot authorize absent dependent witness",()=>{const f=input();f.events=f.events.filter(x=>x.id==="separate");const r=replayLifecycle(f);assert.deepEqual(r.claims.map(x=>x.status),["UNKNOWN","OBSERVED"])});
