import test from "node:test";
import assert from "node:assert/strict";
import {reconcileAdvisory} from "./app-token-reconcile-v1.mjs";
const sha="a".repeat(40),repository="metalogiclabs/mathgraph",pr=197,appId=5308912;
const report=()=>({source:{repository,head_sha:sha},permission:"ADVISORY_ONLY",
scope:"GITHUB_CHECK_RUN_OBSERVATION_ONLY",status:"UNKNOWN",evidence:[{id:"ci"}],
results:[{id:"native",status:"UNKNOWN"}]});
const ext="mathgraph-check-advisory-v1:"+repository+"#"+pr+"@"+sha;
const opts={repository,pr,headSha:sha,appId,installationToken:"test-installation-token",allowedRepos:[repository]};
const fake=(items=[],change={})=>{
 const calls=[];let head=change.head||sha;
 const fetcher=async(url,o)=>{const path=new URL(url).pathname;calls.push({path,method:o.method,body:o.body&&JSON.parse(o.body)});
 if(path.endsWith("/pulls/"+pr))return {ok:true,json:async()=>({head:{sha:head},base:{repo:{full_name:repository}}})};
 if(path.endsWith("/check-runs")&&o.method==="GET")return {ok:true,json:async()=>({total_count:items.length,check_runs:items})};
 if(o.method==="POST"||o.method==="PATCH")return {ok:true,json:async()=>({
 id:o.method==="POST"?77:items[0].id,head_sha:sha,conclusion:"neutral",app:{id:appId}})};
 throw Error("unexpected "+path);
 };return {fetcher,calls};
};
test("dry run never writes",async()=>{const m=fake();const r=await reconcileAdvisory(report(),{...opts,fetcher:m.fetcher});assert.equal(r.mode,"PREVIEW");assert.equal(m.calls.filter(c=>c.method!=="GET").length,0)});
test("create uses App token only on explicitly allowed repo",async()=>{const m=fake();const r=await reconcileAdvisory(report(),{...opts,fetcher:m.fetcher,write:true});assert.equal(r.mode,"CREATED");assert.equal(m.calls.filter(c=>c.method==="POST").length,1)});
test("stale exact head refuses any write",async()=>{const m=fake([], {head:"b".repeat(40)});await assert.rejects(reconcileAdvisory(report(),{...opts,fetcher:m.fetcher,write:true}),/STALE/);assert.equal(m.calls.filter(c=>c.method==="POST").length,0)});
test("foreign repo not allowed",async()=>await assert.rejects(reconcileAdvisory(report(),{...opts,allowedRepos:[]}),/UNAUTHORIZED/));
test("missing installation credential refused",async()=>await assert.rejects(reconcileAdvisory(report(),{...opts,installationToken:""}),/UNAUTHORIZED/));
test("existing exact App run can be updated, not duplicated",async()=>{const m=fake([{id:12,app:{id:appId},name:"MathGraph Check / advisory evidence",external_id:ext,head_sha:sha,status:"completed",conclusion:"neutral",output:{summary:"older"}}]);const r=await reconcileAdvisory(report(),{...opts,fetcher:m.fetcher,write:true});assert.equal(r.mode,"UPDATED");assert.equal(m.calls.filter(c=>c.method==="PATCH").length,1);assert.equal(m.calls.filter(c=>c.method==="POST").length,0)});
test("existing current run is idempotent",async()=>{const m=fake([{id:12,app:{id:appId},name:"MathGraph Check / advisory evidence",external_id:ext,head_sha:sha,status:"completed",conclusion:"neutral",output:{summary:"older"}}]);const r=await reconcileAdvisory(report(),{...opts,fetcher:m.fetcher,write:false});assert.equal(r.existing,1)});
test("duplicate publisher identities fail closed",async()=>{const item={id:12,app:{id:appId},name:"MathGraph Check / advisory evidence",external_id:ext,head_sha:sha};const m=fake([item,{...item,id:13}]);await assert.rejects(reconcileAdvisory(report(),{...opts,fetcher:m.fetcher,write:true}),/DUPLICATE/);});
test("foreign app check is never overwritten",async()=>{const m=fake([{id:12,app:{id:999},name:"MathGraph Check / advisory evidence",external_id:ext,head_sha:sha}]);const r=await reconcileAdvisory(report(),{...opts,fetcher:m.fetcher,write:false});assert.equal(r.existing,0)});
test("unsupported warrant cannot publish",async()=>{const r=report();r.permission="MERGE_APPROVED";const m=fake();await assert.rejects(reconcileAdvisory(r,{...opts,fetcher:m.fetcher,write:true}),/UNQUALIFIED/);});
