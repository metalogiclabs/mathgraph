import test from "node:test";
import assert from "node:assert/strict";
import {routePKCYamlEvent as route} from "./pkc-yaml-event-gate.mjs";
const repo="metalogiclabs/mathgraph";
const payload={repository:{full_name:repo},installation:{id:42},
 pull_request:{number:171,head:{sha:"a".repeat(40)}}};
const good={signatureVerified:true,event:"pull_request",action:"edited",
 payload,allowRepos:[repo],enabled:true};
test("opt-in off preserves legacy route",()=>assert.equal(route({...good,enabled:false}).route,"LEGACY_ONLY"));
test("signed scoped event admitted",()=>assert.equal(route(good).route,"PKC_YAML_ADVISORY"));
test("unsigned event denied",()=>assert.equal(route({...good,signatureVerified:false}).route,"DENY"));
test("foreign carrier denied",()=>assert.equal(route({...good,payload:{...payload,repository:{full_name:"other/repo"}}}).route,"DENY"));
test("stale or invalid SHA denied",()=>assert.equal(route({...good,payload:{...payload,pull_request:{number:171,head:{sha:"bad"}}}}).route,"DENY"));
test("unsupported event denied",()=>assert.equal(route({...good,event:"push"}).route,"DENY"));
test("unlisted repository denied",()=>assert.equal(route({...good,allowRepos:[]}).route,"DENY"));
