// GitHub App webhook, dedicated always-running process, no PR code execution.
import http from "node:http";
import {createHmac,sign,timingSafeEqual} from "node:crypto";
import {resolve} from "node:path";
import {fileURLToPath} from "node:url";
import {analyze,checkOutput,githubAPI,loadPR} from "./core.mjs";

export function signatureOK(raw,header,secret) {
  if (!secret || typeof header!=="string" || !/^sha256=[a-f0-9]{64}$/i.test(header))
    return false;
  const actual=Buffer.from(header.slice(7),"hex");
  const expected=createHmac("sha256",secret).update(raw).digest();
  return actual.length===expected.length && timingSafeEqual(actual,expected);
}
export function makeJWT(id,key,now=Math.floor(Date.now()/1000)) {
  if (!/^\d+$/.test(String(id)) || !key) throw new Error("INVALID_APP_AUTH");
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
async function handlePR(payload,config) {
  const repository=payload.repository.full_name,number=payload.pull_request.number;
  const originalHead=payload.pull_request.head.sha;
  const jwt=makeJWT(config.id,config.key);
  const auth=await githubAPI("/app/installations/"+payload.installation.id+
    "/access_tokens",jwt,"POST",{});
  if (!auth?.token) throw new Error("INSTALLATION_TOKEN_UNAVAILABLE");
  const snapshot=await loadPR(repository,number,auth.token);
  if (snapshot.sha!==originalHead) return; // stale delivery
  const report=analyze(snapshot);
  const fresh=await githubAPI("/repos/"+repository+"/pulls/"+number,auth.token);
  if (fresh.head.sha!==originalHead) return; // race guard
  await githubAPI("/repos/"+repository+"/check-runs",auth.token,"POST",{
    ...checkOutput(report),head_sha:originalHead,
    external_id:repository+"#"+number+"@"+originalHead
  });
}
export function start(env=process.env) {
  const key=String(env.GITHUB_APP_PRIVATE_KEY||"").replace(/\\n/g,"\n");
  const secret=env.GITHUB_WEBHOOK_SECRET,id=env.GITHUB_APP_ID;
  const allow=new Set(String(env.MATHGRAPH_ALLOWED_REPOS||"").split(",").map(s=>s.trim()).filter(Boolean));
  if (!key || !secret || !id || !allow.size) throw new Error("MISSING_APP_CONFIG");
  const deliveries=new Set(),config={key,id};
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
      res.writeHead(202);res.end("queued");
      // Requires an always-running worker, not a terminating serverless request.
      void handlePR(payload,config).catch(err=>
        console.error("MATHGRAPH_CHECK_WORKER_FAILURE",err.message));
    } catch {
      if(!res.headersSent) {res.writeHead(400);res.end("invalid payload");}
    }
  });
  server.listen(Number(env.PORT||8787),"0.0.0.0");
  return server;
}
if(process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url))
  start();
