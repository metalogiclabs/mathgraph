// Isolated App-token reconciliation gate. No App registration or deployment.
// Caller supplies a GitHub-App installation token; token issuance belongs to
// the existing authenticated worker. Default remains preview-only.
import {buildAdvisoryCheck} from "./advisory-publisher-v1.mjs";
const SHA=/^[a-f0-9]{40}$/;
const REPO=/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
export async function reconcileAdvisory(report,{
 repository,pr,headSha,appId,installationToken,allowedRepos=[],
 fetcher=fetch,write=false
}={}){
 if(!REPO.test(repository??"")||!Number.isSafeInteger(pr)||pr<1||
   !SHA.test(headSha??"")||!Number.isSafeInteger(appId)||appId<1||
   !allowedRepos.includes(repository)||typeof installationToken!=="string"||
   installationToken.length<10)throw Error("UNAUTHORIZED_RECONCILIATION");
 const request=buildAdvisoryCheck(report,{repository,sha:headSha});
 const api=async(path,method="GET",body)=>{
  const response=await fetcher("https://api.github.com"+path,{method,
   headers:{Accept:"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28",
   Authorization:"Bearer "+installationToken,"Content-Type":"application/json"},
   body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(15000)});
  if(!response.ok)throw Error("GITHUB_HTTP_"+response.status);
  return response.json();
 };
 const prefix="/repos/"+repository;
 async function exactHead(){
  const p=await api(prefix+"/pulls/"+pr);
  if(p?.head?.sha!==headSha||p?.base?.repo?.full_name!==repository)throw Error("STALE_PR_HEAD");
 }
 await exactHead();
 const externalId="mathgraph-check-advisory-v1:"+repository+"#"+pr+"@"+headSha;
 const data=await api(prefix+"/commits/"+headSha+"/check-runs?check_name="+
  encodeURIComponent(request.name)+"&filter=all&per_page=100");
 if(!Array.isArray(data?.check_runs)||!Number.isSafeInteger(data.total_count)||
   data.total_count>data.check_runs.length||data.total_count>100)throw Error("INCOMPLETE_RECONCILIATION");
 const own=data.check_runs.filter(r=>r?.app?.id===appId&&r.name===request.name&&r.external_id===externalId);
 if(own.length>1)throw Error("DUPLICATE_APP_CHECKS");
 if(own.length===1&&(!Number.isSafeInteger(own[0].id)||own[0].head_sha!==headSha))
  throw Error("CHECK_IDENTITY_MISMATCH");
 await exactHead(); // guard races after reconciliation
 if(!write)return {mode:"PREVIEW",check:request,existing:own.length};
 if(own.length===1){
  const old=own[0];
  if(old.status==="completed"&&old.conclusion==="neutral"&&
     old.output?.summary===request.output.summary)return {mode:"UNCHANGED",check_run_id:old.id};
  // Never silently overwrite another run: same App/check identity only.
  const updated=await api(prefix+"/check-runs/"+old.id,"PATCH",{
   status:"completed",conclusion:"neutral",external_id:externalId,output:request.output});
  if(updated.id!==old.id||updated.conclusion!=="neutral"||
     updated.head_sha!==headSha)throw Error("UPDATE_READBACK_MISMATCH");
  return {mode:"UPDATED",check_run_id:updated.id};
 }
 const created=await api(prefix+"/check-runs","POST",{...request,external_id:externalId});
 if(!Number.isSafeInteger(created?.id)||created.head_sha!==headSha||
   created.conclusion!=="neutral"||created.app?.id!==appId)
   throw Error("CREATE_READBACK_MISMATCH");
 return {mode:"CREATED",check_run_id:created.id};
}
