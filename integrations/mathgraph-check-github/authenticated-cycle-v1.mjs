// Authenticated GitHub-native PR observation. Uses scoped GITHUB_TOKEN,
// reads GitHub REST directly; no untrusted PR content is executed.
import {check,resolve,monitor} from "./check-resolve-monitor-v1.mjs";
const SHA=/^[0-9a-f]{40}$/;
const OWNER=/^[A-Za-z0-9_.-]+$/;
export async function githubSnapshot({repository,pr,token,fetcher=fetch,plans={}}){
 if(typeof repository!=="string"||!repository.split("/").every(x=>OWNER.test(x))||
    repository.split("/").length!==2||!Number.isSafeInteger(pr)||pr<1||
    typeof token!=="string"||token.length<8)throw Error("INVALID_INPUT");
 const api=async path=>{
  const url="https://api.github.com/repos/"+repository+path;
  const r=await fetcher(url,{headers:{Accept:"application/vnd.github+json",
   Authorization:"Bearer "+token,"X-GitHub-Api-Version":"2022-11-28"},
   signal:AbortSignal.timeout(15000)});
  if(!r.ok)throw Error("GITHUB_HTTP_"+r.status);
  return r.json();
 };
 const target=await api("/pulls/"+pr);
 if(target?.base?.repo?.full_name!==repository||target?.head?.repo?.full_name===undefined||
   !SHA.test(target.base.sha)||!SHA.test(target.head.sha))throw Error("PR_SOURCE_UNKNOWN");
 const sha=target.head.sha;
 // Paginate, then select exact-head latest completed run per name;
 // an in-progress newer rerun must keep the obligation UNKNOWN.
 let checks=[];
 for(let page=1;page<=10;page++){
   const r=await api("/commits/"+sha+"/check-runs?per_page=100&page="+page);
   if(!Array.isArray(r.check_runs)||!Number.isSafeInteger(r.total_count))throw Error("CHECKS_INCOMPLETE");
   checks.push(...r.check_runs);
   if(checks.length>=r.total_count)break;
   if(page===10)throw Error("CHECKS_PAGINATION_LIMIT");
 }
 const latest=new Map();
 for(const run of checks){
  if(run.head_sha!==sha||typeof run.name!=="string"||!Number.isSafeInteger(run.id))continue;
  if(run.app?.slug==="mathgraph-check"||run.name.startsWith("MathGraph Check"))continue;
  const old=latest.get(run.name);
  if(!old||(Date.parse(run.started_at||"")||0)>(Date.parse(old.started_at||"")||0)||
   ((Date.parse(run.started_at||"")||0)===(Date.parse(old.started_at||"")||0)&&run.id>old.id))latest.set(run.name,run);
 }
 if(latest.size===0)throw Error("NO_INDEPENDENT_CHECKS");
 const evidence=[...latest.values()].sort((a,b)=>a.name.localeCompare(b.name)).map(r=>({
  id:"github-check:"+r.id,subject_sha:sha,verifier_sha:sha,
  conclusion:r.status!=="completed"?"pending":r.conclusion==="success"?"success":
   ["failure","timed_out","action_required"].includes(r.conclusion)?"failure":"unknown",
  name:r.name,check_run_id:r.id
 }));
 const input={subject:{repository,pr,base_sha:target.base.sha,head_sha:sha},
  carrier:{repository,head_sha:sha},evidence,
  claims:evidence.map(e=>({id:e.name,requires:[e.id]}))};
 const result=check(input,{allowedRepositories:[repository],
  authenticatedEvidenceIds:evidence.map(e=>e.id)});
 result.claim_dependencies=input.claims.map(c=>({id:c.id,requires:c.requires}));
 return {input,result,plans:resolve(result,plans)};
}
export function compareSnapshots(before,after,{changedEvidenceIds=[]}={}){
 if(!before?.result||!after?.result)throw Error("MISSING_AUTHENTICATED_SNAPSHOTS");
 // Fresh authenticated replay of every assertion must come from caller's private
 // readbacks; never trust incoming claim's independent_requalification flag.
 const next={...after.result,independent_requalification:false};
 return monitor(before.result,next,{changedEvidenceIds});
}
