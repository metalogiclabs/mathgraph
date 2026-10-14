// Read-only acceptance of the genuine GitHub->Cloudflare pull_request delivery.
// JWT and webhook secrets are never printed or persisted. This script does NOT redeliver.
// Only reports signed-delivery metadata and the first-party PR #20 head identity.
import { normalizePrivateKey, APP_CLIENT_ID } from "./app-authentication.mjs";
import { makeJWT } from "./webhook.mjs";

const APP_ID=5308912;
const REPOSITORY="metalogiclabs/go-ethereum";
const REPO_ID=1399674070;
const PR=20;
const SHA="b57c5493d2bc066c184cbc9335bdf635f045a026";
const TARGET="https://mathgraph-check-webhook-pilot.metalogiclabs-check.workers.dev/github/webhook";
const EARLIEST="2026-10-14T10:42:13Z";

function need(ok, code) { if(!ok) throw Error(code); }
async function getJSON(path, jwt) {
  need(/^\/app(?:\/hook\/(?:config|deliveries(?:\/\d+)?))?(?:\?per_page=100)?$/.test(path),
    "UNAUTHORIZED_READBACK_PATH");
  const response=await fetch("https://api.github.com"+path,{
    headers:{"Accept":"application/vnd.github+json",
      "Authorization":"Bearer "+jwt,
      "User-Agent":"MathGraph-Check-Live-Delivery-Audit",
      "X-GitHub-Api-Version":"2022-11-28"},
    signal:AbortSignal.timeout(20000)
  });
  const endpointLabel=path==="/app"?"APP":
    path==="/app/hook/config"?"HOOK_CONFIG":
    path.startsWith("/app/hook/deliveries/")?"DELIVERY_DETAIL":"DELIVERY_LIST";
  need(response.ok,"GITHUB_"+endpointLabel+"_HTTP_"+response.status);
  return response.json();
}
async function verify() {
  const material=normalizePrivateKey(process.env.MATHGRAPH_CHECK_APP_PRIVATE_KEY);
  const jwt=makeJWT(APP_CLIENT_ID,material.key);
  const app=await getJSON("/app",jwt);
  need(app?.id===APP_ID && app.owner?.login==="metalogiclabs",
    "REGISTERED_APP_IDENTITY_MISMATCH");
  need(Array.isArray(app.events) && app.events.includes("pull_request"),
    "PULL_REQUEST_SUBSCRIPTION_MISSING");
  const config=await getJSON("/app/hook/config",jwt);
  need(config.url===TARGET && config.content_type==="json" &&
       String(config.insecure_ssl)==="0",
    "GITHUB_HOOK_CONFIG_MISMATCH");
  // Never serialize 'config' -- GitHub's response can contain a masked secret.
  const ready=await fetch(TARGET.replace(/\/github\/webhook$/,"/ready"),{
    signal:AbortSignal.timeout(20000)});
  need(ready.status===200,"CLOUDFLARE_NOT_READY_"+ready.status);

  const deliveries=await getJSON("/app/hook/deliveries?per_page=100",jwt);
  need(Array.isArray(deliveries),"APP_DELIVERY_LIST_UNAVAILABLE");
  const plausible=deliveries.filter(x=>
    x.repository_id===REPO_ID && x.event==="pull_request" &&
    x.action==="opened" && x.delivered_at>=EARLIEST);
  need(plausible.length>0,"OWNED_PR_DELIVERY_NOT_OBSERVED");
  let accepted=null;
  for(const summary of plausible.slice(0,12)) {
    const entry=await getJSON("/app/hook/deliveries/"+summary.id,jwt);
    const raw=entry.request?.payload;
    const payload=typeof raw==="string"?JSON.parse(raw):raw;
    if(payload?.repository?.full_name!==REPOSITORY ||
       payload?.pull_request?.number!==PR ||
       payload?.pull_request?.head?.sha!==SHA) continue;
    need(entry.id===summary.id && entry.status_code===202 &&
         entry.event==="pull_request" && entry.action==="opened" &&
         entry.repository_id===REPO_ID,
      "OWNED_PR_DELIVERY_NOT_ACCEPTED");
    need(String(entry.request?.headers?.["X-Hub-Signature-256"]||
        entry.request?.headers?.["x-hub-signature-256"]||"")
        .match(/^sha256=[a-f0-9]{64}$/i),
      "DELIVERY_HMAC_HEADER_NOT_OBSERVED");
    need(entry.url===TARGET,"DELIVERY_TARGET_DIFFERENT");
    accepted={deliveryId:entry.id,statusCode:entry.status_code,
      deliveredAt:entry.delivered_at,
      event:entry.event,action:entry.action,
      appId:APP_ID,repo:REPOSITORY,pr:PR,head:SHA,
      workerReady:true,
      workflowRunSubscribed:app.events.includes("workflow_run")};
    break;
  }
  need(accepted!==null,"EXACT_PR20_SIGNED_DELIVERY_NOT_FOUND");
  console.log("MATHGRAPH_CHECK_LIVE_WEBHOOK_DELIVERY_VERIFIED "+
    JSON.stringify(accepted));
}
try { await verify(); }
catch(e) {
  const msg=String(e?.message??"UNKNOWN");
  console.error("MATHGRAPH_CHECK_LIVE_DELIVERY_NOT_QUALIFIED "+
    (/^[A-Z0-9_]+$/.test(msg)?msg:"AUDIT_FAILED"));
  process.exitCode=1;
}
