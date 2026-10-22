import test from "node:test";
import assert from "node:assert/strict";
import {check,resolve,monitor} from "./check-resolve-monitor-v1.mjs";
const sha=x=>x.repeat(40);
const subject={repository:"metalogiclabs/mathgraph",pr:194,head_sha:sha("a")};
function report(statuses=["OBSERVED","OBSERVED"],opts={}) {
 return {subject:{...subject,...opts.subject},results:statuses.map((status,i)=>({id:"c"+i,status})),
 claim_dependencies:[{id:"c0",requires:["e0"]},{id:"c1",requires:["e1"]}],...opts};
}
test("product CHECK refuses unsupported scope",()=>assert.equal(check({},{}).status,"UNKNOWN"));
test("RESOLVE selects cheapest permitted and source-authoritative plan",()=>{
 const r=resolve(report(["UNKNOWN"]),{c0:[{id:"unsafe",cost:0,allowed:false,source_authoritative:true},{id:"guess",cost:1,allowed:true},{id:"native",cost:3,allowed:true,source_authoritative:true}]});
 assert.equal(r[0].next.experiment,"native");assert.equal(r[0].next.kind,"PROPOSAL_NOT_EXECUTED");
});
test("RESOLVE does not invent a plan",()=>assert.equal(resolve(report(["UNKNOWN"]),{})[0].next,null));
test("MONITOR retains unaffected warranted observation",()=>{
 const r=monitor(report(),report(["UNKNOWN","OBSERVED"]),{changedEvidenceIds:["e0"]});
 assert.deepEqual(r.transitions.map(x=>x.to),["UNKNOWN","OBSERVED"]);
});
test("MONITOR refuses unqualified restored evidence",()=>{
 const r=monitor(report(["UNKNOWN","OBSERVED"]),report(),{changedEvidenceIds:["e0"]});
 assert.equal(r.transitions[0].to,"UNKNOWN");assert.equal(r.transitions[1].to,"OBSERVED");
});
test("MONITOR admits explicit requalification without certifying it",()=>{
 const r=monitor(report(["UNKNOWN","OBSERVED"]),report(["OBSERVED","OBSERVED"],{independent_requalification:true}),{changedEvidenceIds:["e0"]});
 assert.equal(r.transitions[0].to,"OBSERVED");assert.equal(r.permission,"ADVISORY_ONLY");
});
test("MONITOR invalidates when exact head changes",()=>{
 const r=monitor(report(),report(["OBSERVED","OBSERVED"],{subject:{head_sha:sha("b")}}));
 assert.deepEqual(r.transitions.map(x=>x.to),["UNKNOWN","UNKNOWN"]);
});
test("MONITOR refuses subject replacement",()=>{
 const r=monitor(report(),report(["OBSERVED","OBSERVED"],{subject:{repository:"nasa-jpl/L4YAML"}}));
 assert.equal(r.status,"UNKNOWN");assert.equal(r.reason,"SUBJECT_CHANGED");
});
test("MONITOR forbids carry-over without dependency provenance",()=>{
 const p=report();p.claim_dependencies=[];
 const r=monitor(p,p);assert.equal(r.transitions[0].to,"UNKNOWN");
});
