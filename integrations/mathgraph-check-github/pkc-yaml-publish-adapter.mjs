// Opt-in GitHub App publisher adapter. No deployment or credential changes.
// The caller provides an existing installation-scoped GitHub API function.
// Only publish on the owned evidence carrier, after authenticated ZIP binding.
import {qualifyLiveCheck} from "./pkc-yaml-live-boundary.mjs";
const NAME="MathGraph Check / evidence scope";
const APP_ID=5308912;
const CARRIER="metalogiclabs/mathgraph";
export function reconcileCarrierCheck(check,previous,head){
 if(!previous)return {operation:"CREATE"};
 const expected=CARRIER+"#178@"+head;
 if(!Number.isSafeInteger(previous.id) || previous.id<1 ||
    previous.app?.id!==APP_ID || previous.name!==NAME ||
    previous.head_sha!==head || previous.external_id!==expected ||
    previous.status!=="completed" || previous.conclusion!=="neutral")
   throw Error("EXISTING_CARRIER_CHECK_INVALID");
 const details="https://github.com/"+CARRIER+"/runs/"+previous.id;
 return {operation:previous.output?.title===check.output.title &&
   previous.output?.summary===check.output.summary &&
   previous.details_url===details?"EXISTING":"UPDATE",id:previous.id};
}
export async function publishPKCYaml({api,zipBytes,artifactMetadata,repo,pr,
 head,appId=5308912,installed=false}={}) {
 if(typeof api!=="function")throw Error("APP_API_REQUIRED");
 if(repo!==CARRIER || pr!==178 ||
    head!=="05a6057e94d899ded94374db4a831963034aea93")
   throw Error("UNAUTHORIZED_CARRIER");
 const prefix="/repos/"+repo;
 const fresh=await api(prefix+"/pulls/"+pr);
 if(fresh?.head?.sha!==head || fresh?.state!=="open" ||
    fresh?.head?.repo?.full_name!==repo ||
    fresh?.base?.repo?.full_name!==repo)throw Error("STALE_PR_HEAD");
 const result=await api(prefix+"/commits/"+head+
   "/check-runs?check_name="+encodeURIComponent(NAME)+"&filter=all&per_page=100");
 if(!Array.isArray(result?.check_runs) || !Number.isSafeInteger(result.total_count) ||
    result.total_count>result.check_runs.length)throw Error("CHECK_CENSUS_INCOMPLETE");
 const gate=qualifyLiveCheck({zipBytes,artifactMetadata,repo,pr,head,
   liveHead:fresh.head.sha,appId,installed,existingChecks:result.check_runs});
 if(!gate.admitted)throw Error("PUBLICATION_DENIED:"+gate.reason);
 const previous=result.check_runs.find(x=>x.id===gate.existingCheckId);
 const plan=reconcileCarrierCheck(gate.check,previous,head);
 const second=await api(prefix+"/pulls/"+pr);
 if(second?.head?.sha!==head || second?.state!=="open" ||
    second?.head?.repo?.full_name!==repo ||
    second?.base?.repo?.full_name!==repo)
   throw Error("STALE_PR_HEAD_BEFORE_WRITE");
 if(plan.operation==="EXISTING")return {state:"EXISTING_CHECK",checkId:plan.id,head};
 let checkId;
 if(plan.operation==="UPDATE"){
   checkId=plan.id;
   const changed=await api(prefix+"/check-runs/"+checkId,"PATCH",{
     status:"completed",conclusion:"neutral",output:gate.check.output,
     details_url:"https://github.com/"+repo+"/runs/"+checkId});
   if(changed?.id!==checkId || changed?.app?.id!==appId ||
      changed?.head_sha!==head || changed?.conclusion!=="neutral")
     throw Error("APP_CHECK_UPDATE_MISMATCH");
 }else{
   const created=await api(prefix+"/check-runs","POST",{
     ...gate.check,head_sha:head,external_id:gate.externalId});
   if(!Number.isSafeInteger(created?.id) || created.id<1 ||
      created?.app?.id!==appId || created?.head_sha!==head ||
      created?.conclusion!=="neutral")throw Error("CHECK_CREATION_UNCONFIRMED");
   checkId=created.id;
   const linked=await api(prefix+"/check-runs/"+checkId,"PATCH",{
     details_url:"https://github.com/"+repo+"/runs/"+checkId});
   if(linked?.id!==checkId || linked?.app?.id!==appId ||
      linked?.head_sha!==head || linked?.conclusion!=="neutral")
     throw Error("CHECK_DETAILS_LINK_UNCONFIRMED");
 }
 const readback=await api(prefix+"/check-runs/"+checkId);
 if(readback?.id!==checkId || readback?.app?.id!==appId ||
    readback?.head_sha!==head || readback?.external_id!==gate.externalId ||
    readback?.status!=="completed" || readback?.conclusion!=="neutral" ||
    readback?.name!==NAME ||
    readback?.details_url!=="https://github.com/"+repo+"/runs/"+checkId ||
    readback?.output?.title!==gate.check.output.title ||
    readback?.output?.summary!==gate.check.output.summary)
   throw Error("APP_CHECK_READBACK_MISMATCH");
 return {state:plan.operation==="UPDATE"?"UPDATED_CHECK":"APP_CHECK_VERIFIED",
   checkId,head,appId,conclusion:"neutral"};
}
