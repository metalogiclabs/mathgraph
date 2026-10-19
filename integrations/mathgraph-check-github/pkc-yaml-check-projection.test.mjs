import test from "node:test";
import assert from "node:assert/strict";
import {projectPKCYamlCheck as project} from "./pkc-yaml-check-projection.mjs";
const head="a".repeat(40);
const scope={carrierRepo:"metalogiclabs/mathgraph",carrierHead:head,authorized:true};
const verdicts={P1:"WARRANTED_BOUNDED",P2:"REJECTED_BOUNDED",P3:"UNKNOWN",
 Y1:"UNKNOWN",Y2:"REJECTED_BOUNDED",Y3:"UNKNOWN"};
const report={schema:"mathgraph.check.pkcyaml.shadow.v1",sourceHead:head,
 authority:"ARCHIVE_SHA256_VERIFIED_BY_WORKFLOW",liveAppCheck:false,merge:"UNKNOWN",
 authorization:"NONE",restoration:"UNKNOWN_NATIVE_REPLAY_REQUIRED",transfer:"UNKNOWN",
 advisory:{conclusion:"neutral",merge:"UNKNOWN",authorization:"NONE",verdicts},
 withdrawalTests:Object.fromEntries(["M1","M2","M3","M4"].map(k=>[k,{pass:true}]))};
test("qualified report projects neutral bounded advisory",()=>{
 const x=project(report,scope);assert.equal(x.conclusion,"neutral");
 assert.equal(x.output.title,"PKC_L4YAML_HISTORICAL_RESEARCH_BOUNDED");
 assert.match(x.output.summary,/General transfer: UNKNOWN/);
});
for(const [name,changes] of [
 ["unapproved",{authorized:false}],["wrong carrier",{carrierRepo:"other/repo"}],
 ["stale head",{carrierHead:"b".repeat(40)}]])test(name+" fails closed",()=>{
 assert.equal(project(report,{...scope,...changes}).output.title,"PKC_L4YAML_EVIDENCE_UNKNOWN");
});
test("promoted unknown claim fails closed",()=>assert.equal(
 project({...report,advisory:{...report.advisory,verdicts:{...verdicts,Y1:"WARRANTED_BOUNDED"}}},scope).output.title,
 "PKC_L4YAML_EVIDENCE_UNKNOWN"));
test("missing withdrawal fails closed",()=>assert.equal(
 project({...report,withdrawalTests:{M1:{pass:true}}},scope).output.title,
 "PKC_L4YAML_EVIDENCE_UNKNOWN"));
test("merge authority forbidden",()=>assert.equal(
 project({...report,merge:"SAFE"},scope).output.title,"PKC_L4YAML_EVIDENCE_UNKNOWN"));
