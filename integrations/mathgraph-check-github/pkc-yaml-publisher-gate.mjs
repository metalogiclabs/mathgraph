// Pre-publication gate for the existing registered GitHub App publisher.
// No API calls or secrets here; caller must use its installation-scoped token,
// independently re-read the exact head and authenticated artifact bytes.
// This module cannot itself grant publication authority.
import {projectPKCYamlCheck} from "./pkc-yaml-check-projection.mjs";
const SHA=/^[a-f0-9]{40}$/;
export function gatePKCYamlPublication({report,repo,pr,head,liveHead,appId,
  installed=false,artifactAuthenticated=false,existingChecks=[]}={}) {
 const deny=reason=>({admitted:false,reason,check:null});
 if(repo!=="metalogiclabs/mathgraph" || !Number.isSafeInteger(pr) || pr<1 ||
    !SHA.test(head||"") || liveHead!==head)return deny("CARRIER_HEAD_UNAUTHORIZED_OR_STALE");
 if(appId!==5308912 || !installed)return deny("REGISTERED_APP_AUTHORITY_MISSING");
 if(!artifactAuthenticated)return deny("ARCHIVE_BYTES_NOT_AUTHENTICATED");
 if(!Array.isArray(existingChecks))return deny("CHECK_RECONCILIATION_UNKNOWN");
 const externalId=repo+"#"+pr+"@"+head;
 const owned=existingChecks.filter(c=>c?.name==="MathGraph Check / evidence scope" &&
   c?.external_id===externalId && c?.app?.id===appId);
 if(owned.length>1)return deny("DUPLICATE_APP_CHECK_CONFLICT");
 const check=projectPKCYamlCheck(report,{carrierRepo:repo,carrierHead:head,authorized:true});
 if(check?.output?.title!=="PKC_L4YAML_HISTORICAL_RESEARCH_BOUNDED" ||
    check?.conclusion!=="neutral")return deny("RECEIPT_NOT_ADMITTED");
 return {admitted:true,reason:"SOURCE_PINNED_ADVISORY_ONLY",check,
   externalId,existingCheckId:owned[0]?.id??null,
   operation:owned.length===1?"RECONCILE_EXISTING":"CREATE_ONE",
   merge:"UNKNOWN",authorization:"NONE"};
}
