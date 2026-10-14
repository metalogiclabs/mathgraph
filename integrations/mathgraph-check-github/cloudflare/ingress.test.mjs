import test from "node:test";
import assert from "node:assert/strict";
import {createHmac,generateKeyPairSync,verify} from "node:crypto";
import {receiveWebhook,parseSignedEvent,appJWT,SCOPE} from "./worker.mjs";
const SHA="a04aa77aaebd81d11274560e8d24d90c6f417589";
const SECRET="fixture-webhook-secret";
const ID="123e4567-e89b-12d3-a456-426614174000";
const event=()=>({
  action:"opened",repository:{full_name:SCOPE.repository},
  installation:{id:42},pull_request:{number:19,
    head:{sha:SHA,repo:{full_name:SCOPE.repository}},
    base:{repo:{full_name:SCOPE.repository}}}
});
function signed(obj=event(),secret=SECRET){
  const body=JSON.stringify(obj);
  return new Request("https://pilot.test/github/webhook",{
    method:"POST",headers:{
      "x-github-event":"pull_request","x-github-delivery":ID,
      "x-hub-signature-256":"sha256="+createHmac("sha256",secret).update(body).digest("hex")
    },body
  });
}
function testEnv(){
  const pending=[];
  return {pending,env:{GITHUB_WEBHOOK_SECRET:SECRET,
    PR_EVENTS:{async send(x){pending.push(x);}}}};
}
test("authentic signed GitHub event queues only exact scoped descriptor",async()=>{
  const {pending,env}=testEnv();
  assert.equal((await receiveWebhook(signed(),env)).status,202);
  assert.deepEqual(pending,[{
    schema:"mathgraph.github-pr-delivery.v0",repository:SCOPE.repository,
    number:19,installationID:42,sha:SHA,delivery:ID,action:"opened"
  }]);
});
test("reject bad signature, foreign repository and foreign head",async()=>{
  const {pending,env}=testEnv();
  assert.equal((await receiveWebhook(signed(event(),"wrong-key"),env)).status,401);
  const bad=event();bad.pull_request.head.repo.full_name="outsider/fork";
  assert.equal((await receiveWebhook(signed(bad),env)).status,202);
  bad.pull_request.head.repo.full_name=SCOPE.repository;
  bad.repository.full_name="upstream/not-owned";
  assert.equal((await receiveWebhook(signed(bad),env)).status,202);
  assert.equal(pending.length,0);
});
test("queue failure returns 503 rather than prematurely acknowledging",async()=>{
  const {env}=testEnv();
  env.PR_EVENTS.send=async()=>{throw Error("queue unavailable");};
  assert.equal((await receiveWebhook(signed(),env)).status,503);
  assert.equal((await receiveWebhook(new Request("https://pilot.test/health"),env)).status,200);
  assert.equal((await receiveWebhook(new Request("https://pilot.test/no"),env)).status,404);
});
test("malformed event does not acquire work authority",()=>{
  assert.equal(parseSignedEvent({action:"closed"},ID,"pull_request"),null);
  assert.equal(parseSignedEvent(event(),"invalid","pull_request"),null);
});
test("registered App JWT signs exact Client ID with RSA",()=>{
  const keys=generateKeyPairSync("rsa",{modulusLength:2048});
  const jwt=appJWT(keys.privateKey.export({type:"pkcs1",format:"pem"}).toString());
  const parts=jwt.split(".");
  assert.equal(parts.length,3);
  assert.equal(JSON.parse(Buffer.from(parts[1],"base64url")).iss,SCOPE.clientID);
  assert.equal(verify("RSA-SHA256",Buffer.from(parts[0]+"."+parts[1]),
    keys.publicKey,Buffer.from(parts[2],"base64url")),true);
});
