// MathGraph Check: Cloudflare Worker HTTP ingress + Queues consumer.
// GitHub's signed bytes are the sole trust source for queue production.
// The native Check remains advisory and source/commit pinned.
import { createHmac, timingSafeEqual, createPrivateKey, sign } from "node:crypto";
import { Buffer } from "node:buffer";
import { analyze, checkOutput } from "../analysis.mjs";
import { appendGethV19NativeEvidence } from "../geth-v19-evidence.mjs";
import { appendExternalNativeReceipt } from "../external-native-receipt.mjs";

export const SCOPE = Object.freeze({
  appID: 5308912,
  clientID: "Iv23lioiUs5KfHD7mkkw",
  owner: "metalogiclabs",
  repository: "metalogiclabs/go-ethereum",
  checkName: "MathGraph Check / evidence scope",
  maxBodyBytes: 1000000,
  maxFiles: 300
});
const SHA = /^[0-9a-f]{40}$/i;
const UUID = /^[0-9a-f-]{16,80}$/i;
const PR_ACTIONS = new Set([
  "opened", "reopened", "synchronize", "ready_for_review", "edited"
]);
const QUEUE_ACTIONS = new Set([...PR_ACTIONS,"ci_completed","ci_recheck"]);
// Signed PR delivery remains the sole external authority. This limited
// internal queue follow-up handles mutable CI evidence without a webhook
// subscription to workflow_run.completed. Never poll indefinitely.
const CI_RECHECK_MAX = 4;
const CI_RECHECK_BASE_DELAY_SECONDS = 60;
const PERMS = { checks: "write", pull_requests: "read", actions: "read" };

function ensure(ok, code) {
  if (!ok) throw new Error(code);
}
function bearer(token) {
  ensure(typeof token === "string" && token.length > 0, "MISSING_GITHUB_AUTH");
  return {
    Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "MathGraph-Check-Cloudflare-Pilot",
    Authorization: "Bearer " + token
  };
}

export function verifyWebhookBytes(bytes, signature, secret) {
  if (!secret || typeof signature !== "string" ||
      !/^sha256=[0-9a-f]{64}$/i.test(signature)) return false;
  const digest = createHmac("sha256", secret).update(bytes).digest();
  const actual = Buffer.from(signature.slice(7), "hex");
  return actual.length === digest.length && timingSafeEqual(actual, digest);
}

export function parseSignedEvent(payload, delivery, eventName) {
  if (!UUID.test(String(delivery || "")) ||
      payload?.repository?.full_name!==SCOPE.repository)
    return null;
  const installationID=payload.installation?.id;
  if (!Number.isSafeInteger(installationID) || installationID<1)
    return null;
  let number,sha,action;
  if (eventName==="pull_request" && PR_ACTIONS.has(payload.action)) {
    const pr=payload.pull_request;
    if (pr?.base?.repo?.full_name!==SCOPE.repository ||
        pr?.head?.repo?.full_name!==SCOPE.repository) return null;
    number=pr.number;
    sha=pr.head.sha;
    action=payload.action;
  } else if (eventName==="workflow_run" && payload.action==="completed") {
    // GitHub Apps can subscribe with Actions:read. A workflow completion is
    // the missing input when CI standing changes without a new commit.
    // Only an unambiguously associated exact-source first-party PR is eligible.
    const run=payload.workflow_run;
    const prs=run?.pull_requests;
    if (run?.event!=="pull_request" ||
        run?.head_repository?.full_name!==SCOPE.repository ||
        !Array.isArray(prs) || prs.length!==1) return null;
    const pr=prs[0];
    if (pr?.base?.repo?.full_name!==SCOPE.repository ||
        pr?.head?.repo?.full_name!==SCOPE.repository ||
        pr?.head?.sha!==run.head_sha) return null;
    number=pr.number;
    sha=run.head_sha;
    action="ci_completed";
  } else {
    return null;
  }
  if (!Number.isSafeInteger(number) || number<1 ||
      !SHA.test(sha || "")) return null;
  // GitHub-signed input is narrowed to one replayable, source-pinned action.
  // The consumer always rechecks live PR HEAD/CI through the GitHub API.
  return {
    schema:"mathgraph.github-pr-delivery.v0",
    repository:SCOPE.repository,number,installationID,
    sha,delivery,action
  };
}

export async function receiveWebhook(request, env) {
  const url = new URL(request.url);
  if (request.method === "GET" && url.pathname === "/health")
    return new Response(JSON.stringify({
      status: "alive", name: "mathgraph-check-webhook-pilot"
    }), { status: 200, headers: { "content-type":"application/json" } });
  if (request.method === "GET" && url.pathname === "/ready") {
    let configured=!!(env?.GITHUB_WEBHOOK_SECRET && env?.GITHUB_APP_PRIVATE_KEY &&
      env?.PR_EVENTS && env?.GITHUB_APP_CLIENT_ID===SCOPE.clientID &&
      String(env?.GITHUB_APP_ID)===String(SCOPE.appID));
    if(configured){
      try { configured=createPrivateKey(env.GITHUB_APP_PRIVATE_KEY).asymmetricKeyType==="rsa"; }
      catch { configured=false; }
    }
    return new Response(configured?"ready":"not configured",{
      status:configured?200:503
    });
  }
  if (request.method !== "POST" || url.pathname !== "/github/webhook")
    return new Response("Not found", { status: 404 });

  if (!env?.GITHUB_WEBHOOK_SECRET || !env?.PR_EVENTS)
    return new Response("Service not configured", { status: 503 });
  if (Number(request.headers.get("content-length")) > SCOPE.maxBodyBytes)
    return new Response("Request too large", { status: 413 });
  const bytes = Buffer.from(await request.arrayBuffer());
  if (bytes.length > SCOPE.maxBodyBytes)
    return new Response("Request too large", { status: 413 });
  if (!verifyWebhookBytes(bytes,
    request.headers.get("x-hub-signature-256"),env.GITHUB_WEBHOOK_SECRET))
    return new Response("Invalid signature", { status: 401 });
  let payload;
  try { payload=JSON.parse(bytes.toString("utf8")); }
  catch { return new Response("Invalid JSON", { status: 400 }); }

  const item = parseSignedEvent(payload,
    request.headers.get("x-github-delivery"),
    request.headers.get("x-github-event"));
  if (!item) return new Response("Ignored", { status: 202 });
  try {
    // Acknowledge only after durable queue acceptance, not before it.
    await env.PR_EVENTS.send(item);
    return new Response("Queued", { status: 202 });
  } catch {
    return new Response("Queue unavailable", { status: 503 });
  }
}

export function appJWT(privateKey) {
  ensure(typeof privateKey === "string" && privateKey.length > 300,
    "GITHUB_APP_SECRET_MISSING");
  let key;
  try { key = createPrivateKey(privateKey.replace(/\\n/g, "\n")); }
  catch { throw new Error("GITHUB_APP_PRIVATE_KEY_INVALID"); }
  ensure(key.asymmetricKeyType === "rsa", "GITHUB_APP_KEY_NOT_RSA");
  const now = Math.floor(Date.now()/1000);
  const enc = obj => Buffer.from(JSON.stringify(obj)).toString("base64url");
  const header=enc({alg:"RS256",typ:"JWT"});
  const claims=enc({iat:now-60,exp:now+540,iss:SCOPE.clientID});
  const signingInput=header+"."+claims;
  return signingInput+"."+sign("RSA-SHA256",
    Buffer.from(signingInput),key).toString("base64url");
}

export async function gh(path, token, {
  method="GET", body, fetcher=fetch
} = {}) {
  ensure(path.startsWith("/repos/"+SCOPE.repository+"/") ||
    path === "/app" || path === "/installation/token" ||
    /^\/app\/installations\/[1-9][0-9]*\/access_tokens$/.test(path),
    "DISALLOWED_GITHUB_API_PATH");
  const headers=bearer(token);
  if (body !== undefined) headers["Content-Type"]="application/json";
  const response=await fetcher("https://api.github.com"+path,{
    method,headers,body:body===undefined?undefined:JSON.stringify(body),
    signal:AbortSignal.timeout(20000)
  });
  if (!response.ok) {
    const e=new Error("GITHUB_HTTP_"+response.status);
    e.status=response.status;
    throw e;
  }
  if (response.status===204) return {revoked:true};
  return response.json();
}

function permissionsOK(perms) {
  return !!perms && perms.checks==="write" &&
    ["read","write"].includes(perms.pull_requests) &&
    ["read","write"].includes(perms.actions);
}

function validQueueItem(item) {
  return !!item && item.schema==="mathgraph.github-pr-delivery.v0" &&
    item.repository===SCOPE.repository &&
    Number.isSafeInteger(item.number) && item.number>0 &&
    Number.isSafeInteger(item.installationID) && item.installationID>0 &&
    SHA.test(item.sha || "") &&
    UUID.test(String(item.delivery || "")) &&
    QUEUE_ACTIONS.has(item.action) &&
    (item.action==="ci_recheck" ?
      Number.isSafeInteger(item.ciRecheckAttempt) &&
      item.ciRecheckAttempt>=1 && item.ciRecheckAttempt<=CI_RECHECK_MAX :
      item.ciRecheckAttempt===undefined);
}
async function getSnapshot(item, token, api) {
  const root="/repos/"+SCOPE.repository;
  const pr=await api(root+"/pulls/"+item.number,token);
  if (pr?.head?.sha!==item.sha || pr.state!=="open") return null;
  if (pr.base?.repo?.full_name!==SCOPE.repository ||
      pr.head?.repo?.full_name!==SCOPE.repository) return null;
  const files=[];
  let files_visibility="COMPLETE";
  for(let page=1;page<=3;page++){
    const batch=await api(root+"/pulls/"+item.number+
      "/files?per_page=100&page="+page,token);
    ensure(Array.isArray(batch) && batch.length<=100,"PR_FILES_API_INVALID");
    files.push(...batch);
    if (batch.length<100) break;
    if (page===3) files_visibility="TRUNCATED_AT_300";
  }
  let runs=[],ci_visibility="COMPLETE";
  try {
    const response=await api(root+"/actions/runs?head_sha="+item.sha+
      "&per_page=100",token);
    ensure(Array.isArray(response?.workflow_runs),
      "PR_ACTIONS_API_INVALID");
    runs=response.workflow_runs;
    if (!Number.isSafeInteger(response.total_count) ||
        response.total_count>runs.length)
      ci_visibility="INCOMPLETE_RUN_WINDOW";
  }catch(e){
    if (e.status===403 || e.status===404)
      ci_visibility="UNKNOWN_NO_ACTIONS_ACCESS";
    else throw e;
  }
  return {repository:SCOPE.repository,number:item.number,
    sha:item.sha,files,runs,files_visibility,ci_visibility};
}

// Point the GitHub mobile/browser details action at the *native* evidence
// report. An omitted details_url defaults to the App's generic homepage.
function nativeDetailsURL(id) {
  ensure(Number.isSafeInteger(id) && id > 0, "CHECK_ID_INVALID");
  return "https://github.com/" + SCOPE.repository + "/runs/" + id;
}

async function existingChecks(item,token,api) {
  const name=SCOPE.checkName;
  const path="/repos/"+SCOPE.repository+"/commits/"+item.sha+
    "/check-runs?per_page=100&filter=all&check_name="+encodeURIComponent(name);
  const result=await api(path,token);
  ensure(Array.isArray(result?.check_runs) &&
    Number.isSafeInteger(result.total_count) &&
    result.total_count<=result.check_runs.length,
    "CHECK_RUN_RECONCILIATION_INCOMPLETE");
  const externalId=SCOPE.repository+"#"+item.number+"@"+item.sha;
  return result.check_runs.filter(c=>
    c.name===name && c.app?.id===SCOPE.appID && c.external_id===externalId);
}

export async function processQueuedPR(item,env,{fetcher=fetch}={}) {
  if (!validQueueItem(item)) return {outcome:"IGNORED_INVALID_EVENT"};
  ensure(env?.GITHUB_APP_PRIVATE_KEY && env?.GITHUB_APP_CLIENT_ID===SCOPE.clientID &&
    String(env.GITHUB_APP_ID)===String(SCOPE.appID),
    "APP_WORKER_CONFIGURATION_INVALID");
  const api=(path,token,opts={})=>gh(path,token,{...opts,fetcher});
  const jwt=appJWT(env.GITHUB_APP_PRIVATE_KEY);
  const app=await api("/app",jwt);
  ensure(app.id===SCOPE.appID && app.owner?.login===SCOPE.owner &&
    permissionsOK(app.permissions),"REGISTERED_APP_IDENTITY_INVALID");
  const root="/repos/"+SCOPE.repository;
  const installation=await api(root+"/installation",jwt);
  ensure(installation?.id===item.installationID &&
    installation.app_id===SCOPE.appID &&
    installation.account?.login===SCOPE.owner &&
    !installation.suspended_at &&
    permissionsOK(installation.permissions),
    "SIGNED_EVENT_INSTALLATION_INVALID");
  const minted=await api("/app/installations/"+installation.id+
    "/access_tokens",jwt,{
      method:"POST",
      body:{repositories:["go-ethereum"],permissions:PERMS}
    });
  ensure(typeof minted?.token==="string" && minted.token.length>=10 &&
    permissionsOK(minted.permissions),"SCOPED_APP_TOKEN_NOT_ISSUED");
  const token=minted.token;
  let result,failed,revokeOK=false,pendingCI=false;
  try {
    // A commit SHA is immutable; PR context and exact-head CI evidence are
    // not. Do not return EXISTING before re-reading the current evidence.
    const matches=await existingChecks(item,token,api);
    ensure(matches.length<=1,"DUPLICATE_APP_CHECK_AUTHORITY");
    const previous=matches[0];
    if(previous){
      ensure(Number.isSafeInteger(previous.id) && previous.id>0 &&
        previous.head_sha===item.sha &&
        previous.status==="completed" && previous.conclusion==="neutral",
        "PREVIOUS_APP_CHECK_INVALID");
    }
    const snapshot=await getSnapshot(item,token,api);
    if(!snapshot){
      result={outcome:"STALE"};
    }else{
      const substantive=snapshot.runs.filter(r=>
        r?.head_sha===item.sha && typeof r.name==="string" &&
        !/^(PR Format Validation|MathGraph Check(\s|\/|$))/i.test(r.name));
      // A source SHA does not freeze its CI standing. Recheck only when
      // substantive CI is absent or still running. Completed failures are
      // terminal UNRESOLVED until another genuine source event.
      pendingCI=snapshot.ci_visibility==="COMPLETE" &&
        (substantive.length===0 ||
          substantive.some(r=>r.status!=="completed"));
      const report=analyze(snapshot);
      ensure(report.authority==="ADVISORY_ONLY" &&
        report.source.sha===item.sha,"CHECK_AUTHORITY_MISMATCH");
      const genericCheck=checkOutput(report);
      const nativeEvidence=await appendGethV19NativeEvidence(report,genericCheck,api,token);
      // The external receipt belongs to goccy/go-yaml, NOT to go-ethereum.
      // The App checks a pinned carrier manifest and public native metadata,
      // never transferring external correctness claims to this PR's code.
      const external=await appendExternalNativeReceipt(
        report,nativeEvidence.check,api,token,snapshot,{fetcher});
      const check=external.check;
      ensure(check.conclusion==="neutral" && check.status==="completed" &&
        check.name===SCOPE.checkName,"FORBIDDEN_TRUTH_PROMOTION");

      // Reconfirm the original PR/HEAD before creating OR updating authority.
      const fresh=await api(root+"/pulls/"+item.number,token);
      if(fresh?.head?.sha!==item.sha || fresh.state!=="open" ||
          fresh.head?.repo?.full_name!==SCOPE.repository ||
          fresh.base?.repo?.full_name!==SCOPE.repository){
        result={outcome:"STALE"};
      }else if(previous){
        const same=previous.output?.title===check.output.title &&
          previous.output?.summary===check.output.summary;
        const detailsURL=nativeDetailsURL(previous.id);
        if(same && previous.details_url===detailsURL){
          result={outcome:"EXISTING",checkID:previous.id};
        }else{
          // A check can have unchanged evidence but an invalid homepage
          // link. Repair navigation on the *same* App-owned Check ID,
          // without changing the evidence or verdict.
          const patch=same ? {details_url:detailsURL} : {
            details_url:detailsURL,
            status:"completed",conclusion:"neutral",output:check.output
          };
          const changed=await api(root+"/check-runs/"+previous.id,token,{
            method:"PATCH",body:patch
          });
          ensure(changed?.id===previous.id && changed.app?.id===SCOPE.appID &&
            changed.head_sha===item.sha && changed.status==="completed" &&
            changed.conclusion==="neutral" &&
            changed.details_url===detailsURL,
            "CHECK_DETAILS_OR_REFRESH_IDENTITY_NOT_CONFIRMED");
          const readback=await existingChecks(item,token,api);
          ensure(readback.length===1 && readback[0].id===previous.id &&
            readback[0].head_sha===item.sha &&
            readback[0].status==="completed" &&
            readback[0].conclusion==="neutral" &&
            readback[0].details_url===detailsURL &&
            readback[0].output?.title===check.output.title &&
            readback[0].output?.summary===check.output.summary,
            "CHECK_DETAILS_OR_REFRESH_READBACK_MISMATCH");
          result={outcome:same?"LINK_REPAIRED":"UPDATED",checkID:previous.id,
            finding:report.finding.code};
        }
      }else{
        const externalID=SCOPE.repository+"#"+item.number+"@"+item.sha;
        const written=await api(root+"/check-runs",token,{
          method:"POST",
          body:{...check,head_sha:item.sha,external_id:externalID}
        });
        ensure(Number.isSafeInteger(written?.id) &&
          written.app?.id===SCOPE.appID &&
          written.head_sha===item.sha &&
          written.status==="completed" && written.conclusion==="neutral",
          "CHECK_POST_IDENTITY_NOT_CONFIRMED");
        // The native check ID is assigned only after POST. Bind its
        // details link to that exact GitHub evidence report immediately.
        const detailsURL=nativeDetailsURL(written.id);
        const linked=await api(root+"/check-runs/"+written.id,token,{
          method:"PATCH",body:{details_url:detailsURL}
        });
        ensure(linked?.id===written.id && linked.app?.id===SCOPE.appID &&
          linked.head_sha===item.sha && linked.status==="completed" &&
          linked.conclusion==="neutral" && linked.details_url===detailsURL,
          "CHECK_DETAILS_LINK_PATCH_NOT_CONFIRMED");
        const readback=await existingChecks(item,token,api);
        ensure(readback.length===1 && readback[0].id===written.id &&
          readback[0].head_sha===item.sha &&
          readback[0].status==="completed" &&
          readback[0].conclusion==="neutral" &&
          readback[0].details_url===detailsURL,
          "CHECK_DETAILS_LINK_READBACK_NOT_CONFIRMED");
        result={outcome:"CREATED",checkID:written.id,
          finding:report.finding.code};
      }
    }
  }catch(error){failed=error;}
  finally{
    try{
      const revoke=await api("/installation/token",token,{method:"DELETE"});
      revokeOK=revoke.revoked===true;
    }catch{revokeOK=false;}
  }
  if(failed)throw failed;
  ensure(revokeOK,"TOKEN_REVOCATION_NOT_VERIFIED");
  return { ...result,repository:SCOPE.repository,number:item.number,sha:item.sha,
    appID:SCOPE.appID,tokenRevoked:true,pendingCI};
}

export async function consumePRQueue(batch,env,{fetcher=fetch}={}) {
  for(const message of batch.messages){
    try{
      const r=await processQueuedPR(message.body,env,{fetcher});
      if(r.pendingCI && r.outcome!=="STALE"){
        const previousAttempt=message.body.action==="ci_recheck" ?
          message.body.ciRecheckAttempt : 0;
        if(previousAttempt<CI_RECHECK_MAX){
          ensure(typeof env?.PR_EVENTS?.send==="function",
            "CI_RECHECK_PRODUCER_NOT_CONFIGURED");
          const nextAttempt=previousAttempt+1;
          await env.PR_EVENTS.send({
            ...message.body,action:"ci_recheck",ciRecheckAttempt:nextAttempt
          },{delaySeconds:CI_RECHECK_BASE_DELAY_SECONDS*nextAttempt});
          r.ciRecheckScheduled=nextAttempt;
        }else{
          // Historic neutral Check remains honest and source-pinned.
          // A bounded retry budget is not evidence that CI passed.
          r.ciRecheckExhausted=true;
        }
      }
      // No secrets, PR body or unchecked source content in logs.
      console.log("MATHGRAPH_PR_EVENT "+JSON.stringify(r));
      message.ack();
    }catch(e){
      // Server errors, rate limits and auth outages go through bounded retry/DLQ.
      // Do not log headers, response bodies, private keys or tokens.
      console.error("MATHGRAPH_PR_EVENT_RETRY "+
        (e.status ? "GITHUB_HTTP_"+e.status :
          /^[-A-Z0-9_]+$/.test(e.message)?e.message:"PROCESSING_ERROR"));
      message.retry({delaySeconds:30});
    }
  }
}

export default {
  fetch(request,env){return receiveWebhook(request,env);},
  queue(batch,env){return consumePRQueue(batch,env);}
};
