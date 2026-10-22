import test from "node:test";
import assert from "node:assert/strict";
import {buildAdvisoryCheck,publishAdvisory} from "./advisory-publisher-v1.mjs";
const a="a".repeat(40),repo="metalogiclabs/mathgraph";
const report=()=>({source:{repository:repo,head_sha:a},permission:"ADVISORY_ONLY",
scope:"GITHUB_CHECK_RUN_OBSERVATION_ONLY",status:"UNKNOWN",
evidence:[{id:"ci"}],results:[{id:"native",status:"UNKNOWN"}]});
test("neutral source-bound publisher payload",()=>{
 const r=buildAdvisoryCheck(report(),{repository:repo,sha:a});
 assert.equal(r.conclusion,"neutral");assert.equal(r.head_sha,a);assert.match(r.output.summary,/Not a merge approval/);
});
test("different PR head refused",()=>assert.throws(()=>buildAdvisoryCheck(report(),{repository:repo,sha:"b".repeat(40)}),/STALE/));
test("different repo refused",()=>assert.throws(()=>buildAdvisoryCheck(report(),{repository:"nasa-jpl/L4YAML",sha:a}),/STALE/));
test("non advisory authority refused",()=>{const r=report();r.permission="MERGE_APPROVED";assert.throws(()=>buildAdvisoryCheck(r,{repository:repo,sha:a}),/UNQUALIFIED/);});
test("semantic warrant claim refused",()=>{const r=report();r.scope="UNIVERSAL_PROOF";assert.throws(()=>buildAdvisoryCheck(r,{repository:repo,sha:a}),/UNQUALIFIED/);});
test("invalid claim verdict refused",()=>{const r=report();r.results[0].status="PROVED";assert.throws(()=>buildAdvisoryCheck(r,{repository:repo,sha:a}),/INVALID_CLAIM/);});
test("default is strictly no-write",async()=>{
 let calls=0;const x=await publishAdvisory(report(),{repository:repo,sha:a,fetcher:()=>{calls++}});
 assert.equal(x.mode,"PREVIEW");assert.equal(calls,0);
});
test("missing token refuses live write",async()=>await assert.rejects(publishAdvisory(report(),{repository:repo,sha:a,dryRun:false}),/APP_TOKEN_REQUIRED/));
test("explicit live mock posts neutral and validates response",async()=>{
 let got;const fetcher=async (url,options)=>{got={url,options};return {ok:true,json:async()=>({id:123,head_sha:a,name:"MathGraph Check / advisory evidence",conclusion:"neutral",html_url:"https://github.com/example"})}};
 const r=await publishAdvisory(report(),{repository:repo,sha:a,token:"mock-token-long",fetcher,dryRun:false});
 assert.equal(r.mode,"PUBLISHED");assert.equal(got.options.method,"POST");assert.equal(JSON.parse(got.options.body).conclusion,"neutral");
});
test("publication identity mismatch refuses to acknowledge success",async()=>{
 const fetcher=async()=>({ok:true,json:async()=>({id:123,head_sha:"b".repeat(40),name:"other",conclusion:"success"})});
 await assert.rejects(publishAdvisory(report(),{repository:repo,sha:a,token:"mock-token-long",fetcher,dryRun:false}),/READBACK_INCOMPLETE/);
});
