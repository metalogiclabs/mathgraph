import test from "node:test";
import assert from "node:assert/strict";
import {generateKeyPairSync} from "node:crypto";
import {mkdtempSync,writeFileSync,readFileSync,existsSync,rmSync} from "node:fs";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {spawnSync} from "node:child_process";
import {fileURLToPath} from "node:url";
import {verifyConfiguredOwnerContract} from "./cloudflare/owner-auth.mjs";

const CLI=fileURLToPath(new URL("./owner-sign.mjs",import.meta.url));
const validContract=()=>({
  schema:"mathgraph.owner-contract.v1",
  subject:{repository:"metalogiclabs/go-ethereum",pr:19,
    sha:"a04aa77aaebd81d11274560e8d24d90c6f417589"},
  policy_version:"pilot-1",actor:"owner",action:"deploy",scope:"a",
  grant:{id:"g1",issuer:"owner",actor:"owner",action:"deploy",scope:"a",
    issued_at:100,expires_at:400},
  conditions:[{name:"safety",scope:"a",status:"INSUFFICIENT",source:"pending-review",
    on_false:"FAIL_SAFETY_VIOLATION",on_unresolved:"UNRESOLVED_SAFETY_EVIDENCE"}]
});
function inTemp(fn){
  const dir=mkdtempSync(join(tmpdir(),"mathgraph-owner-sign-test-"));
  try{return fn(dir);}finally{rmSync(dir,{recursive:true,force:true});}
}
function setup(dir){
  const keys=generateKeyPairSync("rsa",{modulusLength:2048});
  const contract=join(dir,"owner-contract.json"),key=join(dir,"owner-private.pem");
  const out=join(dir,"owner-envelope.json");
  writeFileSync(contract,JSON.stringify(validContract()));
  writeFileSync(key,keys.privateKey.export({type:"pkcs8",format:"pem"}),{mode:0o600});
  return {keys,contract,key,out};
}
const run=({contract,key,out})=>spawnSync(process.execPath,[CLI,
  "--contract",contract,"--key",key,"--out",out],{encoding:"utf8"});

test("local owner signer emits an independently verifiable exact-byte envelope",()=>inTemp(dir=>{
  const x=setup(dir),result=run(x);
  assert.equal(result.status,0,result.stderr);
  assert.equal(result.stdout.trim(),"SIGNED_OWNER_ENVELOPE_CREATED");
  const envelope=readFileSync(x.out,"utf8");
  const pub=x.keys.publicKey.export({type:"spki",format:"pem"}).toString();
  const checked=verifyConfiguredOwnerContract(envelope,pub);
  assert.equal(checked.verified,true);
  assert.equal(checked.contract.subject.pr,19);
  assert.equal(checked.contract.conditions[0].status,"INSUFFICIENT");
  assert.doesNotMatch(result.stdout+result.stderr,/PRIVATE KEY|BEGIN RSA/);
}));
test("local owner signer cannot silently replace an existing signed output",()=>inTemp(dir=>{
  const x=setup(dir);
  assert.equal(run(x).status,0);
  const previous=readFileSync(x.out,"utf8");
  writeFileSync(x.contract,JSON.stringify({...validContract(),policy_version:"changed"}));
  assert.notEqual(run(x).status,0);
  assert.equal(readFileSync(x.out,"utf8"),previous);
}));
test("local owner signer rejects malformed policy and invalid private key",()=>inTemp(dir=>{
  const x=setup(dir);
  writeFileSync(x.contract,'{"schema":"unqualified"}');
  const invalid=run(x);
  assert.notEqual(invalid.status,0);
  assert.match(invalid.stderr,/INVALID_OWNER_CONTRACT/);
  assert.equal(existsSync(x.out),false);
  writeFileSync(x.contract,JSON.stringify(validContract()));
  writeFileSync(x.key,"not-a-private-key");
  const badKey=run(x);
  assert.notEqual(badKey.status,0);
  assert.match(badKey.stderr,/INVALID_PRIVATE_KEY/);
  assert.equal(existsSync(x.out),false);
}));
