// A read-only comparison harness. The two source adapters run upstream of this
// function; neither it nor the framed assessor is a native verifier.
import {assessWarrant} from "./warrant.mjs";
import {assessConsequentialFrame} from "./consequential-frame.mjs";

const same=(a,b)=>a?.repository===b?.repository &&
  a?.pr===b?.pr && a?.sha===b?.sha;

export function replayFrameCase({
  snapshot,verifiedOwner,frameBytes,frameSha256,nativeReceipt,asOf
}){
  return {
    framed:assessConsequentialFrame({snapshot,verifiedOwner,frameBytes,
      frameSha256,nativeReceipt,asOf}),
    packetOnly:assessWarrant(snapshot,
      verifiedOwner?.verified ? verifiedOwner.contract : undefined,asOf),
    verifiedOwner
  };
}

// A *separately coded*, full-information conventional rule reference for the
// frozen finite experiment, not a third-party reviewer or frontier agent.
// It consumes the same independently supplied frame, native result and grant.
export function conventionalReference({frame,verifiedOwner,nativeReceipt,asOf}){
  const c=verifiedOwner?.verified ? verifiedOwner.contract : null;
  if(!c || !same(c.subject,frame?.subject) ||
      c.policy_version!==frame.policy_version ||
      c.action!==frame.action || c.scope!==frame.scope ||
      !Array.isArray(c.conditions) ||
      c.conditions.length!==frame.required.length ||
      frame.required.some(r=>c.conditions.filter(x=>x.name===r.name).length!==1))
    return "ABSTAIN";
  const g=c.grant;
  if(!g || g.actor!==c.actor || g.action!==c.action ||
      g.scope!==c.scope || !Number.isSafeInteger(asOf))
    return "ABSTAIN";
  if(asOf>=g.expires_at || (g.revoked_at!==undefined &&
      g.revoked_at!==null && asOf>=g.revoked_at)) return "REFUSE";
  if(asOf<g.issued_at) return "ABSTAIN";
  const validNative=nativeReceipt?.state===frame.native_profile.state &&
    same(nativeReceipt?.subject,frame.native_profile.subject) &&
    Array.isArray(nativeReceipt?.observations);
  let unknown=false;
  for(const requirement of frame.required){
    const signed=c.conditions.find(x=>x.name===requirement.name);
    const native=validNative?nativeReceipt.observations.filter(o=>
      o.name===requirement.name && o.scope===frame.scope &&
      o.source===requirement.source):[];
    const observed=native.length===1 &&
      native[0].status===requirement.native_status ? native[0].status :
      "INSUFFICIENT";
    if(observed==="WARRANTED_FALSE") return "REFUSE";
    if(observed!=="WARRANTED_TRUE" || signed.status!=="WARRANTED_TRUE")
      unknown=true;
  }
  return unknown?"ABSTAIN":"ADMIT";
}
