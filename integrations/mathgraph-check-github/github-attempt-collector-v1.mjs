// Source-exact authenticated GitHub Actions attempt collector.
// Produces observations, never synthesizes an unobserved pending transition.
import {replayLifecycle} from "./living-warrant-cycle-v1.mjs";
const SHA=/^[a-f0-9]{40}$/;
export async function collectAttempts({repository,runId,expectedSha,token,fetcher=fetch,maxAttempts=10}={}){
 if(!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repository??"")||
 !Number.isSafeInteger(runId)||runId<1||!SHA.test(expectedSha??"")||
 typeof token!=="string"||token.length<8||maxAttempts<1||maxAttempts>20)
 throw Error("INVALID_COLLECTOR_INPUT");
 const api=async path=>{
 const r=await fetcher("https://api.github.com/repos/"+repository+path,{
 headers:{Accept:"application/vnd.github+json",Authorization:"Bearer "+token,
 "X-GitHub-Api-Version":"2022-11-28"},signal:AbortSignal.timeout(15000)});
 if(!r.ok)throw Error("GITHUB_HTTP_"+r.status);
 return r.json();
 };
 const run=await api("/actions/runs/"+runId);
 if(run.head_sha!==expectedSha||run.repository?.full_name!==repository||
 !Number.isSafeInteger(run.run_attempt)||run.run_attempt<1||
 run.run_attempt>maxAttempts)throw Error("RUN_SOURCE_OR_ATTEMPT_MISMATCH");
 const observations=[];
 for(let attempt=1;attempt<=run.run_attempt;attempt++){
 const data=await api("/actions/runs/"+runId+"/attempts/"+attempt+"/jobs?per_page=100");
 if(!Array.isArray(data.jobs)||!Number.isSafeInteger(data.total_count)||
 data.total_count!==data.jobs.length||!data.jobs.length)throw Error("ATTEMPT_INCOMPLETE");
 const jobs=data.jobs.filter(j=>j.run_id===runId&&Number.isSafeInteger(j.id));
 if(jobs.length!==data.jobs.length)throw Error("JOB_IDENTITY_UNKNOWN");
 const state=jobs.some(j=>j.status!=="completed")?"pending":
 jobs.some(j=>j.conclusion==="failure"||j.conclusion==="timed_out")?"failure":
 jobs.every(j=>j.conclusion==="success")?"success":"pending";
 observations.push({attempt,conclusion:state,job_ids:jobs.map(j=>j.id).sort((a,b)=>a-b),
 receipt_id:"github:"+repository+":"+runId+":"+attempt+":"+
 jobs.map(j=>j.id+":"+j.status+":"+j.conclusion).sort().join(",")});
 }
 return {repository,run_id:runId,head_sha:expectedSha,observations,
 trust:"AUTHENTICATED_GITHUB_REST_READBACK",permission:"ADVISORY_ONLY"};
}
export function evaluateCollected(series){
 if(!series?.observations?.length||!SHA.test(series.head_sha??""))throw Error("NO_AUTHENTICATED_SERIES");
 const events=series.observations.map(o=>({type:"OBSERVE",id:"native-ci",
 generation:o.attempt,source_sha:series.head_sha,receipt_id:o.receipt_id,conclusion:o.conclusion}));
 return replayLifecycle({source:{repository:series.repository,sha:series.head_sha},
 claims:[{id:"native-ci-attempt",requires:["native-ci"]}],events,
 authenticatedReceipts:series.observations.map(o=>o.receipt_id)});
}
