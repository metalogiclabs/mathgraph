import test from "node:test";
import assert from "node:assert/strict";
import {monitor} from "./check-resolve-monitor-v1.mjs";
const a="a".repeat(40),b="b".repeat(40);
const subject={repository:"metalogiclabs/mathgraph",pr:194,head_sha:a};
const report=(status,head=a,extra={})=>({
 subject:{...subject,head_sha:head},
 claim_dependencies:[{id:"native",requires:["e0"]}],
 results:[{id:"native",status}],
 ...extra
});
for (const forge of [true,{},[],1,"trusted"]) {
 test("caller-controlled requalification must not override changed evidence: "+JSON.stringify(forge),()=>{
  const before=report("UNKNOWN");
  const after=report("OBSERVED",a,{independent_requalification:forge});
  const result=monitor(before,after,{changedEvidenceIds:["e0"]});
  assert.equal(result.transitions[0].to,"UNKNOWN");
  assert.equal(result.transitions[0].reason,"REQUALIFICATION_REQUIRED");
  assert.equal(result.permission,"ADVISORY_ONLY");
 });
}
test("caller-controlled requalification cannot reuse a changed head",()=>{
 const result=monitor(report("OBSERVED"),report("OBSERVED",b,{independent_requalification:true}));
 assert.equal(result.transitions[0].to,"UNKNOWN");
});
test("unaffected observation can remain observed",()=>{
 const result=monitor(report("OBSERVED"),report("OBSERVED"),{changedEvidenceIds:[]});
 assert.equal(result.transitions[0].to,"OBSERVED");
});
test("changed evidence failure remains blocked",()=>{
 const result=monitor(report("OBSERVED"),report("BLOCKED",{...subject}.head_sha,{independent_requalification:true}),{changedEvidenceIds:["e0"]});
 assert.equal(result.transitions[0].to,"BLOCKED");
});
