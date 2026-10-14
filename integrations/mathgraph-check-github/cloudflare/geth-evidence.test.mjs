import {test} from "node:test";
import assert from "node:assert/strict";
import {appendGethV19NativeEvidence as append,V19} from "../geth-v19-evidence.mjs";
const assessment={authority:"ADVISORY_ONLY",source:{repository:V19.repository,pr:V19.pr,sha:V19.sha},
  ci:{state:"GITHUB_REPORTED_SUCCESS_AT_EXACT_HEAD"}};
const check={name:"MathGraph Check / evidence scope",status:"completed",conclusion:"neutral",
  output:{title:"DECLARED_VERIFICATION_RESIDUAL",summary:"generic report: remote_conflicting_fcu=UNKNOWN"}};
function fx(o={}){
  let calls=[];
  const run={id:V19.run,status:"completed",conclusion:"success",head_sha:V19.sha,
    repository:{full_name:V19.repository},path:V19.workflow,event:"push",run_attempt:1};
  const artifact={id:V19.artifact,name:V19.artifactName,digest:V19.zipDigest,
    expired:false,workflow_run:{id:V19.run,head_sha:V19.sha}};
  const githubRead=async(path,t)=>{
    assert.equal(t,"test-installation-token");
    calls.push(path);
    if(o.unavailable) throw Error("GITHUB_HTTP_503");
    if(path.endsWith("/"+V19.run))return {...run,...o.run};
    if(path.endsWith("/artifacts?per_page=100"))return {
      total_count:1,artifacts:[{...artifact,...o.artifact}]};
    throw Error("UNEXPECTED_API_READ");
  };
  return {report:structuredClone(assessment),check:structuredClone(check),
    githubRead,token:"test-installation-token",calls};
}
test("native result is only an exact-source historical scope; Check remains neutral",async()=>{
 const f=fx(); const r=await append(f.report,f.check,f.githubRead,f.token);
 assert.equal(r.state,"WARRANTED_BOUNDED_HISTORICAL_NATIVE_ARTIFACT");
 assert.equal(r.check.conclusion,"neutral");
 assert.equal(r.check.output.title,"DECLARED_VERIFICATION_RESIDUAL");
 assert.match(r.check.output.summary,/concurrent_fcu.*UNKNOWN/);
 assert.match(r.check.output.summary,/remote_conflicting_fcu.*UNKNOWN/);
 assert.match(r.check.output.summary,/original source-pinned GitHub run/);
 assert.match(r.check.output.summary,/generic report/);
 assert.equal(f.calls.length,2);
});
test("no cross-PR evidence transport and no gratuitous API reads",async()=>{
 for(const source of [
   {...assessment.source,pr:18},
   {...assessment.source,sha:"f".repeat(40)},
   {repository:"teorth/IEANTN",pr:158,sha:"f".repeat(40)}
 ]){
   const f=fx();f.report.source=source;
   const r=await append(f.report,f.check,f.githubRead,f.token);
   assert.equal(r.state,"NOT_APPLICABLE");assert.deepEqual(r.check,check);
   assert.equal(f.calls.length,0);
 }
});
test("failed or modified original run cannot qualify native evidence",async()=>{
 for(const run of [
  {conclusion:"failure"},{head_sha:"f".repeat(40)},
  {path:".github/workflows/other.yml"},{run_attempt:2},
  {repository:{full_name:"attacker/other"}}
 ]) {
  const f=fx({run});const r=await append(f.report,f.check,f.githubRead,f.token);
  assert.equal(r.state,"UNKNOWN_NATIVE_RUN_IDENTITY_MISMATCH");
  assert.deepEqual(r.check,check);
 }
});
test("wrong artifact hash/expired/wrong run cannot qualify native evidence",async()=>{
 for(const artifact of [
  {digest:"sha256:"+"f".repeat(64)},{expired:true},
  {workflow_run:{id:1,head_sha:V19.sha}},
  {id:1234}
 ]){
  const f=fx({artifact});const r=await append(f.report,f.check,f.githubRead,f.token);
  assert.equal(r.state,"UNKNOWN_NATIVE_RUN_IDENTITY_MISMATCH");
  assert.deepEqual(r.check,check);
 }
});
test("unavailable GitHub provenance fails closed; no positive claim",async()=>{
 const f=fx({unavailable:true});
 const r=await append(f.report,f.check,f.githubRead,f.token);
 assert.equal(r.state,"UNKNOWN_NATIVE_RUN_READBACK_UNAVAILABLE");
 assert.deepEqual(r.check,check);
});
test("escalated Check authorizations are refused",async()=>{
 const f=fx();f.check.conclusion="success";
 await assert.rejects(append(f.report,f.check,f.githubRead,f.token),/FORBIDDEN_NATIVE_CHECK_AUTHORITY/);
 const g=fx();g.report.authority="WARRANTED";
 await assert.rejects(append(g.report,g.check,g.githubRead,g.token),/FORBIDDEN_NATIVE_CHECK_AUTHORITY/);
});
