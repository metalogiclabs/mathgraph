import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";
import {appendExternalNativeReceipt, pinnedJSON, EVIDENCE}
  from "../external-native-receipt.mjs";

const dir=join(dirname(fileURLToPath(import.meta.url)),"../fixtures");
const manifest=readFileSync(join(dir,"external-native-evidence.v1.json"),"utf8");
const reportBody=readFileSync(join(dir,"one-finding-report.v1.json"),"utf8");
const SHA="a".repeat(40);
function blobHash(s){
 const b=Buffer.from(s,"utf8");
 return createHash("sha1").update("blob "+b.length+"\0").update(b).digest("hex");
}
function githubFile(text,sha){
 return {sha,encoding:"base64",content:Buffer.from(text).toString("base64")};
}
const baseReport=()=>({authority:"ADVISORY_ONLY",source:{
  repository:EVIDENCE.carrier,pr:21,sha:SHA
}});
const baseCheck=()=>({
  name:"MathGraph Check / evidence scope",
  status:"completed",conclusion:"neutral",
  output:{title:"BEHAVIORAL_SCOPE_UNKNOWN",
    summary:"Generic exact Ethereum PR head. CI is not a correctness proof."}
});
const baseSnapshot=()=>({
  repository:EVIDENCE.carrier,number:21,sha:SHA,
  files_visibility:"COMPLETE",
  files:EVIDENCE.carrierFiles.map(filename=>({filename,status:"added"}))
});
function fixture(options={}){
 const calls=[], external=[];
 const githubRead=async(path,token)=>{
  assert.equal(token,"short-lived-installation-token");
  assert.equal(path,"/repos/"+EVIDENCE.carrier+
    "/contents/"+EVIDENCE.manifest+"?ref="+SHA);
  calls.push(path);
  return githubFile(options.manifestText??manifest,
    options.manifestSha??EVIDENCE.manifestBlob);
 };
 const fetcher=async(uri,init)=>{
  const url=new URL(uri);
  assert.equal(url.origin,"https://api.github.com");
  assert.equal(init.method,"GET");
  // An installation-scoped token is sent only to api.github.com for the
  // exact allowlisted, user-owned research repository's public metadata.
  assert.equal(init.headers.Authorization,"Bearer short-lived-installation-token");
  external.push(url.pathname+url.search);
  if(options.status403) return new Response("rate limited",{status:403});
  const reportPath="/repos/"+EVIDENCE.reporter+"/contents/"+EVIDENCE.reportPath;
  if(url.pathname===reportPath){
    return new Response(JSON.stringify(githubFile(options.reportText??reportBody,
      options.reportSha??EVIDENCE.reportBlob)),{status:200});
  }
  const prefix="/repos/"+EVIDENCE.reporter+"/actions/runs/";
  assert.ok(url.pathname.startsWith(prefix));
  const id=Number(url.pathname.slice(prefix.length).split("/")[0]);
  const which=EVIDENCE.runs.find(r=>r.id===id);
  assert.ok(which);
  if(url.pathname.endsWith("/artifacts")){
    return new Response(JSON.stringify({
      total_count:1,artifacts:[{
        id:which.artifact,name:which.name,expired:false,
        digest:options.wrongDigest ? "sha256:"+"f".repeat(64):which.digest,
        workflow_run:{id:which.id,head_sha:which.head}
      }]
    }),{status:200});
  }
  return new Response(JSON.stringify({
    id:which.id,head_sha:options.wrongSourceSHA?"e".repeat(40):which.head,
    repository:{full_name:EVIDENCE.reporter},
    status:"completed",conclusion:options.failedRun?"failure":"success",
    path:which.path,event:"push",run_attempt:1
  }),{status:200});
 };
 const run=async (snapshot=baseSnapshot(),check=baseCheck())=>
  appendExternalNativeReceipt(baseReport(),check,githubRead,
    "short-lived-installation-token",snapshot,{fetcher});
 return {calls,external,githubRead,fetcher,run};
}
test("fixture blobs match exact GitHub source pins",()=>{
 assert.equal(blobHash(manifest),EVIDENCE.manifestBlob);
 assert.equal(blobHash(reportBody),EVIDENCE.reportBlob);
 assert.equal(pinnedJSON(githubFile(manifest,EVIDENCE.manifestBlob),EVIDENCE.manifestBlob).schema,
  "mathgraph.external-native-evidence.v1");
});
test("one subject-correct native finding: 3 pinned runs, 2 archives, no merge authority",async()=>{
 const f=fixture();
 const result=await f.run();
 assert.equal(result.state,"WARRANTED_BOUNDED_EXTERNAL_NATIVE_METADATA_RECHECKED");
 assert.equal(f.calls.length,1);
 assert.equal(f.external.length,6); // 3 run + 2 artifact + 1 report
 assert.equal(result.subject,"goccy/go-yaml");
 assert.equal(result.sourceSha,EVIDENCE.subjectHead);
 assert.equal(result.carrierSha,SHA);
 assert.equal(result.check.output.title,"EXTERNAL_NATIVE_ONE_FINDING_BOUNDED");
 assert.equal(result.check.conclusion,"neutral");
 assert.match(result.check.output.summary,/NOT this Ethereum/);
 assert.match(result.check.output.summary,/69 of 130/);
 assert.match(result.check.output.summary,/issue #872/);
 assert.match(result.check.output.summary,/did NOT rerun Go tests/);
 assert.match(result.check.output.summary,/Generic exact Ethereum PR head/);
});
test("unrelated PR never reads external source or changes generic Check",async()=>{
 const f=fixture();
 const snap=baseSnapshot();
 snap.files=[{filename:"core/types/transaction.go"}];
 const check=baseCheck();
 const r=await f.run(snap,check);
 assert.equal(r.state,"NOT_APPLICABLE");
 assert.equal(r.check,check);
 assert.equal(f.calls.length,0);
 assert.equal(f.external.length,0);
});
test("changed carrier Go source or incomplete changed-file window fails closed",async()=>{
 for(const setup of [
  s=>s.files.push({filename:"core/txpool.go"}),
  s=>s.files_visibility="TRUNCATED_AT_300",
  s=>s.sha="b".repeat(40)
 ]){
  const f=fixture(),s=baseSnapshot();
  setup(s);
  const r=await f.run(s);
  assert.equal(r.check.output.title,"EXTERNAL_RECEIPT_UNKNOWN");
  assert.equal(r.check.conclusion,"neutral");
  assert.equal(r.state,"CARRIER_SOURCE_SCOPE_INCOMPLETE");
  assert.equal(f.calls.length,0);
 }
});
test("no authority for wrong manifest bytes even if claimed source blob looks right",async()=>{
 const f=fixture({manifestText:manifest.replace("author_pr_repairs", "hacked_repairs")});
 const r=await f.run();
 assert.equal(r.check.output.title,"EXTERNAL_RECEIPT_UNKNOWN");
 assert.equal(r.state,"SOURCE_BYTES_NOT_PINNED");
 assert.equal(f.external.length,0);
});
test("report Git blob or semantic source mismatch cannot be promoted",async()=>{
 for(const opts of [
  {reportSha:"b".repeat(40)},
  {reportText:reportBody.replace("introduced_case_count", "hacked_case_count")}
 ]){
  const f=fixture(opts),r=await f.run();
  assert.equal(r.check.conclusion,"neutral");
  assert.equal(r.check.output.title,"EXTERNAL_RECEIPT_UNKNOWN");
  assert.equal(f.external.length,1);
 }
});
test("stale run, failed run, changed artifact digest, or 403 refuses native warrant",async()=>{
 for(const opts of [
  {wrongSourceSHA:true},{failedRun:true},{wrongDigest:true},{status403:true}
 ]){
  const f=fixture(opts),r=await f.run();
  assert.equal(r.check.output.title,"EXTERNAL_RECEIPT_UNKNOWN");
  assert.equal(r.check.conclusion,"neutral");
  assert.ok(r.state!=="WARRANTED_BOUNDED_EXTERNAL_NATIVE_METADATA_RECHECKED");
  assert.match(r.check.output.summary,/retain|UNKNOWN|could not|could not be/);
 }
});
test("no dynamic GitHub API proxy; only exact allowlisted GitHub research-read paths",async()=>{
 const f=fixture();
 await f.run();
 assert.deepEqual([...new Set(f.external)].sort(),
  [
   ...EVIDENCE.runs.flatMap(pin=>[
      "/repos/"+EVIDENCE.reporter+"/actions/runs/"+pin.id,
      ...(pin.artifact?["/repos/"+EVIDENCE.reporter+"/actions/runs/"+
        pin.id+"/artifacts?per_page=100"]:[])
   ]),
   "/repos/"+EVIDENCE.reporter+"/contents/"+EVIDENCE.reportPath+
     "?ref="+EVIDENCE.reportCommit
  ].sort());
});
