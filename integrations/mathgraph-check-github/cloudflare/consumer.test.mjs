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
  let seq=1000,ciConclusion="success",staleHead=Boolean(opts.stale);
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
        head:{sha:staleHead?"f".repeat(40):SHA,
          repo:{full_name:SCOPE.repository}}});
    if(p==="/repos/"+SCOPE.repository+"/pulls/19/files")
      return json([{filename:".github/workflows/bal-v19.yml",
        patch:"+echo concurrent_fcu=UNKNOWN;remote_conflicting_fcu=UNKNOWN"}]);
    if(p==="/repos/"+SCOPE.repository+"/actions/runs")
      return opts.noCI?json({},403):json({total_count:1,workflow_runs:[{
        id:38202260024,name:"BAL V19 native qualification",
        head_sha:SHA,status:"completed",conclusion:ciConclusion}]});
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
    if(/^\/repos\/metalogiclabs\/go-ethereum\/check-runs\/[0-9]+$/.test(p) &&
       init.method==="PATCH"){
      const fields=JSON.parse(init.body);
      if(opts.failRefresh && fields.output) return json({message:"blocked"},403);
      if(opts.failDetails && !fields.output) return json({message:"blocked"},403);
      const match=saved.find(x=>String(x.id)===p.split("/").at(-1));
      assert.ok(match);
      assert.equal(fields.details_url,
        "https://github.com/"+SCOPE.repository+"/runs/"+match.id);
      if(fields.output){
        assert.deepEqual(Object.keys(fields).sort(),
          ["conclusion","details_url","output","status"]);
        assert.equal(fields.conclusion,"neutral");
        assert.equal(fields.status,"completed");
      }else{
        assert.deepEqual(Object.keys(fields),["details_url"]);
      }
      Object.assign(match,fields);
      return json({...match,app:{
        id:opts.badRefreshPublisher && fields.output ? 15368:SCOPE.appID
      }});
    }
    throw Error("UNKNOWN_FIXTURE_ROUTE");
  };
  return {env,saved,calls,fetcher,
    setCI(state){ciConclusion=state;},setStale(value){staleHead=value;}};

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
  assert.equal(m.saved[0].details_url,
    "https://github.com/"+SCOPE.repository+"/runs/"+m.saved[0].id);
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

test("same-SHA mutable CI evidence updates one App Check, then returns to previous warrant",async()=>{
  const m=setup();
  const before=await processQueuedPR(item,m.env,{fetcher:m.fetcher});
  assert.equal(before.outcome,"CREATED");
  assert.equal(m.saved.length,1);
  assert.equal(m.saved[0].output.title,"DECLARED_VERIFICATION_RESIDUAL");
  const originalID=m.saved[0].id;
  m.setCI("failure");
  const revised=await processQueuedPR({...item,action:"edited"},m.env,{fetcher:m.fetcher});
  assert.equal(revised.outcome,"UPDATED");
  assert.equal(revised.checkID,originalID);
  assert.equal(m.saved.length,1);
  assert.equal(m.saved[0].output.title,"CURRENT_HEAD_CI_UNRESOLVED");
  assert.equal(m.saved[0].head_sha,SHA);
  assert.equal(m.saved[0].conclusion,"neutral");
  m.setCI("success");
  assert.equal((await processQueuedPR(item,m.env,{fetcher:m.fetcher})).outcome,"UPDATED");
  assert.equal(m.saved[0].output.title,"DECLARED_VERIFICATION_RESIDUAL");
  assert.equal((await processQueuedPR(item,m.env,{fetcher:m.fetcher})).outcome,"EXISTING");
  assert.equal(m.calls.filter(c=>c.method==="POST" && c.path.endsWith("/check-runs")).length,1);
  assert.equal(m.calls.filter(c=>c.method==="PATCH").length,3);
  assert.equal(m.calls.filter(c=>c.method==="DELETE").length,4);
});
test("same-SHA check cannot silently reuse stale PR and bad refresh does not acquire authority",async()=>{
  const stale=setup();
  assert.equal((await processQueuedPR(item,stale.env,{fetcher:stale.fetcher})).outcome,"CREATED");
  stale.setStale(true);
  assert.equal((await processQueuedPR(item,stale.env,{fetcher:stale.fetcher})).outcome,"STALE");
  assert.equal(stale.saved.length,1);
  assert.equal(stale.calls.filter(c=>c.method==="PATCH").length,1);
  const denied=setup({failRefresh:true});
  assert.equal((await processQueuedPR(item,denied.env,{fetcher:denied.fetcher})).outcome,"CREATED");
  denied.setCI("failure");
  await assert.rejects(processQueuedPR(item,denied.env,{fetcher:denied.fetcher}),
    /GITHUB_HTTP_403/);
  assert.equal(denied.saved.length,1);
  assert.equal(denied.saved[0].output.title,"DECLARED_VERIFICATION_RESIDUAL");
  assert.equal(denied.calls.filter(c=>c.method==="DELETE").length,2);
  const inconsistent=setup({badRefreshPublisher:true});
  assert.equal((await processQueuedPR(item,inconsistent.env,{fetcher:inconsistent.fetcher})).outcome,"CREATED");
  inconsistent.setCI("failure");
  await assert.rejects(processQueuedPR(item,inconsistent.env,{fetcher:inconsistent.fetcher}),
    /CHECK_DETAILS_OR_REFRESH_IDENTITY_NOT_CONFIRMED/);
});
test("duplicate App-identity Checks at the same source SHA cannot be silently merged",async()=>{
  const m=setup();
  assert.equal((await processQueuedPR(item,m.env,{fetcher:m.fetcher})).outcome,"CREATED");
  m.saved.push({...m.saved[0],id:333});
  await assert.rejects(processQueuedPR(item,m.env,{fetcher:m.fetcher}),
    /DUPLICATE_APP_CHECK_AUTHORITY/);
  assert.equal(m.calls.filter(c=>c.method==="PATCH").length,1);
});

test("old check whose details link fell back to MathGraph homepage is repaired in place",async()=>{
  const m=setup();
  assert.equal((await processQueuedPR(item,m.env,{fetcher:m.fetcher})).outcome,"CREATED");
  const originalID=m.saved[0].id;
  const originalSummary=m.saved[0].output.summary;
  m.saved[0].details_url="https://mathgraph.org/";
  const again=await processQueuedPR({...item,action:"edited"},m.env,{fetcher:m.fetcher});
  assert.equal(again.outcome,"LINK_REPAIRED");
  assert.equal(again.checkID,originalID);
  assert.equal(m.saved.length,1);
  assert.equal(m.saved[0].details_url,
    "https://github.com/"+SCOPE.repository+"/runs/"+originalID);
  assert.equal(m.saved[0].output.summary,originalSummary);
  assert.equal(m.saved[0].conclusion,"neutral");
  assert.equal((await processQueuedPR(item,m.env,{fetcher:m.fetcher})).outcome,"EXISTING");
});
test("a failed native details patch never claims Check publication",async()=>{
  const m=setup({failDetails:true});
  await assert.rejects(processQueuedPR(item,m.env,{fetcher:m.fetcher}),
    /GITHUB_HTTP_403/);
  assert.equal(m.saved.length,1);
  assert.equal(m.calls.filter(x=>x.method==="DELETE").length,1);
});
