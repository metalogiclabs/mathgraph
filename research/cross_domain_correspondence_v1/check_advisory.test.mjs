import test from "node:test";
import assert from "node:assert/strict";
import {advisory} from "./check_advisory.mjs";
const baseline={P1:"WARRANTED_BOUNDED",P2:"REJECTED_BOUNDED",P3:"UNKNOWN",
 Y1:"UNKNOWN",Y2:"REJECTED_BOUNDED",Y3:"UNKNOWN"};
const receipt={protocol_commit:"9c8b427c679398fd80ea56d9a91a1627b2e96b6d",
 mode:"authenticated archived native verifier replay + modeled dependency withdrawal",
 new_native_sources_executed:false,baseline};
const scope={sourceHead:"abc",expectedHead:"abc"};
test("bounded advisory is neutral",()=>{const r=advisory(receipt,scope);
 assert.equal(r.conclusion,"neutral");assert.equal(r.merge,"UNKNOWN");
 assert.deepEqual(r.verdicts,baseline)});
test("PKC withdrawal affects only dependent claims",()=>{const r=advisory(receipt,{...scope,withdrawn:["pkc-decl"]});
 assert.equal(r.verdicts.P1,"UNKNOWN_WITHDRAWN");
 assert.equal(r.verdicts.P2,"UNKNOWN_WITHDRAWN");
 assert.equal(r.verdicts.Y2,"REJECTED_BOUNDED")});
test("YAML withdrawal preserves PKC",()=>{const r=advisory(receipt,{...scope,withdrawn:["yaml-dump"]});
 assert.equal(r.verdicts.Y2,"UNKNOWN_WITHDRAWN");
 assert.equal(r.verdicts.P1,"WARRANTED_BOUNDED")});
test("restoring withdrawal returns baseline, not a native replay claim",()=>assert.deepEqual(advisory(receipt,scope).verdicts,baseline));
test("stale head fails closed",()=>assert.equal(advisory(receipt,{sourceHead:"old",expectedHead:"new"}).title,"EVIDENCE_UNKNOWN"));
test("wrong protocol fails closed",()=>assert.equal(advisory({...receipt,protocol_commit:"wrong"},scope).title,"EVIDENCE_UNKNOWN"));
test("unrecognized withdrawal fails closed",()=>assert.equal(advisory(receipt,{...scope,withdrawn:["unknown"]}).title,"EVIDENCE_UNKNOWN"));
test("missing receipt fails closed",()=>assert.equal(advisory(null,scope).title,"EVIDENCE_UNKNOWN"));
test("extra baseline claim fails closed",()=>assert.equal(advisory({...receipt,baseline:{...baseline,P4:"WARRANTED_BOUNDED"}},scope).title,"EVIDENCE_UNKNOWN"));
