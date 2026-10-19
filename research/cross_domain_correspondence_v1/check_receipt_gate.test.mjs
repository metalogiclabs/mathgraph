import test from "node:test";
import assert from "node:assert/strict";
import {qualifiedAdvisory,AUTHORITY} from "./check_receipt_gate.mjs";
const run={id:AUTHORITY.run,head_sha:AUTHORITY.head,status:"completed",
 conclusion:"success",repository:{full_name:AUTHORITY.repo}};
const artifact={id:AUTHORITY.artifact,name:AUTHORITY.name,expired:false,
 digest:AUTHORITY.digest,workflow_run:{id:AUTHORITY.run,head_sha:AUTHORITY.head}};
const read=async path=>path.includes("/artifacts/")?artifact:run;
test("metadata alone never promotes native claims",async()=>{
 const r=await qualifiedAdvisory({githubRead:read,carrierHead:AUTHORITY.head,
 receipt:{archive_authenticated:true}});
 assert.equal(r.state,"UNKNOWN");assert.equal(r.check.conclusion,"neutral");
 assert.match(r.check.summary,/archive-byte verification not wired/);
});
test("stale source fails closed",async()=>{
 const r=await qualifiedAdvisory({githubRead:read,carrierHead:"old"});
 assert.equal(r.state,"UNKNOWN")});
test("wrong archive digest fails closed",async()=>{
 const r=await qualifiedAdvisory({githubRead:async p=>p.includes("/artifacts/")?
 {...artifact,digest:"sha256:wrong"}:run,carrierHead:AUTHORITY.head});
 assert.equal(r.state,"UNKNOWN");assert.match(r.check.summary,/archive authority mismatch/);
});
test("missing GitHub reader fails closed",async()=>{
 const r=await qualifiedAdvisory({carrierHead:AUTHORITY.head});
 assert.equal(r.state,"UNKNOWN")});
