// GitHub App webhook, dedicated always-running process, no PR code execution.
import http from "node:http";
import {createHmac,sign,timingSafeEqual} from "node:crypto";
import {resolve} from "node:path";
import {fileURLToPath} from "node:url";
import {analyze,checkOutput,githubAPI,loadPR} from "./core.mjs";
import {handlePKCYamlSignedEvent} from "./pkc-yaml-webhook-bridge.mjs";

export function signatureOK(raw,header,secret) {
  if (!secret || typeof header!=="string" || !/^sha256=[a-f0-9]{64}$/i.test(header))
    return false;
  const actual=Buffer.from(header.slice(7),"hex");
  const expected=createHmac("sha256",secret).update(raw).digest();
  return actual.length===expected.length && timingSafeEqual(actual,expected);
}
export function makeJWT(id,key,now=Math.floor(Date.now()/1000)) {
  // GitHub recommends the Client ID as JWT issuer. Numeric App IDs remain valid.
  if (!/^(?:[1-9]\d*|[A-Za-z][A-Za-z0-9_-]{7,127})$/.test(String(id)) || !key)
    throw new Error("INVALID_APP_AUTH");
  const header=Buffer.from(JSON.stringify({alg:"RS256",typ:"JWT"})).toString("base64url");
  const payload=Buffer.from(JSON.stringify({iat:now-60,exp:now+540,iss:String(id)})).toString("base64url");
  const message=header+"."+payload;
  return message+"."+sign("RSA-SHA256",Buffer.from(message),key).toString("base64url");
}
export function accepted(event,action,repository,allow) {
  return event==="pull_request" &&
    ["opened","reopened","edited","synchronize","ready_for_review"].includes(action) &&
    allow.has(repository);
}
async function appAPI(path,token,method="GET",body) {
  if(method!=="GET_BYTES")return githubAPI(path,token,method,body);
  if(path!=="/repos/metalogiclabs/mathgraph/actions/artifacts/12171240289/zip")
    throw Error("ZIP_PATH_NOT_ALLOWLISTED");
  const response=await fetch("https://api.github.com"+path,{method:"GET",
    headers:{Authorization:"Bearer "+token,Accept:"application/vnd.github+json",
      "X-GitHub-Api-Version":"2022-11-28","User-Agent":"MathGraph-Check-v0"},
    signal:AbortSignal.timeout(15000)});
  if(!response.ok)throw Error("ZIP_DOWNLOAD_HTTP_"+response.status);
  const bytes=new Uint8Array(await response.arrayBuffer());
  if(bytes.length>2_000_000)throw Error("ZIP_TOO_LARGE");
  return bytes;
}
async function handlePR(payload,config) {
  const repository=payload.repository.full_name,number=payload.pull_request.number;
  const originalHead=payload.pull_request.head.sha;
  const jwt=makeJWT(config.id,config.key);
  const auth=await githubAPI("/app/installations/"+payload.installation.id+
    "/access_tokens",jwt,"POST",{});
  if (!auth?.token) throw new Error("INSTALLATION_TOKEN_UNAVAILABLE");
  if(config.pkcYamlEnabled && repository==="metalogiclabs/mathgraph" && number===178) {
    // Signed and allowlisted before handlePR. Opt-in source-specific App route.
    // No fallback to a generic Check after a denied PKC/YAML publication.
    return handlePKCYamlSignedEvent({event:"pull_request",action:payload.action,
      payload,signatureVerified:true,enabled:true,
      allowRepos:[...config.allow],githubAPI:appAPI,token:auth.token,
      appId:config.appID,installed:true});
  }
  const snapshot=await loadPR(repository,number,auth.token);
  if (snapshot.sha!==originalHead) return; // stale delivery
  const report=analyze(snapshot);
  const fresh=await githubAPI("/repos/"+repository+"/pulls/"+number,auth.token);
  if (fresh.head.sha!==originalHead) return; // race guard
  const check=checkOutput(report);
  const externalId=repository+"#"+number+"@"+originalHead;
  // Reconcile with GitHub's durable Check Run state before a fresh write.
  // This avoids duplicates after worker restarts; it is not an exactly-once queue.
  const checks=await githubAPI("/repos/"+repository+"/commits/"+originalHead+
    "/check-runs?check_name="+encodeURIComponent(check.name)+"&filter=all&per_page=100",auth.token);
  if (!Array.isArray(checks?.check_runs) ||
      !Number.isSafeInteger(checks.total_count) ||
      checks.total_count>checks.check_runs.length) throw new Error("CHECK_RECONCILIATION_INCOMPLETE");
  const existing=checks.check_runs.find(item=>
    item.name===check.name && item.external_id===externalId &&
    item.app?.id===config.appID);
  if (existing) return; // a retry / restarted worker already published it
  await githubAPI("/repos/"+repository+"/check-runs",auth.token,"POST",{
    ...check,head_sha:originalHead,external_id:externalId
  });
}
export function start(env=process.env) {
  const key=String(env.GITHUB_APP_PRIVATE_KEY||"").replace(/\\n/g,"\n");
  const secret=env.GITHUB_WEBHOOK_SECRET;
  const id=env.GITHUB_APP_CLIENT_ID || env.GITHUB_APP_ID;
  const appID=Number(env.GITHUB_APP_ID);
  const allow=new Set(String(env.MATHGRAPH_ALLOWED_REPOS||"").split(",").map(s=>s.trim()).filter(Boolean));
  if (!key || !secret || !id || !allow.size ||
      !Number.isSafeInteger(appID) || appID<1) throw new Error("MISSING_APP_CONFIG");
  const deliveries=new Set(),inFlight=new Set(),config={key,id,appID,
    allow,pkcYamlEnabled:env.MATHGRAPH_PKC_YAML_LIVE==="true"};
  const server=http.createServer(async(req,res)=>{
    if (req.method==="GET" && req.url==="/health") {
      res.writeHead(200);res.end("ok");return;
    }
    if (req.method!=="POST" || req.url!=="/github/webhook") {
      res.writeHead(404);res.end();return;
    }
    let size=0;const chunks=[];
    try {
      for await(const chunk of req) {
        size+=chunk.length;
        if(size>1_000_000) {res.writeHead(413);res.end("oversized");return;}
        chunks.push(chunk);
      }
      const raw=Buffer.concat(chunks);
      if(!signatureOK(raw,req.headers["x-hub-signature-256"],secret)) {
        res.writeHead(401);res.end("bad signature");return;
      }
      const payload=JSON.parse(raw.toString("utf8"));
      const delivery=String(req.headers["x-github-delivery"]||"");
      if(!delivery || deliveries.has(delivery) ||
          !accepted(req.headers["x-github-event"],payload.action,
            payload.repository?.full_name,allow) ||
          !Number.isSafeInteger(payload.installation?.id) ||
          !Number.isSafeInteger(payload.pull_request?.number) ||
          !/^[a-f0-9]{40}$/i.test(payload.pull_request?.head?.sha||"")) {
        res.writeHead(202);res.end("ignored");return;
      }
      deliveries.add(delivery);
      if(deliveries.size>1000) deliveries.clear();
      // Serialize same-SHA work within this single process, even for new deliveries.
      const identity=payload.repository.full_name+"#"+payload.pull_request.number+
        "@"+payload.pull_request.head.sha;
      if(inFlight.has(identity)){
        res.writeHead(202);res.end("already-processing");return;
      }
      inFlight.add(identity);
      res.writeHead(202);res.end("queued");
      // Requires an always-running worker; acknowledged events have no durable queue.
      void handlePR(payload,config).catch(err=>
        console.error("MATHGRAPH_CHECK_WORKER_FAILURE",err.message))
        .finally(()=>inFlight.delete(identity));
    } catch {
      if(!res.headersSent) {res.writeHead(400);res.end("invalid payload");}
    }
  });
  server.listen(Number(env.PORT||8787),"0.0.0.0");
  return server;
}
if(process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url))
  start();
