// Read-only confirmation of actual GitHub App webhook delivery receipts.
// Uses the registered App JWT; never emits credentials or full webhook payload.
import { appendFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { normalizePrivateKey, APP_CLIENT_ID } from "./app-authentication.mjs";
import { makeJWT } from "./webhook.mjs";

const APP_ID=5308912, OWNER="metalogiclabs";
const TARGET_REPOSITORY="metalogiclabs/go-ethereum";
const TARGET_PR=18;
const TARGET_SHA="7c48a0811a21dad7ff192171e905663966e15c95";
const SINCE="2026-10-14T00:00:00Z";
const MAX_CANDIDATES=25;
function requireResult(value,code) { if(!value) throw new Error(code); }

export async function auditSignedDeliveryReceipts({
  privateKey,
  fetcher=fetch,
  since=SINCE
}={}) {
  const key=normalizePrivateKey(privateKey).key;
  const jwt=makeJWT(APP_CLIENT_ID,key);
  const call=async(path)=>{
    requireResult(path==="/app" ||
      path==="/app/hook/deliveries?per_page=100" ||
      /^\/app\/hook\/deliveries\/[1-9]\d*$/.test(path),
      "UNAUTHORIZED_DELIVERY_AUDIT_PATH");
    const r=await fetcher("https://api.github.com"+path,{
      method:"GET",headers:{
        "Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28",
        "User-Agent":"MathGraph-App-Webhook-Receipt-Audit",
        Authorization:"Bearer "+jwt
      },signal:AbortSignal.timeout(15000)
    });
    requireResult(r.ok,"GITHUB_DELIVERIES_READ_HTTP_"+r.status);
    const raw=await r.text();
    // Delivery IDs can exceed Number.MAX_SAFE_INTEGER. Preserve GitHub's
    // original decimal bytes before JSON.parse loses precision.
    const lossless=path.startsWith("/app/hook/deliveries") ?
      raw.replace(/("id"\s*:\s*)([1-9]\d{15,})/g,'$1"$2"') : raw;
    return JSON.parse(lossless);
  };
  const app=await call("/app");
  requireResult(app.id===APP_ID && app.owner?.login===OWNER,
    "WRONG_REGISTERED_APP_IDENTITY");
  const listing=await call("/app/hook/deliveries?per_page=100");
  requireResult(Array.isArray(listing) && listing.length<=100,
    "GITHUB_DELIVERIES_LIST_INVALID");

  if (process.env.MATHGRAPH_RECEIPT_AUDIT_DIAGNOSTIC==="true") {
    console.log("MATHGRAPH_RECEIPT_LIST_METADATA "+JSON.stringify({
      total:listing.length,
      newest:listing.slice(0,20).map(x=>({
        id:x.id,event:x.event,action:x.action,
        status_code:x.status_code,delivered_at:x.delivered_at,
        redelivery:x.redelivery
      }))
    }));
  }

  const candidates=listing.filter(x=>
    x.event==="pull_request" &&
    x.action==="edited" &&
    typeof x.delivered_at==="string" &&
    x.delivered_at>=since &&
    /^[1-9]\d{0,30}$/.test(String(x.id))
  ).slice(0,MAX_CANDIDATES);
  const receipts=[];
  for(const summary of candidates) {
    const detail=await call("/app/hook/deliveries/"+summary.id);
    const payload=detail.request?.payload;
    if (process.env.MATHGRAPH_RECEIPT_AUDIT_DIAGNOSTIC==="true") {
      console.log("MATHGRAPH_RECEIPT_DETAIL_SHAPE "+JSON.stringify({
        id:summary.id,
        payload_present:payload!==undefined && payload!==null,
        payload_type:typeof payload,
        payload_field_names:payload && typeof payload==="object" ?
          Object.keys(payload).slice(0,18):[],
        repo_match:payload?.repository?.full_name===TARGET_REPOSITORY,
        pr_number_top:payload?.number===TARGET_PR,
        pr_number_nested:payload?.pull_request?.number===TARGET_PR,
        sha_match:payload?.pull_request?.head?.sha===TARGET_SHA,
        status_code:detail.status_code??summary.status_code
      }));
    }
    if(payload?.repository?.full_name!==TARGET_REPOSITORY ||
      payload?.pull_request?.number!==TARGET_PR ||
      payload?.pull_request?.head?.sha!==TARGET_SHA)
      continue;
    const status=Number(detail.status_code??summary.status_code);
    const match={
      id:summary.id,
      guid:String(summary.guid||detail.guid||""),
      delivered_at:summary.delivered_at,
      event:"pull_request",
      action:"edited",
      status_code:status,
      accepted_by_webhook:status===202,
      redelivery:summary.redelivery===true,
      repository:TARGET_REPOSITORY,pr:TARGET_PR,sha:TARGET_SHA
    };
    requireResult(/^[a-f0-9-]{16,80}$/i.test(match.guid),
      "DELIVERY_GUID_INVALID");
    receipts.push(match);
  }
  requireResult(receipts.some(x=>x.accepted_by_webhook),
    "NO_GITHUB_ACCEPTED_PR18_SIGNED_DELIVERY");
  return {
    authority:"GITHUB_APP_DELIVERY_RECEIPT",
    app_id:APP_ID,
    repository:TARGET_REPOSITORY,pr:TARGET_PR,sha:TARGET_SHA,
    candidate_window:candidates.length,
    receipts
  };
}

if(process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  try {
    const result=await auditSignedDeliveryReceipts({
      privateKey:process.env.MATHGRAPH_CHECK_APP_PRIVATE_KEY
    });
    console.log("MATHGRAPH_LIVE_HOOK_RECEIPTS "+JSON.stringify(result));
    if(process.env.GITHUB_STEP_SUMMARY) {
      appendFileSync(process.env.GITHUB_STEP_SUMMARY,
        "### GitHub App's actual pull_request delivery receipts\n" +
        "App ID: "+result.app_id+"; PR: "+result.pr+
        "; SHA: "+result.sha+"\n"+
        result.receipts.map(x=>
          "Delivery "+x.id+" | "+x.delivered_at+" | HTTP "+
          x.status_code+" | "+x.event+"."+x.action+
          " | accepted="+x.accepted_by_webhook).join("\n")+
        "\n\nFull webhook payloads and credentials were not logged.\n");
    }
  }catch(error){
    // Errors must remain stable, never expose request/response bodies or auth.
    const raw=String(error.message||"UNKNOWN");
    const code=/^[A-Z0-9_]+$/.test(raw)?raw:"UNEXPECTED_DELIVERY_AUDIT_FAILURE";
    console.error("MATHGRAPH_DELIVERY_AUDIT_UNQUALIFIED "+code);
    process.exitCode=1;
  }
}
