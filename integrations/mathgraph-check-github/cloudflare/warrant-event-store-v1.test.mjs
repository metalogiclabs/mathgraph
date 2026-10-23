import test from "node:test";
import assert from "node:assert/strict";
import {recordWarrantEvent} from "./warrant-event-store-v1.mjs";
const sha="a".repeat(40);
const event=()=>({schema:"mathgraph.monitor.transition.v1",repository:"metalogiclabs/go-ethereum",pr:20,
 head_sha:sha,kind:"EVIDENCE_CHANGED",permission:"ADVISORY_ONLY",
 downstream_warrant_status:"REQUALIFICATION_REQUIRED",semantic_verification:"NOT_ESTABLISHED"});
function store(){const m=new Map();return {m,WARRANT_EVENTS:{
 async get(k){return m.has(k)?{text:async()=>m.get(k)}:null},
 async put(k,v){m.set(k,v)}
 }}}
test("durable write and same-key retry read back",async()=>{
 const s=store();const a=await recordWarrantEvent(s,event());
 const b=await recordWarrantEvent(s,event());
 assert.equal(a.state,"RECORDED");assert.equal(b.state,"EXISTING");
 assert.equal(a.key,b.key);assert.equal(s.m.size,1);
});
test("storage unconfigured fails closed",async()=>await assert.rejects(recordWarrantEvent({},event()),/NOT_CONFIGURED/));
test("foreign repository refused",async()=>{const e=event();e.repository="nasa-jpl/L4YAML";await assert.rejects(recordWarrantEvent(store(),e),/INVALID_WARRANT_EVENT/)});
test("authority escalation refused",async()=>{const e=event();e.permission="MERGE_APPROVED";await assert.rejects(recordWarrantEvent(store(),e),/INVALID_WARRANT_EVENT/)});
test("tampered existing object rejected",async()=>{
 const s=store();const a=await recordWarrantEvent(s,event());s.m.set(a.key,"bad");
 await assert.rejects(recordWarrantEvent(s,event()),/DIGEST_COLLISION/);
});
test("persisted data unavailable at readback fails closed",async()=>{
 const s={WARRANT_EVENTS:{get:async()=>null,put:async()=>{}}};
 await assert.rejects(recordWarrantEvent(s,event()),/READBACK_MISMATCH/);
});
