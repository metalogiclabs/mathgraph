import test from "node:test";
import assert from "node:assert/strict";
import {consumePKCYaml as consume} from "./pkc-yaml-live-consumer.mjs";
const head="a".repeat(40);
test("disabled bridge makes no API calls",async()=>{
 let calls=0;const r=await consume({githubAPI:async()=>{calls++},enabled:false});
 assert.equal(r.state,"DISABLED");assert.equal(calls,0)});
test("wrong repository denied",async()=>await assert.rejects(consume({
 githubAPI:async()=>{},enabled:true,repo:"other/repo",pr:171,head,token:"token",
 installed:true}),/APP_CARRIER_NOT_AUTHORIZED/));
test("missing installation token denied",async()=>await assert.rejects(consume({
 githubAPI:async()=>{},enabled:true,repo:"metalogiclabs/mathgraph",pr:171,head,
 installed:true}),/APP_CARRIER_NOT_AUTHORIZED/));
test("missing artifact authority denied before Check write",async()=>{
 let calls=0;await assert.rejects(consume({githubAPI:async()=>{calls++;return {}},
 enabled:true,repo:"metalogiclabs/mathgraph",pr:171,head,token:"token",
 installed:true}),/ARTIFACT_AUTHORITY_MISMATCH/);assert.equal(calls,1)});
