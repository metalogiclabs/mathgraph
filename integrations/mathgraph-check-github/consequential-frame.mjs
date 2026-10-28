// Research-only independent obligation frame for a source-bound owner packet.
// The caller must independently verify the owner signature and obtain the
// nativeReceipt from its *trusted* source-pinned adapter. This module never
// authenticates a human policy owner or authorizes a GitHub/release action.
import {createHash} from "node:crypto";
import {assessWarrant} from "./warrant.mjs";

const BOUNDARY="FROZEN_RESEARCH_FRAME_ADVISORY_ONLY";
const SHA=/^[a-f0-9]{40}$/i;
const SHA256=/^[a-f0-9]{64}$/i;
const REPO=/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
const NAME=/^[a-z][a-z0-9_]{0,79}$/;
const IDENT=/^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}$/;
const STATES=new Set(["WARRANTED_TRUE","WARRANTED_FALSE","INSUFFICIENT"]);
const same=(a,b)=>a?.repository===b?.repository &&
  a?.pr===b?.pr && a?.sha===b?.sha;
const code=name=>name.toUpperCase();
const deny=(reason)=>({boundary:BOUNDARY,decision:"ABSTAIN",
  residuals:[{code:reason}],future:{grant_expires_at:null},
  evidence:[],missing_observations:[],native_profile:null,source:null});

function validFrame(f) {
  if (!f || typeof f!=="object" || Array.isArray(f) ||
      f.schema!=="mathgraph.consequential-research-frame.v1" ||
      f.authority!=="FROZEN_RESEARCH_ORACLE_ONLY" ||
      !REPO.test(f.subject?.repository||"") ||
      !Number.isSafeInteger(f.subject?.pr) || f.subject.pr<1 ||
      !SHA.test(f.subject?.sha||"") ||
      !IDENT.test(f.policy_version||"") || !IDENT.test(f.action||"") ||
      !IDENT.test(f.scope||"") ||
      !/^WARRANTED_BOUNDED_[A-Z0-9_]+$/.test(f.native_profile?.state||"") ||
      !same(f.native_profile?.subject,f.subject) ||
      !Array.isArray(f.required) || f.required.length===0 ||
      f.required.length>64) return false;
  const seen=new Set();
  for(const r of f.required){
    if(!r || !NAME.test(r.name||"") || seen.has(r.name) ||
        !IDENT.test(r.source||"") || !STATES.has(r.native_status))
      return false;
    seen.add(r.name);
  }
  return true;
}

export function assessConsequentialFrame({
  snapshot,verifiedOwner,frameBytes,frameSha256,nativeReceipt,asOf
}={}){
  if(typeof frameBytes!=="string" || Buffer.byteLength(frameBytes)>65536 ||
      typeof frameSha256!=="string" || !SHA256.test(frameSha256) ||
      createHash("sha256").update(frameBytes).digest("hex")!==frameSha256)
    return deny("UNRESOLVED_FRAME_DIGEST");
  let f;
  try{f=JSON.parse(frameBytes)}catch{return deny("UNRESOLVED_FRAME_SCHEMA");}
  // Duplicate JSON keys/alternative encodings cannot define competing frames.
  if(JSON.stringify(f)!==frameBytes || !validFrame(f))
    return deny("UNRESOLVED_FRAME_SCHEMA");
  if(!snapshot || !same({repository:snapshot.repository,
    pr:snapshot.number,sha:snapshot.sha},f.subject))
    return deny("UNRESOLVED_FRAME_SUBJECT");
  if(verifiedOwner?.verified!==true || !verifiedOwner.contract)
    return deny(verifiedOwner?.code||"UNRESOLVED_OWNER_SIGNATURE");
  const c=verifiedOwner.contract;
  if(!same(c.subject,f.subject) || c.policy_version!==f.policy_version ||
      c.action!==f.action || c.scope!==f.scope)
    return deny("UNRESOLVED_FRAME_POLICY_BINDING");
  if(!Array.isArray(c.conditions) || c.conditions.length!==f.required.length ||
      new Set(c.conditions.map(x=>x?.name)).size!==f.required.length ||
      c.conditions.some(x=>x?.scope!==f.scope) ||
      f.required.some(r=>!c.conditions.some(x=>x?.name===r.name)))
    return deny("UNRESOLVED_OBLIGATION_FRAME_INCOMPLETE");

  const nativeQualified=Boolean(nativeReceipt &&
    nativeReceipt.state===f.native_profile.state &&
    same(nativeReceipt.subject,f.native_profile.subject) &&
    Array.isArray(nativeReceipt.observations) &&
    nativeReceipt.observations.length<=64 &&
    nativeReceipt.observations.every(o=>o && NAME.test(o.name||"") &&
      IDENT.test(o.source||"") && o.scope===f.scope &&
      STATES.has(o.status)) &&
    new Set(nativeReceipt.observations.map(o=>o.name)).size===
      nativeReceipt.observations.length);
  const observationByName=new Map(nativeQualified?
    nativeReceipt.observations.map(o=>[o.name,o]):[]);
  const qualified=f.required.flatMap(r=>{
    const o=observationByName.get(r.name);
    if(!o || o.source!==r.source || r.native_status==="INSUFFICIENT")
      return [];
    // The frozen frame is a conservative ceiling; adapter observations are
    // a separate necessary input. Neither side alone can make a TRUE/FALSE.
    const status=o.status===r.native_status ? o.status : "CONFLICTING";
    return [{name:r.name,scope:f.scope,source:r.source,status}];
  });
  // Delegate the actual policy/obligation decision to the existing V0
  // protected-frame kernel. This adapter adds exact-byte research pins and
  // native-envelope scope binding, not another trusted decision semantics.
  const protectedFrame={schema:"mathgraph.protected-frame.v0",
    subject:f.subject,policy_version:f.policy_version,
    action:f.action,scope:f.scope,
    requirements:f.required.map(r=>({name:r.name,scope:f.scope,
      on_false:"FAIL_"+code(r.name),
      on_unresolved:"UNRESOLVED_"+code(r.name)})),
    qualified};
  const result=assessWarrant(snapshot,c,asOf,protectedFrame);
  const evidence=result.evidence||[];
  return {...result,boundary:BOUNDARY,
    decision_kernel:"PROTECTED_FRAME_V0",
    native_profile:{state:f.native_profile.state,
      qualified:nativeQualified},
    source:structuredClone(f.subject),evidence,
    missing_observations:evidence.filter(x=>
      x.status!=="WARRANTED_TRUE" && x.status!=="WARRANTED_FALSE")
      .map(x=>x.name)};
}
