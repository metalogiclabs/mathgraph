import test from "node:test";
import assert from "node:assert/strict";
import {qualifySameHeadLifecycle as run} from "./same-head-ci-lifecycle-v1.mjs";
const sha="a".repeat(40),repository="metalogiclabs/go-ethereum";
const obs=(conclusion,attempt,id)=>({source_sha:sha,authenticated_receipt:"receipt-"+attempt,
 run_attempt:attempt,check_run_id:id,conclusion});
const fixture=()=>({repository,sha,observations:[obs("success",1,101),obs("pending",2,102),obs("success",3,102)],
 otherChecks:[{source_sha:sha,authenticated_receipt:"lint-receipt",conclusion:"success"}]});
test("same SHA native check history selectively withdraws and restores",()=>{
 const r=run(fixture());assert.equal(r.state,"OBSERVED");
 assert.deepEqual(r.history.slice(1).map(f=>f.claims.map(c=>c.status)),
 [["OBSERVED","OBSERVED"],["UNKNOWN","OBSERVED"],["OBSERVED","OBSERVED"]]);
 assert.equal(r.permission,"ADVISORY_ONLY");
});
test("pending run does not restore evidence",()=>{const f=fixture();f.observations.pop();assert.equal(run(f).claims.find(c=>c.id==="target").status,"UNKNOWN")});
test("failed rerun blocks only dependent claim",()=>{const f=fixture();f.observations[2].conclusion="failure";assert.deepEqual(run(f).claims.map(c=>c.status),["BLOCKED","OBSERVED"])});
test("wrong source rejected",()=>{const f=fixture();f.observations[1].source_sha="b".repeat(40);assert.equal(run(f).reason,"INVALID_AUTHENTICATED_RUN")});
test("regressed attempt rejected",()=>{const f=fixture();f.observations[2].run_attempt=1;assert.equal(run(f).reason,"NONMONOTONIC_REPLAY")});
test("unqualified other evidence rejected",()=>{const f=fixture();f.otherChecks[0].conclusion="pending";assert.equal(run(f).reason,"UNVERIFIED_INDEPENDENT_EVIDENCE")});
test("rejects an unrecorded run identifier",()=>{const f=fixture();f.observations[2].check_run_id=0;assert.equal(run(f).reason,"INVALID_AUTHENTICATED_RUN")});
