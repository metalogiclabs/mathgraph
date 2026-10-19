import test from "node:test";
import assert from "node:assert/strict";
import {gatePKCYamlPublication as gate} from "./pkc-yaml-publisher-gate.mjs";
const head="a".repeat(40);
const baseline={P1:"WARRANTED_BOUNDED",P2:"REJECTED_BOUNDED",P3:"UNKNOWN",Y1:"UNKNOWN",Y2:"REJECTED_BOUNDED",Y3:"UNKNOWN"};
const report={schema:"mathgraph.check.pkcyaml.shadow.v1",sourceHead:head,
 authority:"ARCHIVE_SHA256_VERIFIED_BY_WORKFLOW",liveAppCheck:false,
 merge:"UNKNOWN",authorization:"NONE",restoration:"UNKNOWN_NATIVE_REPLAY_REQUIRED",
 transfer:"UNKNOWN",advisory:{conclusion:"neutral",merge:"UNKNOWN",authorization:"NONE",verdicts:baseline},
 withdrawalTests:Object.fromEntries(["M1","M2","M3","M4"].map(k=>[k,{pass:true}]))};
const base={report,repo:"metalogiclabs/mathgraph",pr:171,head,liveHead:head,
 appId:5308912,installed:true,artifactAuthenticated:true,existingChecks:[]};
test("qualified exact head permits one neutral advisory",()=>{
 const r=gate(base);assert.equal(r.admitted,true);
 assert.equal(r.operation,"CREATE_ONE");assert.equal(r.check.conclusion,"neutral");
 assert.equal(r.authorization,"NONE")});
for(const [label,change] of [["wrong app",{appId:1}],["stale head",{liveHead:"b".repeat(40)}],
 ["unauthenticated",{artifactAuthenticated:false}],["not installed",{installed:false}],
 ["wrong repo",{repo:"other/repo"}]])test(label+" fails closed",()=>{
 assert.equal(gate({...base,...change}).admitted,false)});
test("existing App check reconciles instead of duplicating",()=>{
 const c={id:123,name:"MathGraph Check / evidence scope",app:{id:5308912},
 external_id:"metalogiclabs/mathgraph#171@"+head};
 const r=gate({...base,existingChecks:[c]});
 assert.equal(r.operation,"RECONCILE_EXISTING");assert.equal(r.existingCheckId,123)});
test("duplicate App identities reject",()=>{
 const c={id:123,name:"MathGraph Check / evidence scope",app:{id:5308912},
 external_id:"metalogiclabs/mathgraph#171@"+head};
 assert.equal(gate({...base,existingChecks:[c,{...c,id:124}]}).admitted,false)});
test("unsupported semantic promotion rejects",()=>{
 assert.equal(gate({...base,report:{...report,transfer:"WARRANTED"}}).admitted,false)});
