import test from "node:test";
import assert from "node:assert/strict";
import {collectAttempts,evaluateCollected} from "./github-attempt-collector-v1.mjs";
const sha="a".repeat(40),repository="metalogiclabs/mathgraph",runId=123;
function fake(states=["success","pending","success"],override={}){
 const fetcher=async(url)=>{
  const p=new URL(url).pathname;
  const data=p.endsWith("/runs/"+runId)?{head_sha:override.sha??sha,repository:{full_name:repository},run_attempt:states.length}:
  {total_count:1,jobs:[{id:100+Number(p.match(/attempts\/(\d+)/)?.[1]||0),run_id:runId,
   status:states[Number(p.match(/attempts\/(\d+)/)?.[1])-1]==="pending"?"in_progress":"completed",
   conclusion:states[Number(p.match(/attempts\/(\d+)/)?.[1])-1]==="pending"?null:states[Number(p.match(/attempts\/(\d+)/)?.[1])-1]}]};
  return {ok:true,json:async()=>data};
 };return fetcher;
}
const args={repository,runId,expectedSha:sha,token:"mockreadtoken"};
test("real-shaped success pending success transitions",async()=>{
 const r=await collectAttempts({...args,fetcher:fake()});
 assert.deepEqual(r.observations.map(x=>x.conclusion),["success","pending","success"]);
 assert.deepEqual(evaluateCollected(r).history.map(h=>h.claims[0].status),["OBSERVED","UNKNOWN","OBSERVED"]);
});
test("foreign head fails closed",async()=>await assert.rejects(collectAttempts({...args,fetcher:fake(undefined,{sha:"b".repeat(40)})}),/RUN_SOURCE/));
test("all checks green preserve bounded observation",async()=>{
 const r=await collectAttempts({...args,fetcher:fake(["success","success"])});assert.equal(evaluateCollected(r).state,"OBSERVED");
});
test("failure is BLOCKED",async()=>{
 const r=await collectAttempts({...args,fetcher:fake(["success","failure"])});assert.equal(evaluateCollected(r).state,"BLOCKED");
});
test("API denial cannot qualify",async()=>await assert.rejects(collectAttempts({...args,fetcher:async()=>({ok:false,status:403})}),/GITHUB_HTTP_403/));
