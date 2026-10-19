import test from "node:test";
import assert from "node:assert/strict";
import {publishPKCYaml} from "./pkc-yaml-publish-adapter.mjs";
test("missing API rejects",async()=>await assert.rejects(
 publishPKCYaml({repo:"metalogiclabs/mathgraph",pr:171,head:"a".repeat(40)}),/APP_API_REQUIRED/));
test("foreign repository rejects before API",async()=>await assert.rejects(
 publishPKCYaml({api:async()=>{throw Error("UNEXPECTED_API")},repo:"other/repo",pr:1,
 head:"a".repeat(40)}),/UNAUTHORIZED_CARRIER/));
test("stale head rejects before publication",async()=>{
 let calls=0;
 await assert.rejects(publishPKCYaml({api:async()=>{calls++;return {head:{sha:"b".repeat(40)}}},
 repo:"metalogiclabs/mathgraph",pr:171,head:"a".repeat(40)}),/STALE_PR_HEAD/);
 assert.equal(calls,1);
});
test("incomplete check census rejects",async()=>{
 let calls=0;
 await assert.rejects(publishPKCYaml({api:async path=>{calls++;
 if(path.includes("/pulls/"))return {head:{sha:"a".repeat(40)}};
 return {total_count:2,check_runs:[]}},
 repo:"metalogiclabs/mathgraph",pr:171,head:"a".repeat(40)}),/CHECK_CENSUS_INCOMPLETE/);
 assert.equal(calls,2);
});
test("unauthenticated archive never writes Check",async()=>{
 let writes=0;
 await assert.rejects(publishPKCYaml({api:async(path,method)=>{
 if(method==="POST")writes++;
 if(path.includes("/pulls/"))return {head:{sha:"a".repeat(40)}};
 return {total_count:0,check_runs:[]}},
 repo:"metalogiclabs/mathgraph",pr:171,head:"a".repeat(40),installed:true,
 zipBytes:new Uint8Array([1,2,3]),artifactMetadata:{}}),/PUBLICATION_DENIED/);
 assert.equal(writes,0);
});
