import test from "node:test";
import assert from "node:assert/strict";
import {transitionReceipt} from "./monitor-transition-v1.mjs";
const sha="a".repeat(40),repo="metalogiclabs/go-ethereum";
const check=(summary="same")=>({head_sha:sha,output:{title:"MathGraph Check: UNKNOWN",summary}});
const args={repository:repo,pr:19,headSha:sha,currentCheck:check()};
test("first observation never claims semantic warrant",()=>{
 const r=transitionReceipt(args);assert.equal(r.kind,"FIRST_OBSERVATION");
 assert.equal(r.permission,"ADVISORY_ONLY");assert.equal(r.semantic_verification,"NOT_ESTABLISHED");
});
test("current same-head evidence retains informational status",()=>{
 const r=transitionReceipt({...args,previousCheck:check()});
 assert.equal(r.kind,"EVIDENCE_UNCHANGED");assert.equal(r.downstream_warrant_status,"NOT_EVALUATED");
});
test("changed evidence requires downstream requalification",()=>{
 const r=transitionReceipt({...args,previousCheck:check("old"),currentCheck:check("new")});
 assert.equal(r.kind,"EVIDENCE_CHANGED");assert.equal(r.downstream_warrant_status,"REQUALIFICATION_REQUIRED");
});
test("stale previous head rejected",()=>assert.throws(()=>transitionReceipt({...args,previousCheck:{...check(),head_sha:"b".repeat(40)}}),/STALE/));
test("incomplete next evidence rejected",()=>assert.throws(()=>transitionReceipt({...args,currentCheck:{}}),/INCOMPLETE/));
test("changed PR identity rejected",()=>assert.throws(()=>transitionReceipt({...args,pr:0}),/INVALID/));
