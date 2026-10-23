// Cloudflare R2 evidence journal; only trusted queued worker invokes this.
// R2 persists across Worker restarts. No proof of external immutability.
// Writes use per-event immutable keys; duplicates are idempotent after readback.
import {createHash} from "node:crypto";
const SHA=/^[a-f0-9]{40}$/;
export async function recordWarrantEvent(env,event){
 if(!env?.WARRANT_EVENTS||typeof env.WARRANT_EVENTS.put!=="function")
  throw Error("DURABLE_STORAGE_NOT_CONFIGURED");
 if(event?.schema!=="mathgraph.monitor.transition.v1"||
 !SHA.test(event.head_sha??"")||event.permission!=="ADVISORY_ONLY"||
 !["FIRST_OBSERVATION","EVIDENCE_CHANGED","EVIDENCE_UNCHANGED"].includes(event.kind)||
 !/^metalogiclabs\/[A-Za-z0-9_.-]+$/.test(event.repository??"")||
 !Number.isSafeInteger(event.pr)||event.pr<1)throw Error("INVALID_WARRANT_EVENT");
 const serialized=JSON.stringify(event);
 const digest=createHash("sha256").update(serialized).digest("hex");
 const key="v1/"+event.repository+"/"+event.pr+"/"+event.head_sha+"/"+digest+".json";
 const prior=await env.WARRANT_EVENTS.get(key);
 if(prior!==null){
  const saved=await prior.text();
  if(saved!==serialized)throw Error("DURABLE_DIGEST_COLLISION");
  return {state:"EXISTING",key,digest};
 }
 // R2 cannot atomically enforce unique-key inserts across concurrent writers.
 // This is append-style history, not globally exactly-once delivery.
 await env.WARRANT_EVENTS.put(key,serialized,{httpMetadata:{contentType:"application/json"}});
 const verify=await env.WARRANT_EVENTS.get(key);
 if(!verify||await verify.text()!==serialized)throw Error("DURABLE_READBACK_MISMATCH");
 return {state:"RECORDED",key,digest};
}
