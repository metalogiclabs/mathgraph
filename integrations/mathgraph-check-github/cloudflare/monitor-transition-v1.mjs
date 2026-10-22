// Native Cloudflare queue monitor event, emitted after authenticated Check readback.
// Observability only: no independent semantic or scientific claim is inferred.
const SHA=/^[a-f0-9]{40}$/;
export function transitionReceipt({repository,pr,headSha,previousCheck,currentCheck,outcome}={}){
 if(typeof repository!=="string"||!Number.isSafeInteger(pr)||pr<1||!SHA.test(headSha??""))
  throw Error("INVALID_MONITOR_SOURCE");
 const old=previousCheck?.output;
 const now=currentCheck?.output;
 if(!now||typeof now.title!=="string"||typeof now.summary!=="string")
  throw Error("INCOMPLETE_MONITOR_EVIDENCE");
 if(previousCheck&&previousCheck.head_sha!==headSha)throw Error("STALE_MONITOR_HEAD");
 const changed=!!old&&(old.title!==now.title||old.summary!==now.summary);
 const kind=!old?"FIRST_OBSERVATION":changed?"EVIDENCE_CHANGED":"EVIDENCE_UNCHANGED";
 return Object.freeze({schema:"mathgraph.monitor.transition.v1",
  repository,pr,head_sha:headSha,kind,outcome:outcome||"UNKNOWN",
  permission:"ADVISORY_ONLY",semantic_verification:"NOT_ESTABLISHED",
  // A change requires the downstream warrant graph to reclose; do not
  // guess which claims are safe from a plain Check summary comparison.
  downstream_warrant_status:changed?"REQUALIFICATION_REQUIRED":"NOT_EVALUATED"});
}
