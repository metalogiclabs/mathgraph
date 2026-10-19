import test from "node:test";
import assert from "node:assert/strict";
import {checkArtifactBytes,extractBoundReport,qualifyLiveCheck,PIN} from "./pkc-yaml-live-boundary.mjs";
test("no ZIP bytes fails closed",()=>assert.equal(checkArtifactBytes(null,{}),false));
test("wrong ZIP digest fails closed",()=>assert.equal(checkArtifactBytes(new Uint8Array([1,2,3]),{
 id:PIN.artifact,digest:"sha256:"+PIN.digest,expired:false,workflow_run:{id:PIN.run}}),false));
test("unbound report cannot authorize live Check",()=>{
 const r=qualifyLiveCheck({zipBytes:new Uint8Array([1,2,3]),
  artifactMetadata:{id:PIN.artifact,digest:"sha256:"+PIN.digest,expired:false,workflow_run:{id:PIN.run}},
  parsedReport:{},repo:PIN.repo,pr:171,head:"a".repeat(40),liveHead:"a".repeat(40),
  appId:5308912,installed:true,existingChecks:[]});
 assert.equal(r.admitted,false);
 assert.equal(r.reason,"ARCHIVE_BYTES_NOT_AUTHENTICATED");
});

test("truncated archive cannot produce report",()=>{
 assert.throws(()=>extractBoundReport(new Uint8Array([0x50,0x4b,0x05,0x06])));
});
test("random ZIP bytes cannot produce report",()=>{
 assert.throws(()=>extractBoundReport(new Uint8Array(128)));
});
