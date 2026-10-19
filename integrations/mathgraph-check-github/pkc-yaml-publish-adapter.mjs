// Opt-in GitHub App publisher adapter. No deployment or credential changes.
// The caller provides an existing installation-scoped GitHub API function.
// Only publish on the owned evidence carrier, after authenticated ZIP binding.
import {qualifyLiveCheck} from "./pkc-yaml-live-boundary.mjs";
const NAME="MathGraph Check / evidence scope";
export async function publishPKCYaml({api,zipBytes,artifactMetadata,repo,pr,
 head,appId=5308912,installed=false}={}) {
 if(typeof api!=="function")throw Error("APP_API_REQUIRED");
 if(repo!=="metalogiclabs/mathgraph" || !Number.isSafeInteger(pr) || pr<1 ||
    !/^[a-f0-9]{40}$/.test(head||""))throw Error("UNAUTHORIZED_CARRIER");
 const prefix="/repos/"+repo;
 const fresh=await api(prefix+"/pulls/"+pr);
 if(fresh?.head?.sha!==head)throw Error("STALE_PR_HEAD");
 const result=await api(prefix+"/commits/"+head+
   "/check-runs?check_name="+encodeURIComponent(NAME)+"&filter=all&per_page=100");
 if(!Array.isArray(result?.check_runs) || !Number.isSafeInteger(result.total_count) ||
    result.total_count>result.check_runs.length)throw Error("CHECK_CENSUS_INCOMPLETE");
 const gate=qualifyLiveCheck({zipBytes,artifactMetadata,repo,pr,head,
   liveHead:fresh.head.sha,appId,installed,existingChecks:result.check_runs});
 if(!gate.admitted)throw Error("PUBLICATION_DENIED:"+gate.reason);
 if(gate.operation==="RECONCILE_EXISTING")return {
   state:"EXISTING_CHECK",checkId:gate.existingCheckId,head};
 const second=await api(prefix+"/pulls/"+pr);
 if(second?.head?.sha!==head)throw Error("STALE_PR_HEAD_BEFORE_WRITE");
 const created=await api(prefix+"/check-runs","POST",{
   ...gate.check,head_sha:head,external_id:gate.externalId});
 if(!Number.isSafeInteger(created?.id))throw Error("CHECK_CREATION_UNCONFIRMED");
 const readback=await api(prefix+"/check-runs/"+created.id);
 if(readback?.id!==created.id || readback?.app?.id!==appId ||
    readback?.head_sha!==head || readback?.external_id!==gate.externalId ||
    readback?.conclusion!=="neutral" || readback?.name!==NAME)
   throw Error("APP_CHECK_READBACK_MISMATCH");
 return {state:"APP_CHECK_VERIFIED",checkId:created.id,head,appId,
   conclusion:"neutral"};
}
