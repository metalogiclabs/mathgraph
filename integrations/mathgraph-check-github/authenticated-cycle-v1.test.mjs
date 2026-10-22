import test from "node:test";
import assert from "node:assert/strict";
import {githubSnapshot,compareSnapshots} from "./authenticated-cycle-v1.mjs";
const a="a".repeat(40),b="b".repeat(40);
function mock({runs,head=a,status=200}={}){
 const got=[];
 const fetcher=async (url,opts)=>{
  got.push(url);
  if(status!==200)return {ok:false,status};
  const data=url.includes("/pulls/")?
   {base:{sha:b,repo:{full_name:"metalogiclabs/mathgraph"}},head:{sha:head,repo:{full_name:"metalogiclabs/mathgraph"}}}:
   {total_count:runs.length,check_runs:runs};
  return {ok:true,json:async()=>data};
 };
 return {fetcher,got};
}
function run(id,name,conclusion="success",status="completed",sha=a){
 return {id,name,head_sha:sha,status,conclusion,started_at:"2026-10-23T00:00:00Z",app:{slug:"github-actions"}};
}
const args={repository:"metalogiclabs/mathgraph",pr:195,token:"not-real-but-long"};
test("authenticated GitHub readback yields observation but not proof",async()=>{
 const m=mock({runs:[run(1,"native")]});
 const r=await githubSnapshot({...args,fetcher:m.fetcher});
 assert.equal(r.result.status,"OBSERVED");assert.equal(r.result.permission,"ADVISORY_ONLY");
 assert.equal(r.result.subject.head_sha,a);assert.equal(m.got.length,2);
});
test("untrusted extra-head checks are ignored",async()=>{
 const m=mock({runs:[run(1,"native","success","completed",b)]});
 await assert.rejects(githubSnapshot({...args,fetcher:m.fetcher}),/NO_INDEPENDENT_CHECKS/);
});
test("pending latest rerun does not reuse old green result",async()=>{
 const older=run(1,"native");older.started_at="2026-10-22T00:00:00Z";
 const m=mock({runs:[older,run(2,"native","success","in_progress")]});
 const r=await githubSnapshot({...args,fetcher:m.fetcher});
 assert.equal(r.result.status,"UNKNOWN");
});
test("checker cannot self-certify",async()=>{
 const m=mock({runs:[{...run(1,"MathGraph Check / evidence scope"),app:{slug:"mathgraph-check"}}]});
 await assert.rejects(githubSnapshot({...args,fetcher:m.fetcher}),/NO_INDEPENDENT_CHECKS/);
});
test("failed run blocks only its exact obligation",async()=>{
 const m=mock({runs:[run(1,"native","failure"),run(2,"lint")]});
 const r=await githubSnapshot({...args,fetcher:m.fetcher});
 assert.equal(r.result.results.find(x=>x.id==="native").status,"BLOCKED");
 assert.equal(r.result.results.find(x=>x.id==="lint").status,"OBSERVED");
});
test("invalid PR sha rejected",async()=>{
 const m=mock({runs:[run(1,"native")],head:"wrong"});
 await assert.rejects(githubSnapshot({...args,fetcher:m.fetcher}),/PR_SOURCE_UNKNOWN/);
});
test("API denial cannot produce a warrant",async()=>{
 const m=mock({runs:[],status:403});
 await assert.rejects(githubSnapshot({...args,fetcher:m.fetcher}),/GITHUB_HTTP_403/);
});
test("change triggers withdrawal; untouched evidence remains",async()=>{
 const first=await githubSnapshot({...args,fetcher:mock({runs:[run(1,"native"),run(2,"lint")]}).fetcher});
 const after=await githubSnapshot({...args,fetcher:mock({runs:[run(1,"native","failure"),run(2,"lint")]}).fetcher});
 const result=compareSnapshots(first,after,{changedEvidenceIds:["github-check:1"]});
 assert.equal(result.transitions.find(x=>x.claim==="native").to,"BLOCKED");
 assert.equal(result.transitions.find(x=>x.claim==="lint").to,"OBSERVED");
});
test("after failure, fresh green result needs requalification",async()=>{
 const before=await githubSnapshot({...args,fetcher:mock({runs:[run(1,"native","failure")]}).fetcher});
 const after=await githubSnapshot({...args,fetcher:mock({runs:[run(1,"native")]}).fetcher});
 const result=compareSnapshots(before,after,{changedEvidenceIds:["github-check:1"]});
 assert.equal(result.transitions[0].to,"UNKNOWN");
});
