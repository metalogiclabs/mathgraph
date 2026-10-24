import test from "node:test";
import assert from "node:assert/strict";
import { createHmac, generateKeyPairSync } from "node:crypto";
import { receiveWebhook, processCarrierPR, consumePRQueue, SCOPE } from "./worker.mjs";

const REPO="metalogiclabs/mathgraph";
const HEAD="05a6057e94d899ded94374db4a831963034aea93";
const DELIVERY="123e4567-e89b-12d3-a456-426614174000";
const SECRET="carrier-test-webhook-secret";
const carrier=()=>({action:"opened",repository:{full_name:REPO},installation:{id:42},
  pull_request:{number:178,head:{sha:HEAD,repo:{full_name:REPO}},
    base:{repo:{full_name:REPO}}}});
function signed(payload=carrier(),signatureSecret=SECRET){
  const body=JSON.stringify(payload);
  return new Request("https://pilot.test/github/webhook",{method:"POST",headers:{
    "x-github-event":"pull_request","x-github-delivery":DELIVERY,
    "x-hub-signature-256":"sha256="+createHmac("sha256",signatureSecret).update(body).digest("hex")
  },body});
}
function fixture(enabled="true"){
  const queued=[];
  return {queued,env:{PKC_YAML_CARRIER_ENABLED:enabled,GITHUB_WEBHOOK_SECRET:SECRET,
    PR_EVENTS:{async send(message){queued.push(message);}}}};
}

test("actual Worker queues exactly the signed frozen carrier when explicitly enabled",async()=>{
  const {queued,env}=fixture();
  assert.equal((await receiveWebhook(signed(),env)).status,202);
  assert.deepEqual(queued,[{schema:"mathgraph.pkcyaml-pr-delivery.v1",repository:REPO,
    number:178,sha:HEAD,installationID:42,delivery:DELIVERY,action:"opened"}]);
});
test("default-off carrier flag leaves Geth scope and all carrier activity unchanged",async()=>{
  const {queued,env}=fixture(undefined);
  delete env.PKC_YAML_CARRIER_ENABLED;
  assert.equal((await receiveWebhook(signed(),env)).status,202);
  assert.equal(queued.length,0);
  assert.equal(SCOPE.repository,"metalogiclabs/go-ethereum");
});
test("actual Worker denies bad signature, wrong PR, foreign repository and stale head",async()=>{
  const {queued,env}=fixture();
  assert.equal((await receiveWebhook(signed(carrier(),"wrong-secret"),env)).status,401);
  const edits=[
    p=>p.pull_request.number=177,
    p=>p.repository.full_name="outsider/mathgraph",
    p=>p.pull_request.head.sha="a".repeat(40),
    p=>p.pull_request.head.repo.full_name="outsider/mathgraph",
    p=>p.pull_request.base.repo.full_name="outsider/mathgraph",
    p=>p.installation.id=0
  ];
  for(const edit of edits){const p=carrier();edit(p);
    assert.equal((await receiveWebhook(signed(p),env)).status,202);}
  assert.equal(queued.length,0);
});

const ITEM={schema:"mathgraph.pkcyaml-pr-delivery.v1",repository:REPO,number:178,
  sha:HEAD,installationID:42,delivery:DELIVERY,action:"opened"};
const PERMS={checks:"write",pull_requests:"read",actions:"read"};
function processFixture(options={}){
  const key=generateKeyPairSync("rsa",{modulusLength:2048}).privateKey;
  const calls=[];
  const env={GITHUB_APP_ID:String(SCOPE.appID),GITHUB_APP_CLIENT_ID:SCOPE.clientID,
    GITHUB_APP_PRIVATE_KEY:key.export({type:"pkcs1",format:"pem"}).toString(),
    PKC_YAML_CARRIER_ENABLED:options.enabled===false?"false":"true"};
  const json=(value,status=200)=>new Response(JSON.stringify(value),{status});
  const fetcher=async(url,init={})=>{
    const parsed=new URL(url),p=parsed.pathname;
    calls.push({path:p,method:init.method||"GET",body:init.body});
    assert.equal(parsed.origin,"https://api.github.com");
    assert.match(init.headers.Authorization,/^Bearer /);
    if(p==="/app")return json({id:SCOPE.appID,owner:{login:SCOPE.owner},permissions:PERMS});
    if(p==="/repos/"+REPO+"/installation")return json({
      id:options.foreignInstallation?43:42,app_id:SCOPE.appID,
      account:{login:SCOPE.owner},suspended_at:null,
      permissions:options.badPermission?{checks:"read",pull_requests:"read",actions:"read"}:PERMS
    });
    if(p==="/app/installations/42/access_tokens"){
      assert.deepEqual(JSON.parse(init.body),{repositories:["mathgraph"],permissions:PERMS});
      if(options.tokenDenied)return json({message:"denied"},403);
      return json({token:"scoped-carrier-token",permissions:PERMS});
    }
    if(p==="/installation/token")return new Response(null,{status:204});
    if(p==="/repos/"+REPO+"/pulls/178")return json({state:"open",
      head:{sha:options.stale?"a".repeat(40):HEAD,repo:{full_name:REPO}},
      base:{repo:{full_name:REPO}}});
    if(p==="/repos/"+REPO+"/pulls/178/files")return json([{
      filename:".mathgraph-check/pkc-yaml/EXTERNAL-RESEARCH-RECEIPT.md"}]);
    if(p==="/repos/"+REPO+"/actions/artifacts/12171240289")return json({
      id:12171240289,expired:false,digest:options.tamperedDigest?
        "sha256:"+"a".repeat(64):
        "sha256:2bbd575f1d93759a734fa459f4f48be599411a44b91d0627b397d02d4f8b98f9",
      workflow_run:{id:39218904172}});
    throw Error("UNEXPECTED_GITHUB_PATH:"+p);
  };
  return {env,calls,fetcher};
}
test("queue consumer is default off, and rejects foreign installation before token mint",async()=>{
  const disabled=processFixture({enabled:false});
  assert.equal((await processCarrierPR(ITEM,disabled.env,{fetcher:disabled.fetcher})).outcome,
    "CARRIER_DISABLED");
  assert.equal(disabled.calls.length,0);
  const bad=processFixture({foreignInstallation:true});
  await assert.rejects(processCarrierPR(ITEM,bad.env,{fetcher:bad.fetcher}),
    /CARRIER_INSTALLATION_INVALID/);
  assert.equal(bad.calls.some(x=>x.path.endsWith("/access_tokens")),false);
});
test("narrow installation token and invalid native digest fail closed without Check POST",async()=>{
  const m=processFixture({tamperedDigest:true});
  await assert.rejects(processCarrierPR(ITEM,m.env,{fetcher:m.fetcher}),
    /ARTIFACT_AUTHORITY_MISMATCH/);
  assert.equal(m.calls.filter(x=>x.path==="/repos/"+REPO+"/check-runs").length,0);
  assert.equal(m.calls.filter(x=>x.method==="DELETE").length,1);
});
test("missing checks:write and API token denial never obtain publisher authority",async()=>{
  for(const options of [{badPermission:true},{tokenDenied:true}]){
    const m=processFixture(options);
    await assert.rejects(processCarrierPR(ITEM,m.env,{fetcher:m.fetcher}),
      /CARRIER_INSTALLATION_INVALID|GITHUB_HTTP_403/);
    assert.equal(m.calls.some(x=>x.path==="/repos/"+REPO+"/check-runs"),false);
  }
});
test("actual queue dispatch retries a denied carrier without entering Geth path",async()=>{
  const m=processFixture({foreignInstallation:true});
  let ack=0,retry=0;
  await consumePRQueue({messages:[{body:ITEM,ack(){ack++},retry(){retry++}}]},
    m.env,{fetcher:m.fetcher});
  assert.equal(ack,0);assert.equal(retry,1);
  assert.equal(m.calls.some(x=>x.path.includes("go-ethereum")),false);
});
