import test from "node:test";
import assert from "node:assert/strict";
import {mkdtemp,readFile,writeFile,rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {captureObservation,readCaptured} from "./durable-ci-capture-v1.mjs";
const sha="a".repeat(40),repository="metalogiclabs/mathgraph";
const fake=(status,conclusion=null,wrong=false)=>async url=>({ok:true,json:async()=>url.includes("/jobs")?
 {total_count:1,jobs:[{id:11,run_id:42,status,conclusion}]}:
 {head_sha:wrong?"b".repeat(40):sha,repository:{full_name:repository},
 run_attempt:2,status,conclusion}});
test("captures transient in_progress then success as distinct durable records",async()=>{
 const dir=await mkdtemp(join(tmpdir(),"mg-ci-"));const path=join(dir,"capture.jsonl");
 try{
 const options={repository,runId:42,sha,token:"test-token",path};
 await captureObservation({...options,fetcher:fake("in_progress"),now:()=>"2026-10-23T00:00:00Z"});
 await captureObservation({...options,fetcher:fake("completed","success"),now:()=>"2026-10-23T00:01:00Z"});
 const x=await readCaptured(path);assert.deepEqual(x.map(z=>z.run_status),["in_progress","completed"]);
 assert.equal(x[0].run_conclusion,null);assert.equal(x[1].run_conclusion,"success");
 }finally{await rm(dir,{recursive:true,force:true})}
});
test("wrong source refuses capture",async()=>{
 const dir=await mkdtemp(join(tmpdir(),"mg-ci-"));const path=join(dir,"capture.jsonl");
 try{await assert.rejects(captureObservation({repository,runId:42,sha,token:"test-token",path,fetcher:fake("completed","success",true)}),/RUN_IDENTITY/);}
 finally{await rm(dir,{recursive:true,force:true})}
});
test("tampered record rejected",async()=>{
 const dir=await mkdtemp(join(tmpdir(),"mg-ci-"));const path=join(dir,"capture.jsonl");
 try{
 await captureObservation({repository,runId:42,sha,token:"test-token",path,fetcher:fake("completed","success")});
 const text=await readFile(path,"utf8");await writeFile(path,text.replace("success","failure"));
 await assert.rejects(readCaptured(path),/CAPTURE_DIGEST_MISMATCH/);
 }finally{await rm(dir,{recursive:true,force:true})}
});
