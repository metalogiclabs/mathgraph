// Deployment candidate wrapper, not yet the active Worker entrypoint.
// Uses existing HMAC validation and refuses to handle unsupported carriers.
// Preserves existing handler by default; no publication unless enabled.
import {signatureOK,accepted} from "./webhook.mjs";
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
