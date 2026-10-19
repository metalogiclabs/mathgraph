// Deployment candidate wrapper, not yet the active Worker entrypoint.
// Uses existing HMAC validation and refuses to handle unsupported carriers.
// Preserves existing handler by default; no publication unless enabled.
import {createHmac,timingSafeEqual} from "node:crypto";
// Standalone shadow equivalent of the existing publisher HMAC/event guard.
// The actual production webhook is not present on this stacked research branch.
function signatureOK(raw,header,secret) {
 if(!secret || typeof header!=="string" || !/^sha256=[a-f0-9]{64}$/i.test(header))return false;
 const actual=Buffer.from(header.slice(7),"hex");
 const expected=createHmac("sha256",secret).update(raw).digest();
 return actual.length===expected.length && timingSafeEqual(actual,expected);
}
function accepted(event,action,repo,allow){
 return event==="pull_request" && ["opened","reopened","edited","synchronize","ready_for_review"].includes(action) && allow.has(repo);
}
import {handlePKCYamlSignedEvent} from "./pkc-yaml-webhook-bridge.mjs";
export async function processPKCYamlDelivery({raw,signature,event,action,
 payload,secret,allowRepos=[],enabled=false,githubAPI,token,
 appId=5308912,installed=false}={}) {
 const verified=raw instanceof Uint8Array &&
   signatureOK(raw,signature,secret);
 if(!verified)return {status:401,state:"DENY",reason:"INVALID_HMAC"};
 const repo=payload?.repository?.full_name;
 if(!accepted(event,action,repo,new Set(allowRepos)))
   return {status:202,state:"IGNORED"};
 const outcome=await handlePKCYamlSignedEvent({event,action,payload,
  signatureVerified:true,enabled,allowRepos,githubAPI,token,appId,installed});
 return {status:202,...outcome};
}
