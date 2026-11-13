// Optional guarded GitHub App webhook registration AFTER Cloudflare is ready.
// Requires explicit CF_HOOK_APPROVED; never sends secrets to a non-allowlisted host.
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { normalizePrivateKey, APP_CLIENT_ID } from "../app-authentication.mjs";
import { makeJWT } from "../webhook.mjs";
const APP_ID=5308912, OWNER="metalogiclabs", NAME="mathgraph-check-webhook-pilot";
function ensure(ok,code){if(!ok)throw Error(code);}
export async function activateWebhook({
  accountId,apiToken,privateKey,hookSecret,approveReplace=false,
  fetcher=fetch
}={}){
  ensure(/^[0-9a-f]{32}$/i.test(String(accountId||"")) &&
    typeof apiToken==="string" && apiToken.length>=10 &&
    typeof hookSecret==="string" && hookSecret.length>=24,
    "CLOUDFLARE_ACTIVATION_CREDENTIALS_INVALID");

  const cf=await fetcher("https://api.cloudflare.com/client/v4/accounts/"+
    accountId+"/workers/subdomain",{
      headers:{Authorization:"Bearer "+apiToken,Accept:"application/json"},
      signal:AbortSignal.timeout(15000)
    });
  ensure(cf.ok,"CLOUDFLARE_WORKER_SUBDOMAIN_UNAVAILABLE");
  const sub=await cf.json();
  ensure(sub?.success===true &&
    /^[a-z0-9][a-z0-9-]{0,62}$/i.test(sub.result?.subdomain||""),
    "CLOUDFLARE_WORKER_SUBDOMAIN_INVALID");
  const base="https://"+NAME+"."+sub.result.subdomain+".workers.dev";
  const ready=await fetcher(base+"/ready",{
    method:"GET",signal:AbortSignal.timeout(15000)
  });
  ensure(ready.status===200 && (await ready.text()).trim()==="ready",
    "CLOUDFLARE_WORKER_NOT_READY");
  const target=base+"/github/webhook";

  const pem=normalizePrivateKey(privateKey);
  const jwt=makeJWT(APP_CLIENT_ID,pem.key);
  const gh=async(method,path,body)=>{
    const headers={Authorization:"Bearer "+jwt,
      Accept:"application/vnd.github+json",
      "X-GitHub-Api-Version":"2022-11-28"};
    if(body)headers["Content-Type"]="application/json";
    const response=await fetcher("https://api.github.com"+path,{
      method,headers,body:body?JSON.stringify(body):undefined,
      signal:AbortSignal.timeout(15000)
    });
    ensure(response.ok,"GITHUB_APP_WEBHOOK_CONFIGURATION_HTTP_"+response.status);
    return response.json();
  };
  const app=await gh("GET","/app");
  ensure(app.id===APP_ID && app.owner?.login===OWNER,
    "WRONG_REGISTERED_APP_FOR_WEBHOOK");
  ensure(Array.isArray(app.events) && app.events.includes("pull_request"),
    "APP_PULL_REQUEST_EVENT_NOT_SUBSCRIBED");

  const previous=await gh("GET","/app/hook/config");
  const oldURL=String(previous?.url||"");
  if(oldURL && oldURL!==target && !approveReplace)
    throw Error("EXISTING_WEBHOOK_URL_REPLACEMENT_NOT_APPROVED");
  // No secret, PEM, token, or old configuration body is logged.
  const updated=await gh("PATCH","/app/hook/config",{
    url:target,content_type:"json",insecure_ssl:"0",secret:hookSecret
  });
  ensure(updated?.url===target && updated.content_type==="json" &&
    String(updated.insecure_ssl)==="0",
    "GITHUB_WEBHOOK_UPDATE_UNCONFIRMED");
  const after=await gh("GET","/app/hook/config");
  ensure(after?.url===target && after.content_type==="json" &&
    String(after.insecure_ssl)==="0",
    "GITHUB_WEBHOOK_READBACK_MISMATCH");
  return {app_id:APP_ID,target,configured:true,
    previous_url_replaced:!!oldURL && oldURL!==target,
    event_subscription:"pull_request",
    secret_verified_by_live_delivery:false};
}
if(process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  try{
    const r=await activateWebhook({
      accountId:process.env.CLOUDFLARE_ACCOUNT_ID,
      apiToken:process.env.CLOUDFLARE_API_TOKEN,
      privateKey:process.env.MATHGRAPH_CHECK_APP_PRIVATE_KEY,
      hookSecret:process.env.MATHGRAPH_CHECK_WEBHOOK_SECRET,
      approveReplace:process.env.MATHGRAPH_CF_HOOK_REPLACE_APPROVED==="true"
    });
    console.log("MATHGRAPH_APP_HOOK_CONFIGURED "+JSON.stringify(r));
  }catch(e){
    const code=/^[A-Z_0-9]+$/.test(String(e.message))?e.message:"WEBHOOK_CONFIG_FAILED";
    console.error("MATHGRAPH_APP_HOOK_NOT_QUALIFIED "+code);
    process.exitCode=1;
  }
}
