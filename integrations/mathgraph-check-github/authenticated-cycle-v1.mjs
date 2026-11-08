// Authenticated GitHub-native PR observation. Uses scoped GITHUB_TOKEN,
// reads GitHub REST directly; no untrusted PR content is executed.
import {check,resolve,monitor} from "./check-resolve-monitor-v1.mjs";
import {checkProjectionClaim} from './projection-claim-v1.mjs';
import {admitSignedProjectionReview} from './signed-projection-review-v1.mjs';
const SHA=/^[0-9a-f]{40}$/;
const OWNER=/^[A-Za-z0-9_.-]+$/;
export async function githubSnapshot({repository,pr,token,fetcher=fetch,plans={},
 projectionClaim,projectionAuthority,signedProjectionReview,trustedReviewerKeys}={}){
 if(typeof repository!=="string"||!repository.split("/").every(x=>OWNER.test(x))||
    repository.split("/").length!==2||!Number.isSafeInteger(pr)||pr<1||
    typeof token!=="string"||token.length<8)throw Error("INVALID_INPUT");
 if(signedProjectionReview!==undefined&&
   (projectionClaim!==undefined||projectionAuthority!==undefined))
   throw Error('AMBIGUOUS_PROJECTION_INPUT');
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
 // These fields are caller-separated on purpose: the trusted host must
 // authenticate its projection policy outside PR content and model output.
 // The current head is taken from GitHub, never from either supplied field.
 const subject={repository,pr,base_sha:target.base.sha,head_sha:sha};
 const projection=signedProjectionReview!==undefined?
  admitSignedProjectionReview(subject,signedProjectionReview,trustedReviewerKeys):
  projectionClaim===undefined?null:checkProjectionClaim(subject,projectionClaim,projectionAuthority);
 if(latest.size===0&&projection?.status!=='BLOCKED'&&
    signedProjectionReview===undefined)throw Error("NO_INDEPENDENT_CHECKS");
 const evidence=[...latest.values()].sort((a,b)=>a.name.localeCompare(b.name)).map(r=>({
  id:"github-check:"+r.id,subject_sha:sha,verifier_sha:sha,
  conclusion:r.status!=="completed"?"pending":r.conclusion==="success"?"success":
   ["failure","timed_out","action_required"].includes(r.conclusion)?"failure":"unknown",
  name:r.name,check_run_id:r.id
 }));
 const input={subject,
  carrier:{repository,head_sha:sha},evidence,
  claims:evidence.map(e=>({id:e.name,requires:[e.id]}))};
 const result=check(input,{allowedRepositories:[repository],
  authenticatedEvidenceIds:evidence.map(e=>e.id)});
 if(!Array.isArray(result.results))result.results=[];
 if(!result.subject)result.subject=subject;
 result.claim_dependencies=input.claims.map(c=>({id:c.id,requires:c.requires}));
 if(projection){
  if(projection.results.some(r=>result.results.some(x=>x.id===r.id)))
   throw Error('AMBIGUOUS_PROJECTION_CLAIM_ID');
  result.results.push(...projection.results);
  result.claim_dependencies.push(...projection.claim_dependencies);
  result.status=result.results.some(x=>x.status==='BLOCKED')?'BLOCKED':
   projection.status==='UNKNOWN'||result.results.some(x=>x.status==='UNKNOWN')?'UNKNOWN':'OBSERVED';
  result.projection_scope=projection.checked_scope;
  if(!evidence.length&&projection.status==='BLOCKED')
   result.reason='QUALIFIED_PROJECTION_ONLY_NO_NATIVE_CHECK_RUNS';
 }
 return {input,result,projection,plans:resolve(result,plans)};
}
export function compareSnapshots(before,after,{changedEvidenceIds=[]}={}){
 if(!before?.result||!after?.result)throw Error("MISSING_AUTHENTICATED_SNAPSHOTS");
 // Fresh authenticated replay of every assertion must come from caller's private
 // readbacks; never trust incoming claim's independent_requalification flag.
 const next={...after.result,independent_requalification:false};
 return monitor(before.result,next,{changedEvidenceIds});
}
