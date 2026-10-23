// Durable observation capture: append-only NDJSON on a local trusted runner.
// GitHub REST is the source of observation; file is a bounded local receipt,
// NOT a signature and not permanent cloud storage by itself.
import {appendFile,readFile} from "node:fs/promises";
import {createHash} from "node:crypto";
const SHA=/^[a-f0-9]{40}$/;
export async function captureObservation({repository,runId,sha,token,path,fetcher=fetch,now=()=>new Date().toISOString()}={}){
 if(!/^[\w.-]+\/[\w.-]+$/.test(repository??"")||!Number.isSafeInteger(runId)||runId<1||
 !SHA.test(sha??"")||!token||!path)throw Error("INVALID_CAPTURE_SCOPE");
 const read=async endpoint=>{
 const r=await fetcher("https://api.github.com/repos/"+repository+endpoint,{
 headers:{Authorization:"Bearer "+token,Accept:"application/vnd.github+json",
 "X-GitHub-Api-Version":"2022-11-28"},signal:AbortSignal.timeout(15000)});
 if(!r.ok)throw Error("GITHUB_HTTP_"+r.status);
 return r.json();
 };
 const run=await read("/actions/runs/"+runId);
 if(run.head_sha!==sha||run.repository?.full_name!==repository||
 !Number.isSafeInteger(run.run_attempt)||run.run_attempt<1)throw Error("RUN_IDENTITY_MISMATCH");
 const jobs=await read("/actions/runs/"+runId+"/jobs?per_page=100");
 if(!Array.isArray(jobs.jobs)||!Number.isSafeInteger(jobs.total_count)||
 jobs.total_count!==jobs.jobs.length)throw Error("JOBS_INCOMPLETE");
 const observations=jobs.jobs.map(j=>{
 if(!Number.isSafeInteger(j.id)||j.run_id!==runId)throw Error("JOB_IDENTITY_MISMATCH");
 return {id:j.id,status:j.status,conclusion:j.conclusion??null};
 }).sort((a,b)=>a.id-b.id);
 const event={schema:"mathgraph.ci-observation.v1",repository,run_id:runId,
 source_sha:sha,attempt:run.run_attempt,recorded_at:now(),run_status:run.status,
 run_conclusion:run.conclusion??null,jobs:observations};
 const bytes=JSON.stringify(event);
 const digest=createHash("sha256").update(bytes).digest("hex");
 const record=JSON.stringify({...event,sha256:digest})+"\n";
 await appendFile(path,record,{flag:"a",mode:0o600});
 return {event,digest};
}
export async function readCaptured(path){
 const raw=await readFile(path,"utf8");
 const lines=raw.split("\n").filter(Boolean);
 if(!lines.length)throw Error("EMPTY_CAPTURE");
 return lines.map(line=>{
 const {sha256,...event}=JSON.parse(line);
 if(createHash("sha256").update(JSON.stringify(event)).digest("hex")!==sha256)
 throw Error("CAPTURE_DIGEST_MISMATCH");
 return event;
 });
}
