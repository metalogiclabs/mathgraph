import test from "node:test";
import assert from "node:assert/strict";
import {createHmac,generateKeyPairSync} from "node:crypto";
import {once} from "node:events";
import {start} from "./webhook.mjs";
const repo="metalogiclabs/mathgraph",head="a".repeat(40),secret="pkc-yaml-signed-test";
const keys=generateKeyPairSync("rsa",{modulusLength:2048});
test("signed HTTP delivery with enabled PKC route refuses invalid archive before Check write",async()=>{
 const original=globalThis.fetch;let writes=0;let metadataReads=0;
 globalThis.fetch=async(url,opts={})=>{
  const u=new URL(url);
  assert.equal(u.origin,"https://api.github.com");
  if(u.pathname==="/app/installations/42/access_tokens")
    return new Response(JSON.stringify({token:"scoped-test-token"}),{status:200});
  if(u.pathname.includes("/actions/artifacts/12171240289")){
    metadataReads++;return new Response(JSON.stringify({id:12171240289,expired:true}),{status:200});
  }
  if(u.pathname.endsWith("/check-runs") && opts.method==="POST")writes++;
  throw Error("UNEXPECTED_GITHUB_PATH:"+u.pathname);
 };
 let server;
 try{
  server=start({PORT:"0",GITHUB_APP_ID:"5308912",
   GITHUB_APP_PRIVATE_KEY:keys.privateKey.export({type:"pkcs8",format:"pem"}),
   GITHUB_WEBHOOK_SECRET:secret,MATHGRAPH_ALLOWED_REPOS:repo,
   MATHGRAPH_PKC_YAML_LIVE:"true"});
  if(!server.listening)await once(server,"listening");
  const payload={action:"edited",repository:{full_name:repo},
   installation:{id:42},pull_request:{number:171,head:{sha:head}}};
  const raw=JSON.stringify(payload);
  const signature="sha256="+createHmac("sha256",secret).update(raw).digest("hex");
  const response=await original("http://127.0.0.1:"+server.address().port+"/github/webhook",{
   method:"POST",headers:{"content-type":"application/json",
    "x-github-event":"pull_request","x-github-delivery":"pkc-yaml-test-1",
    "x-hub-signature-256":signature},body:raw});
  assert.equal(response.status,202);
  for(let i=0;i<100&&metadataReads===0;i++)await new Promise(r=>setTimeout(r,10));
  assert.equal(metadataReads,1);
  assert.equal(writes,0);
 }finally{globalThis.fetch=original;if(server)await new Promise(resolve=>server.close(resolve))}
});
