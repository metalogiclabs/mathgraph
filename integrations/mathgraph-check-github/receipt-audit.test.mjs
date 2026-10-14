import test from "node:test";
import assert from "node:assert/strict";
import {generateKeyPairSync,verify} from "node:crypto";
import {auditSignedDeliveryReceipts} from "./receipt-audit.mjs";

const sha="7c48a0811a21dad7ff192171e905663966e15c95";
const guid="ab1f6cde-a97f-4ca7-b315-286816ed1991";
function fixture({wrongApp=false,failed=false,missing=false}={}){
  const keys=generateKeyPairSync("rsa",{modulusLength:2048});
  const privateKey=keys.privateKey.export({type:"pkcs1",format:"pem"}).toString();
  const calls=[];
  const json=x=>new Response(JSON.stringify(x),{status:200});
  const list=missing?[]:[{
    id:321,guid,delivered_at:"2026-10-14T05:27:19Z",event:"pull_request",
    action:"edited",status_code:failed?503:202,redelivery:false
  }];
  const fetcher=async(url,init)=>{
    const path=new URL(url).pathname;
    calls.push(path);
    assert.equal(new URL(url).origin,"https://api.github.com");
    const t=init.headers.Authorization.slice(7).split(".");
    assert.equal(JSON.parse(Buffer.from(t[1],"base64url")).iss,"Iv23lioiUs5KfHD7mkkw");
    assert.equal(verify("RSA-SHA256",Buffer.from(t[0]+"."+t[1]),
      keys.publicKey,Buffer.from(t[2],"base64url")),true);
    if(path==="/app")return json({id:wrongApp?15368:5308912,
      owner:{login:"metalogiclabs"}});
    if(path==="/app/hook/deliveries")return json(list);
    if(path==="/app/hook/deliveries/321")return json({
      ...list[0],request:{payload:{
        repository:{full_name:"metalogiclabs/go-ethereum"},
        pull_request:{number:18,head:{sha}}
      }}
    });
    throw Error("UNEXPECTED_AUDIT_API_PATH");
  };
  return {privateKey,fetcher,calls};
}
test("verified app JWT reads GitHub's 202 receipt and binds PR and SHA",async()=>{
  const f=fixture();
  const value=await auditSignedDeliveryReceipts(f);
  assert.equal(value.authority,"GITHUB_APP_DELIVERY_RECEIPT");
  assert.equal(value.app_id,5308912);
  assert.equal(value.receipts.length,1);
  assert.equal(value.receipts[0].accepted_by_webhook,true);
  assert.equal(value.receipts[0].sha,sha);
  assert.deepEqual(f.calls,[
    "/app","/app/hook/deliveries","/app/hook/deliveries/321"
  ]);
});
test("no receipt and failed delivery cannot be promoted to success",async()=>{
  for(const opt of [{missing:true},{failed:true}]) {
    const f=fixture(opt);
    await assert.rejects(auditSignedDeliveryReceipts(f),
      /NO_GITHUB_ACCEPTED_TARGET_SIGNED_DELIVERY/);
  }
});
test("wrong registered App identity rejects before delivery listing",async()=>{
  const f=fixture({wrongApp:true});
  await assert.rejects(auditSignedDeliveryReceipts(f),
    /WRONG_REGISTERED_APP_IDENTITY/);
  assert.deepEqual(f.calls,["/app"]);
});

test("19-digit GitHub delivery IDs retain exact decimal digits through API request",async()=>{
  const f=fixture();
  const id="3848195435306942569";
  const guid="ab1f6cde-a97f-4ca7-b315-286816ed1991";
  const fetcher=async(url,opts)=>{
    const path=new URL(url).pathname;
    if(path==="/app/hook/deliveries"){
      return new Response('[{"id":'+id+
        ',"guid":"'+guid+'","delivered_at":"2026-10-14T05:27:20Z",'+
        '"event":"pull_request","action":"edited","status_code":202,"redelivery":false}]',
        {status:200});
    }
    if(path==="/app/hook/deliveries/"+id){
      return new Response(JSON.stringify({
        request:{payload:{
          repository:{full_name:"metalogiclabs/go-ethereum"},
          pull_request:{number:18,head:{sha}}
        }},
        status_code:202
      }),{status:200});
    }
    return f.fetcher(url,opts);
  };
  const r=await auditSignedDeliveryReceipts({
    privateKey:f.privateKey,fetcher
  });
  assert.equal(r.receipts[0].id,id);
  assert.equal(r.receipts[0].accepted_by_webhook,true);
});


test("real App PR #21 opened target accepts only exact registered PR/commit",async()=>{
  const f=fixture();
  const id="3848195435306942688",guid="ab1f6cde-a97f-4ca7-b315-286816ed1992";
  const fetcher=async(url,opts)=>{
    const path=new URL(url).pathname;
    if(path==="/app/hook/deliveries")
      return new Response('[{"id":'+id+',"guid":"'+guid+'","delivered_at":"2026-10-14T16:36:10Z","event":"pull_request","action":"opened","status_code":202,"redelivery":false}]');
    if(path==="/app/hook/deliveries/"+id)
      return new Response(JSON.stringify({status_code:202,request:{payload:{
        repository:{full_name:"metalogiclabs/go-ethereum"},
        pull_request:{number:21,head:{sha:"1c6e656e55b82819f36b0e9a6ea38809ce61b40b"}}
      }}}));
    return f.fetcher(url,opts);
  };
  const result=await auditSignedDeliveryReceipts({
    privateKey:f.privateKey,fetcher,target:"pr21",
    since:"2026-10-14T16:30:00Z"
  });
  assert.equal(result.pr,21);
  assert.equal(result.sha,"1c6e656e55b82819f36b0e9a6ea38809ce61b40b");
  assert.equal(result.receipts[0].action,"opened");
  assert.equal(result.receipts[0].id,id);
  assert.equal(result.receipts[0].status_code,202);
});
test("PR #21 cannot inherit PR #18 receipts or wrong source SHA",async()=>{
  const f=fixture();
  await assert.rejects(auditSignedDeliveryReceipts({
    privateKey:f.privateKey,fetcher:f.fetcher,target:"pr21"
  }),/NO_GITHUB_ACCEPTED_TARGET_SIGNED_DELIVERY/);
  await assert.rejects(auditSignedDeliveryReceipts({
    privateKey:f.privateKey,fetcher:f.fetcher,target:"unapproved"
  }),/UNSUPPORTED_AUDIT_TARGET/);
});
