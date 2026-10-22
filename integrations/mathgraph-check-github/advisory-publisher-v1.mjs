// Conservative, opt-in GitHub App publisher for MathGraph Check reports.
// Does not acquire credentials, install Apps, accept arbitrary URLs or run PR code.
const SHA=/^[a-f0-9]{40}$/;
const REPO=/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
export function buildAdvisoryCheck(report,{repository,sha}={}){
 if(!REPO.test(repository??"")||!SHA.test(sha??""))throw Error("INVALID_DESTINATION");
 if(report?.source?.repository!==repository||report?.source?.head_sha!==sha)
   throw Error("STALE_SOURCE_REFUSED");
 if(report?.permission!=="ADVISORY_ONLY"||
   report?.scope!=="GITHUB_CHECK_RUN_OBSERVATION_ONLY"||
   !Array.isArray(report.evidence)||!Array.isArray(report.results))
   throw Error("UNQUALIFIED_REPORT");
 if(report.status!=="UNKNOWN"&&report.status!=="BLOCKED"&&report.status!=="OBSERVED")
   throw Error("INVALID_ASSESSMENT");
 if(report.results.some(r=>!["UNKNOWN","BLOCKED","OBSERVED"].includes(r.status)))
   throw Error("INVALID_CLAIM_ASSESSMENT");
 const msg=report.status==="BLOCKED"?
   "A reported required check failed. No claim of independent semantic verification.":
   report.status==="UNKNOWN"?
   "At least one obligation is unresolved; existing native checks do not establish a full warrant.":
   "Source-bound native checks were observed. No independent semantic warrant is conferred.";
 const rows=report.results.slice(0,30).map(x=>
   "- "+String(x.id).replace(/[\r\n]/g," ").slice(0,100)+": "+x.status).join("\n");
 return {name:"MathGraph Check / advisory evidence",head_sha:sha,status:"completed",
  conclusion:"neutral",external_id:"mathgraph-check-observation-v1:"+repository+":"+sha,
  output:{title:"MathGraph Check: "+report.status,
   summary:["**Advisory only. Not a merge approval or scientific certificate.**",
    msg,"Source: `"+repository+"@"+sha+"`",
    "Check Run observations ("+report.evidence.length+"):",
    rows||"No reported obligations","**Resolve / Monitor:** separate authenticated stages; no automatic action permitted."
   ].join("\n\n").slice(0,65000)}};
}
export async function publishAdvisory(report,{repository,sha,token,fetcher=fetch,dryRun=true}={}){
 const body=buildAdvisoryCheck(report,{repository,sha});
 if(dryRun)return {mode:"PREVIEW",request:body};
 if(typeof token!=="string"||token.length<10)throw Error("APP_TOKEN_REQUIRED");
 const response=await fetcher("https://api.github.com/repos/"+repository+"/check-runs",{
  method:"POST",headers:{Accept:"application/vnd.github+json",
   "X-GitHub-Api-Version":"2022-11-28",Authorization:"Bearer "+token,
   "Content-Type":"application/json"},body:JSON.stringify(body),
   signal:AbortSignal.timeout(15000)});
 if(!response.ok)throw Error("GITHUB_PUBLISH_HTTP_"+response.status);
 const result=await response.json();
 if(result?.head_sha!==sha||result?.name!==body.name||result?.conclusion!=="neutral")
  throw Error("PUBLISH_READBACK_INCOMPLETE");
 return {mode:"PUBLISHED",check_run_id:result.id,url:result.html_url};
}
