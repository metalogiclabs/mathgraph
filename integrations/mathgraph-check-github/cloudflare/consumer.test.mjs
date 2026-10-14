import test from "node:test";
import assert from "node:assert/strict";
import {generateKeyPairSync} from "node:crypto";
import {processQueuedPR,consumePRQueue,SCOPE} from "./worker.mjs";
const SHA="a04aa77aaebd81d11274560e8d24d90c6f417589";
const item={schema:"mathgraph.github-pr-delivery.v0",
  repository:SCOPE.repository,number:19,installationID:42,sha:SHA,
  delivery:"123e4567-e89b-12d3-a456-426614174000",action:"opened"};
const grant={checks:"write",pull_requests:"read",actions:"read"};
function setup(opts={}){
  const keys=generateKeyPairSync("rsa",{modulusLength:2048});
  const env={
    GITHUB_APP_PRIVATE_KEY:keys.privateKey.export({type:"pkcs1",format:"pem"}).toString(),
    GITHUB_APP_CLIENT_ID:SCOPE.clientID,GITHUB_APP_ID:String(SCOPE.appID)
  };
  const saved=[],calls=[];
  const json=(x,status=200)=>new Response(JSON.stringify(x),{status});
  let seq=1000;
  const fetcher=async(raw,init={})=>{
    const u=new URL(raw);assert.equal(u.origin,"https://api.github.com");
    calls.push({path:u.pathname,method:init.method||"GET"});
    const p=u.pathname;
    assert.match(init.headers.Authorization,/^Bearer /);
    if(p==="/app")return json({id:opts.badApp?15368:SCOPE.appID,
      owner:{login:SCOPE.owner},permissions:grant});
    if(p==="/repos/"+SCOPE.repository+"/installation")
      return json({id:opts.badInstallation?43:42,app_id:SCOPE.appID,
        account:{login:SCOPE.owner},suspended_at:null,permissions:grant});
    if(p==="/app/installations/42/access_tokens"){
      assert.deepEqual(JSON.parse(init.body),{
        repositories:["go-ethereum"],permissions:grant});
      return json({token:"mock-installation-token",permissions:grant});
    }
    if(p==="/installation/token")
      return opts.revokeFails?json({},403):new Response(null,{status:204});
    if(p==="/repos/"+SCOPE.repository+"/pulls/19")
      return json({state:"open",base:{repo:{full_name:SCOPE.repository}},
        head:{sha:opts.stale?"f".repeat(40):SHA,
          repo:{full_name:SCOPE.repository}}});
    if(p==="/repos/"+SCOPE.repository+"/pulls/19/files")
      return json([{filename:".github/workflows/bal-v19.yml",
        patch:"+echo concurrent_fcu=UNKNOWN;remote_conflicting_fcu=UNKNOWN"}]);
    if(p==="/repos/"+SCOPE.repository+"/actions/runs")
      return opts.noCI?json({},403):json({total_count:1,workflow_runs:[{
        id:38202260024,name:"BAL V19 native qualification",
        head_sha:SHA,status:"completed",conclusion:"success"}]});
    if(p==="/repos/"+SCOPE.repository+"/commits/"+SHA+"/check-runs"){
      assert.equal(u.searchParams.get("filter"),"all");
      assert.equal(u.searchParams.get("check_name"),SCOPE.checkName);
      return json({total_count:saved.length,check_runs:saved});
    }
    if(p==="/repos/"+SCOPE.repository+"/check-runs"){
      const result={...JSON.parse(init.body),id:++seq,
        app:{id:opts.badPublisher?15368:SCOPE.appID}};
      saved.push(result);return json(result);
    }
    throw Error("UNKNOWN_FIXTURE_ROUTE");
  };
  return {env,saved,calls,fetcher};
}
test("queue publishes one neutral App-owned exact-head check",async()=>{
  const m=setup();
  const r=await processQueuedPR(item,m.env,{fetcher:m.fetcher});
  assert.equal(r.outcome,"CREATED");
  assert.equal(r.tokenRevoked,true);
  assert.equal(m.saved.length,1);
  assert.equal(m.saved[0].app.id,SCOPE.appID);
  assert.equal(m.saved[0].conclusion,"neutral");
  assert.equal(m.saved[0].head_sha,SHA);
  assert.match(m.saved[0].output.summary,/concurrent_fcu=UNKNOWN/);
  assert.equal(m.calls.filter(x=>x.method==="DELETE").length,1);
});
test("redelivery reuses same App Check rather than creating duplicate",async()=>{
  const m=setup();
  assert.equal((await processQueuedPR(item,m.env,{fetcher:m.fetcher})).outcome,"CREATED");
  assert.equal((await processQueuedPR(item,m.env,{fetcher:m.fetcher})).outcome,"EXISTING");
  assert.equal(m.saved.length,1);
});
test("source revision changed or App identity mismatch fails closed",async()=>{
  const stale=setup({stale:true});
  assert.equal((await processQueuedPR(item,stale.env,{fetcher:stale.fetcher})).outcome,"STALE");
  assert.equal(stale.saved.length,0);
  for(const opt of [{badApp:true},{badInstallation:true}]){
    const m=setup(opt);
    await assert.rejects(processQueuedPR(item,m.env,{fetcher:m.fetcher}),
      /REGISTERED_APP_IDENTITY_INVALID|SIGNED_EVENT_INSTALLATION_INVALID/);
    assert.equal(m.saved.length,0);
  }
});
test("absent CI remains advisory and missing revocation remains unresolved",async()=>{
  const m=setup({noCI:true});
  const r=await processQueuedPR(item,m.env,{fetcher:m.fetcher});
  assert.equal(r.finding,"DECLARED_VERIFICATION_RESIDUAL");
  assert.equal(m.saved[0].conclusion,"neutral");
  const r2=setup({revokeFails:true});
  await assert.rejects(processQueuedPR(item,r2.env,{fetcher:r2.fetcher}),
    /TOKEN_REVOCATION_NOT_VERIFIED/);
});
test("queue ACKs valid work, retries a failed App identity and drops invalid event",async()=>{
  const m=setup();let ack=0,retry=0;
  const msg={body:item,ack(){ack++;},retry(){retry++;}};
  await consumePRQueue({messages:[msg]},m.env,{fetcher:m.fetcher});
  assert.equal(ack,1);assert.equal(retry,0);
  const bad=setup({badApp:true});
  await consumePRQueue({messages:[msg]},bad.env,{fetcher:bad.fetcher});
  assert.equal(retry,1);
  const ignored=setup();
  await consumePRQueue({messages:[{body:{untrusted:true},
    ack(){ack++;},retry(){retry++;}}]},ignored.env,{fetcher:ignored.fetcher});
  assert.equal(ack,2);
  assert.equal(ignored.calls.length,0);
});
