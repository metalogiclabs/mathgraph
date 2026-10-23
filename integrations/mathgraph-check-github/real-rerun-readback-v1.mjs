// Independent GitHub REST attestation of actual workflow rerun attempts.
// Read-only, source-pinned, no claim about interim pending-state observation.
const repo="metalogiclabs/mathgraph",runId=39878398161;
const sha="63018d9accc5c05c153cfe1ac22fca1c032cbbb5";
const expected=[120169578515,120170194613];
const token=process.env.GITHUB_TOKEN;
if(typeof token!=="string"||token.length<8)throw Error("NO_GITHUB_READ_TOKEN");
async function get(path){
 const response=await fetch("https://api.github.com/repos/"+repo+path,{headers:{
 Authorization:"Bearer "+token,Accept:"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"
 },signal:AbortSignal.timeout(15000)});
 if(!response.ok)throw Error("GITHUB_HTTP_"+response.status+"_"+path);
 return response.json();
}
const run=await get("/actions/runs/"+runId);
if(run.head_sha!==sha||run.repository?.full_name!==repo||run.conclusion!=="success"||run.run_attempt<2)
 throw Error("RUN_SOURCE_OR_ATTEMPTS_MISMATCH");
const observations=[];
for(let attempt=1;attempt<=2;attempt++){
 const data=await get("/actions/runs/"+runId+"/attempts/"+attempt+"/jobs?per_page=100");
 if(!Array.isArray(data.jobs)||data.total_count!==data.jobs.length)throw Error("INCOMPLETE_ATTEMPT_JOBS");
 const job=data.jobs.find(j=>j.id===expected[attempt-1]);
 if(!job||job.run_id!==runId||job.status!=="completed"||job.conclusion!=="success"||
    job.head_sha&&job.head_sha!==sha)throw Error("JOB_SOURCE_OR_RESULT_MISMATCH");
 observations.push({attempt,job_id:job.id,status:job.status,conclusion:job.conclusion});
}
console.log("MATHGRAPH_REAL_SAME_SHA_RERUN_VERIFIED "+JSON.stringify({
 repository:repo,run_id:runId,head_sha:sha,observations,
 scope:"TWO_COMPLETED_NATIVE_SUCCESS_OBSERVATIONS_ONLY",
 pending_observed:false,permission:"ADVISORY_ONLY"}));
