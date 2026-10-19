import test from "node:test";
import assert from "node:assert/strict";
import {createHmac} from "node:crypto";
import {processPKCYamlDelivery as process} from "./webhook-pkc-yaml.mjs";
const secret="signed-webhook-test-secret";
const repo="metalogiclabs/mathgraph";
const payload={repository:{full_name:repo},installation:{id:42},
 pull_request:{number:171,head:{sha:"a".repeat(40)}}};
const raw=Buffer.from(JSON.stringify(payload));
const signature="sha256="+createHmac("sha256",secret).update(raw).digest("hex");
const base={raw,signature,event:"pull_request",action:"edited",payload,secret,allowRepos:[repo]};
test("valid signed delivery is legacy-only when disabled",async()=>{
 let n=0;const r=await process({...base,enabled:false,githubAPI:async()=>n++});
 assert.equal(r.state,"LEGACY_ONLY");assert.equal(n,0)});
test("bad HMAC rejected",async()=>{
 const r=await process({...base,signature:"sha256"+"0".repeat(64),enabled:true});
 assert.equal(r.status,401);assert.equal(r.state,"DENY")});
test("valid signed opt-in event missing installation token fails closed",async()=>{
 const r=await process({...base,enabled:true});
 assert.equal(r.state,"UNKNOWN");assert.equal(r.reason,"INSTALLATION_AUTH_MISSING")});
test("foreign event ignored",async()=>{
 const r=await process({...base,event:"push",enabled:true});
 assert.equal(r.state,"IGNORED")});
