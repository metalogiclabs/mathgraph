import test from "node:test";
import assert from "node:assert/strict";
import {generateKeyPairSync} from "node:crypto";
import {activateWebhook} from "./activate-webhook.mjs";
const TARGET_URL="https://mathgraph-check-webhook-pilot.cf-test.workers.dev/github/webhook";
function fixture({existing="",notReady=false,wrongApp=false,noEvent=false}={}){
  const keys=generateKeyPairSync("rsa",{modulusLength:2048});
  let prior=existing,patches=0;
  const calls=[];
  const json=x=>new Response(JSON.stringify(x),{status:200});
  const fetcher=async(raw,opts={})=>{
    const u=new URL(raw);calls.push(u.host+u.pathname+":"+(opts.method||"GET"));
    if(u.host==="api.cloudflare.com" &&
       u.pathname.endsWith("/workers/subdomain"))
      return json({success:true,result:{subdomain:"cf-test"}});
    if(u.host==="mathgraph-check-webhook-pilot.cf-test.workers.dev")
      return new Response(notReady?"not ready":"ready",{status:notReady?503:200});
    assert.equal(u.host,"api.github.com");
    assert.match(opts.headers.Authorization,/^Bearer /);
    if(u.pathname==="/app")return json({
      id:wrongApp?15368:5308912,owner:{login:"metalogiclabs"},
      events:noEvent?[]:["pull_request"]
    });
    if(u.pathname==="/app/hook/config"){
      if(opts.method==="PATCH"){
        const payload=JSON.parse(opts.body);
        assert.equal(payload.secret,"fixture-shared-signature-key-123456");
        assert.equal(payload.insecure_ssl,"0");
        patches++;
        prior=payload.url;
        return json({url:prior,content_type:"json",insecure_ssl:"0"});
      }
      return json({url:prior,content_type:"json",insecure_ssl:"0"});
    }
    throw Error("UNEXPECTED_TEST_API_ROUTE");
  };
  const args={
    accountId:"a".repeat(32),apiToken:"fixture-cloudflare-token",
    privateKey:keys.privateKey.export({type:"pkcs1",format:"pem"}).toString(),
    hookSecret:"fixture-shared-signature-key-123456",
    fetcher
  };
  return {args,calls,get patches(){return patches;}};
}
test("configures exact GitHub App webhook only after Cloudflare /ready",async()=>{
  const f=fixture();
  const x=await activateWebhook(f.args);
  assert.equal(x.configured,true);
  assert.equal(x.target,TARGET_URL);
  assert.equal(x.app_id,5308912);
  assert.equal(x.secret_verified_by_live_delivery,false);
  assert.equal(f.patches,1);
});
test("different existing webhook requires explicit replacement approval",async()=>{
  const f=fixture({existing:"https://existing.example/hook"});
  await assert.rejects(activateWebhook(f.args),
    /EXISTING_WEBHOOK_URL_REPLACEMENT_NOT_APPROVED/);
  assert.equal(f.patches,0);
  const x=await activateWebhook({...f.args,approveReplace:true});
  assert.equal(x.previous_url_replaced,true);
  assert.equal(f.patches,1);
});
test("incomplete Cloudflare or wrong App refuses webhook update",async()=>{
  for(const opts of [{notReady:true},{wrongApp:true},{noEvent:true}]){
    const f=fixture(opts);
    await assert.rejects(activateWebhook(f.args),
      /CLOUDFLARE_WORKER_NOT_READY|WRONG_REGISTERED_APP_FOR_WEBHOOK|APP_PULL_REQUEST_EVENT_NOT_SUBSCRIBED/);
    assert.equal(f.patches,0);
  }
});
