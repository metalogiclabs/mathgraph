import test from "node:test";
import assert from "node:assert/strict";
import {requalifyFreshGitHubCI} from "./fresh-ci-requalification-v1.mjs";
const repo="metalogiclabs/mathgraph",pr=266,a="a".repeat(40),b="b".repeat(40);
const old={result:{subject:{repository:repo,pr,head_sha:a},independent_requalification:true}};
const args={repository:repo,pr,token:"test-token-long-enough",requiredChecks:["native-ci"],previous:old};
const run=(name="native-ci",status="completed",conclusion="success",sha=b,slug="github-actions")=>({
 id:13,name,head_sha:sha,status,conclusion,started_at:"2026-11-04T00:00:00Z",app:{slug}
});
async function withGitHubMock(runs,fn,{head=b,http=200}={}){
 const prev=globalThis.fetch,calls=[];
 globalThis.fetch=async (url,opts)=>{
  calls.push({url,auth:opts?.headers?.Authorization});
  if(http!==200)return {ok:false,status:http};
  return {ok:true,json:async()=>url.includes("/pulls/")?
   {base:{sha:a,repo:{full_name:repo}},head:{sha:head,repo:{full_name:repo}}}:
   {total_count:runs.length,check_runs:runs}};
 };
 try{return await fn(calls);}finally{globalThis.fetch=prev;}
}
test("live-style CI-only readback observes newly verified exact head, without permission",async()=>{
 await withGitHubMock([run()],async calls=>{
  const r=await requalifyFreshGitHubCI(args);
  assert.equal(r.status,"OBSERVED");
  assert.equal(r.changed_head,true);
  assert.equal(r.subject.head_sha,b);
  assert.equal(r.permission,"ADVISORY_ONLY");
  assert.equal(r.semantic_verification,"NOT_ESTABLISHED");
  assert.equal(r.checks[0].check_run_id,13);
  assert.equal(calls.length,2);
  assert.ok(calls.every(c=>c.auth==="Bearer "+args.token));
 });
});
test("caller-forged green and in-band requalification cannot override a pending API check",async()=>{
 await withGitHubMock([run("native-ci","in_progress","success")],async()=>{
  const r=await requalifyFreshGitHubCI({...args,previous:{...old,result:{...old.result,results:[{id:"native-ci",status:"OBSERVED"}]}},independent_requalification:true});
  assert.equal(r.status,"UNKNOWN");
  assert.equal(r.checks[0].reason,"CHECK_NOT_SUCCESSFUL_AND_COMPLETED");
 });
});
test("new head with failed independent check is blocked",async()=>{
 await withGitHubMock([run("native-ci","completed","failure")],async()=>{
  const r=await requalifyFreshGitHubCI(args);
  assert.equal(r.status,"BLOCKED");assert.equal(r.checks[0].status,"BLOCKED");
 });
});
test("successful unrelated check does not satisfy required check name",async()=>{
 await withGitHubMock([run("lint")],async()=>{
  const r=await requalifyFreshGitHubCI(args);
  assert.equal(r.status,"UNKNOWN");assert.equal(r.checks[0].reason,"NO_EXACT_HEAD_INDEPENDENT_CHECK");
 });
});
test("one pending required check blocks all-green conclusion",async()=>{
 await withGitHubMock([run(),{...run("safety"),id:14,status:"queued",conclusion:null}],async()=>{
  const r=await requalifyFreshGitHubCI({...args,requiredChecks:["native-ci","safety"]});
  assert.equal(r.status,"UNKNOWN");
  assert.deepEqual(r.checks.map(x=>x.status),["OBSERVED","UNKNOWN"]);
 });
});
test("fake check at different head cannot be used",async()=>{
 await withGitHubMock([run("native-ci","completed","success",a)],async()=>{
  await assert.rejects(requalifyFreshGitHubCI(args),/NO_INDEPENDENT_CHECKS/);
 });
});
test("MathGraph's own check cannot self-certify",async()=>{
 await withGitHubMock([run("native-ci","completed","success",b,"mathgraph-check")],async()=>{
  await assert.rejects(requalifyFreshGitHubCI(args),/NO_INDEPENDENT_CHECKS/);
 });
});
test("GitHub API denial fails closed",async()=>{
 await withGitHubMock([],async()=>{
  await assert.rejects(requalifyFreshGitHubCI(args),/GITHUB_HTTP_403/);
 },{http:403});
});
test("wrong previous subject is refused before external access",async()=>{
 await withGitHubMock([run()],async calls=>{
  const r=await requalifyFreshGitHubCI({...args,previous:{result:{subject:{repository:"other/repo",pr,head_sha:a}}}});
  assert.equal(r.status,"UNKNOWN");assert.equal(r.reason,"PREVIOUS_SUBJECT_MISMATCH");
  assert.equal(calls.length,0);
 });
});
test("missing, duplicate and invalid check requirements are refused",async()=>{
 await withGitHubMock([run()],async calls=>{
  for(const requiredChecks of [[],["native-ci","native-ci"],["\";process.exit(0)"],[123]]){
    const r=await requalifyFreshGitHubCI({...args,requiredChecks});
    assert.equal(r.status,"UNKNOWN");assert.equal(r.reason,"INVALID_FRESH_READBACK_REQUEST");
  }
  assert.equal(calls.length,0);
 });
});
test("exact same head can be independently checked without invented source change",async()=>{
 await withGitHubMock([run()],async()=>{
  const r=await requalifyFreshGitHubCI({...args,previous:{result:{subject:{repository:repo,pr,head_sha:b}}}});
  assert.equal(r.status,"OBSERVED");assert.equal(r.changed_head,false);
 });
});
test("real GitHub matrix check names containing commas are valid exact names",async()=>{
 const name="test-rust / test-rust (ubuntu-latest, stable)";
 await withGitHubMock([run(name)],async()=>{
  const r=await requalifyFreshGitHubCI({...args,requiredChecks:[name]});
  assert.equal(r.status,"OBSERVED");
  assert.equal(r.checks[0].name,name);
  assert.equal(r.checks[0].check_run_id,13);
 });
});
