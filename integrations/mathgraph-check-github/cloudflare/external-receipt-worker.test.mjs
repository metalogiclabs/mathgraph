import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname,join } from "node:path";
import { fileURLToPath } from "node:url";
import { generateKeyPairSync } from "node:crypto";
import { processQueuedPR, SCOPE } from "./worker.mjs";
import { EVIDENCE } from "../external-native-receipt.mjs";

const fixtureDir=join(dirname(fileURLToPath(import.meta.url)),"../fixtures");
const manifest=readFileSync(join(fixtureDir,"external-native-evidence.v1.json"),"utf8");
const report=readFileSync(join(fixtureDir,"one-finding-report.v1.json"),"utf8");
const SHA="1c6e656e55b82819f36b0e9a6ea38809ce61b40b";
const item={schema:"mathgraph.github-pr-delivery.v0",
  repository:SCOPE.repository,number:21,installationID:42,sha:SHA,
  delivery:"123e4567-e89b-12d3-a456-426614174001",action:"opened"};
const perms={checks:"write",pull_requests:"read",actions:"read"};
const sendJson=(v,status=200)=>new Response(JSON.stringify(v),{status});
function mockAPI() {
 const priv=generateKeyPairSync("rsa",{modulusLength:2048}).privateKey
   .export({type:"pkcs1",format:"pem"}).toString();
 const env={GITHUB_APP_ID:String(SCOPE.appID),GITHUB_APP_CLIENT_ID:SCOPE.clientID,
   GITHUB_APP_PRIVATE_KEY:priv};
 const calls=[], checks=[];
 const fileObj=(contents,sha)=>({sha,encoding:"base64",content:Buffer.from(contents).toString("base64")});
 const fetcher=async (raw,options={})=>{
  const url=new URL(raw),path=url.pathname;
  assert.equal(url.origin,"https://api.github.com");
  calls.push({path,method:options.method||"GET",external:path.startsWith("/repos/heathsanchez/test")});
  const token=options.headers?.Authorization;
  if(path.startsWith("/repos/heathsanchez/test/")) {
    assert.equal(token,undefined,"scoped App token must not cross repositories");
    if(path.endsWith("/ONE_FINDING_REPORT.json")) {
      assert.equal(url.searchParams.get("ref"),EVIDENCE.reportCommit);
      return sendJson(fileObj(report,EVIDENCE.reportBlob));
    }
    const match=path.match(/\/actions\/runs\/(\d+)/);
    assert.ok(match,"unexpected public evidence path");
    const r=EVIDENCE.runs.find(x=>String(x.id)===match[1]);
    assert.ok(r);
    if(path.endsWith("/artifacts"))
      return sendJson({total_count:1,artifacts:[{
        id:r.artifact,name:r.name,expired:false,digest:r.digest,
        workflow_run:{id:r.id,head_sha:r.head}
      }]});
    return sendJson({id:r.id,head_sha:r.head,status:"completed",
      conclusion:"success",repository:{full_name:EVIDENCE.reporter},
      event:"push",run_attempt:1,path:r.path});
  }
  assert.match(token||"",/^Bearer /);
  if(path==="/app")return sendJson({id:SCOPE.appID,owner:{login:SCOPE.owner},
    permissions:perms});
  if(path==="/repos/"+SCOPE.repository+"/installation")
    return sendJson({id:42,app_id:SCOPE.appID,
      account:{login:SCOPE.owner},suspended_at:null,permissions:perms});
  if(path==="/app/installations/42/access_tokens")
    return sendJson({token:"example-exact-repo-installation-token",
      permissions:perms});
  if(path==="/installation/token")return new Response(null,{status:204});
  if(path==="/repos/"+SCOPE.repository+"/pulls/21")
    return sendJson({state:"open",head:{sha:SHA,repo:{full_name:SCOPE.repository}},
      base:{repo:{full_name:SCOPE.repository}}});
  if(path==="/repos/"+SCOPE.repository+"/pulls/21/files") {
    return sendJson(EVIDENCE.carrierFiles.map(filename=>({filename,status:"added"})));
  }
  if(path==="/repos/"+SCOPE.repository+"/actions/runs") {
    return sendJson({total_count:0,workflow_runs:[]});
  }
  if(path==="/repos/"+SCOPE.repository+"/contents/"+EVIDENCE.manifest){
    assert.equal(url.searchParams.get("ref"),SHA);
    return sendJson(fileObj(manifest,EVIDENCE.manifestBlob));
  }
  if(path==="/repos/"+SCOPE.repository+"/commits/"+SHA+"/check-runs") {
    assert.equal(url.searchParams.get("filter"),"all");
    return sendJson({total_count:checks.length,check_runs:checks});
  }
  if(path==="/repos/"+SCOPE.repository+"/check-runs"){
    if(options.method==="POST"){
      const value={...JSON.parse(options.body),id:1401,app:{id:SCOPE.appID}};
      checks.push(value);
      return sendJson(value);
    }
    throw Error("UNEXPECTED_CHECK_ROUTE");
  }
  if(path==="/repos/"+SCOPE.repository+"/check-runs/1401"){
    assert.equal(options.method,"PATCH");
    const patch=JSON.parse(options.body),prev=checks[0];
    Object.assign(prev,patch);
    return sendJson(prev);
  }
  throw Error("UNEXPECTED_APP_ROUTE_"+path);
 };
 return {env,checks,calls,fetcher};
}
test("signed first-party event consumes pinned external source and publishes one neutral App Check",async()=>{
 const t=mockAPI();
 const result=await processQueuedPR(item,t.env,{fetcher:t.fetcher});
 assert.equal(result.outcome,"CREATED");
 assert.equal(result.appID,5308912);
 assert.equal(result.checkID,1401);
 assert.equal(result.tokenRevoked,true);
 assert.equal(t.checks.length,1);
 const c=t.checks[0];
 assert.equal(c.head_sha,SHA);
 assert.equal(c.conclusion,"neutral");
 assert.equal(c.output.title,"EXTERNAL_NATIVE_ONE_FINDING_BOUNDED");
 assert.match(c.output.summary,/NOT this Ethereum/);
 assert.match(c.output.summary,/69 of 130/);
 assert.match(c.output.summary,/issue #872/);
 assert.match(c.output.summary,/did NOT rerun Go tests/);
 assert.equal(c.details_url,"https://github.com/"+SCOPE.repository+"/runs/1401");
 assert.ok(t.calls.filter(x=>x.external).length>=6);
 const again=await processQueuedPR({...item,action:"edited"},t.env,{fetcher:t.fetcher});
 assert.equal(again.outcome,"EXISTING");
 assert.equal(t.checks.length,1);
});
