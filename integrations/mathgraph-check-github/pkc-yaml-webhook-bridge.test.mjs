import test from "node:test";
import assert from "node:assert/strict";
import {handlePKCYamlSignedEvent as handle} from "./pkc-yaml-webhook-bridge.mjs";
const repo="metalogiclabs/mathgraph";
const payload={repository:{full_name:repo},installation:{id:42},
 pull_request:{number:171,head:{sha:"a".repeat(40)}}};
const base={event:"pull_request",action:"edited",payload,
 signatureVerified:true,enabled:true,allowRepos:[repo]};
test("disabled bridge does not call GitHub",async()=>{
 let n=0;const r=await handle({...base,enabled:false,githubAPI:async()=>n++});
 assert.equal(r.state,"LEGACY_ONLY");assert.equal(n,0)});
test("unsigned delivery does not call GitHub",async()=>{
 let n=0;const r=await handle({...base,signatureVerified:false,githubAPI:async()=>n++});
 assert.equal(r.state,"DENY");assert.equal(n,0)});
test("missing installation authorization fails closed",async()=>{
 const r=await handle(base);assert.equal(r.state,"UNKNOWN");
 assert.equal(r.reason,"INSTALLATION_AUTH_MISSING")});
test("foreign event fails closed",async()=>{
 const r=await handle({...base,event:"push"});assert.equal(r.state,"DENY")});
