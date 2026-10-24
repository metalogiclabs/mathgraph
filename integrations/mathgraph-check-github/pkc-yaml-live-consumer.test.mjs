import test from "node:test";
import assert from "node:assert/strict";
import {consumePKCYaml as consume} from "./pkc-yaml-live-consumer.mjs";
const head="05a6057e94d899ded94374db4a831963034aea93";
test("disabled bridge makes no API calls",async()=>{
 let calls=0;const r=await consume({githubAPI:async()=>{calls++},enabled:false});
 assert.equal(r.state,"DISABLED");assert.equal(calls,0)});
test("wrong repository denied",async()=>await assert.rejects(consume({
 githubAPI:async()=>{},enabled:true,repo:"other/repo",pr:178,head,token:"token",
 installed:true}),/APP_CARRIER_NOT_AUTHORIZED/));
test("missing installation token denied",async()=>await assert.rejects(consume({
 githubAPI:async()=>{},enabled:true,repo:"metalogiclabs/mathgraph",pr:178,head,
 installed:true}),/APP_CARRIER_NOT_AUTHORIZED/));
test("unqualified carrier denied before artifact access",async()=>{
 let calls=0;await assert.rejects(consume({githubAPI:async path=>{calls++;
 if(path.includes("/pulls/"))return {head:{sha:head},state:"open",
   base:{repo:{full_name:"metalogiclabs/mathgraph"}},
   head:{sha:head,repo:{full_name:"metalogiclabs/mathgraph"}}};
 return {}},enabled:true,repo:"metalogiclabs/mathgraph",pr:178,head,token:"token",
 installed:true}),/DEDICATED_CARRIER_NOT_QUALIFIED/);assert.equal(calls,2)});
test("carrier must be open and its exact base/head repositories verified",async()=>{
 for(const change of [{state:"closed"},{head:{sha:head,repo:{full_name:"foreign/repo"}}},
   {base:{repo:{full_name:"foreign/repo"}}}]){
   let calls=0;
   await assert.rejects(consume({githubAPI:async()=>{calls++;
     return {state:"open",head:{sha:head,repo:{full_name:"metalogiclabs/mathgraph"}},
       base:{repo:{full_name:"metalogiclabs/mathgraph"}},...change};},
     enabled:true,repo:"metalogiclabs/mathgraph",pr:178,head,token:"token",
     installed:true}),/STALE_CARRIER_HEAD/);
   assert.equal(calls,1);
 }
});
