import {test} from "node:test";
import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import {bindQualifiedNativeReceipt as bind} from "./native-receipt-bridge.mjs";
const sum=b=>createHash("sha256").update(b).digest("hex");
const subject={repository:"teorth/IEANTN",pr:158,sha:"a".repeat(40)};
const receipt={schema:"metalogic.real-external-pr-native-evidence.v1",
  original_external_repo:subject.repository,protocol_sha256:sum("protocol"),
  qualified_count:1,action_authorization:"NONE",
  advisory_conclusion:"NEUTRAL_REVIEW_EVIDENCE_ONLY",code_repair_generated:"NO",
  method_generator_software_authorship:"HUMAN_WRITTEN",scientific_L7:"UNKNOWN",
  cases:[{pr:158,head_sha:subject.sha,base_sha:"b".repeat(40),
    result:"WARRANTED_BOUNDED_REAL_PR_NATIVE_REGRESSION",
    source_behavioral_proof:"RED_BASE_GREEN_HEAD_NATIVE_TESTS",
    application_to_external_owner:"READ_ONLY_NOT_INSTALLED",
    AST_derived_new_test_methods:["test_one"],
    before_source_with_head_tests:{test_count:1,exit_code:1},
    after_source_with_head_tests:{test_count:1,exit_code:0},
    old_full_suite_on_base:{test_count:11,exit_code:0},
    full_suite_on_head:{test_count:12,exit_code:0}}]};
const data=Buffer.from(JSON.stringify(receipt));
const pin=(id,commit)=>({repository:"heathsanchez/test",id,commit,workflow:".github/workflows/qualify.yml"});
const policy={schema:"metalogic.mathgraph-check.native-bridge-policy.v1",
 subject,baseSha:"b".repeat(40),protocolSha256:receipt.protocol_sha256,
 receiptSha256:sum(data),actionAuthorization:"NONE",selectedTests:1,
 baseSuite:11,headSuite:12,producer:pin(101,"c".repeat(40)),
 replay:pin(102,"d".repeat(40))};
const run=p=>({id:p.id,status:"completed",conclusion:"success",
 head_sha:p.commit,path:p.workflow,repository:{full_name:p.repository}});
const check={name:"MathGraph Check / evidence scope",status:"completed",
 conclusion:"neutral",output:{title:"BEHAVIORAL_SCOPE_UNKNOWN",summary:"ordinary App report"}};
function fixture(){return {assessment:{authority:"ADVISORY_ONLY",source:{...subject}},
 check:structuredClone(check),receiptBytes:Buffer.from(data),
 reviewedPolicy:structuredClone(policy),originalRun:run(policy.producer),
 independentReplayRun:run(policy.replay),currentPRHead:subject.sha}}
test("matching native receipt retains neutral Check and generic verdict",()=>{
 const x=bind(fixture());assert.equal(x.state,"WARRANTED_BOUNDED_HISTORICAL_NATIVE_RECEIPT");
 assert.equal(x.check.conclusion,"neutral");assert.equal(x.actionAuthorization,"NONE");
 assert.equal(x.check.output.title,"BEHAVIORAL_SCOPE_UNKNOWN");
 assert.match(x.check.output.summary,/ordinary App report/);
});
test("VALID foreign PR evidence cannot be attached to an owned PR",()=>{
 const x=fixture();x.assessment.source={repository:"metalogiclabs/go-ethereum",pr:19,sha:"e".repeat(40)};
 const r=bind(x);assert.equal(r.state,"UNKNOWN_SOURCE_SCOPE_MISMATCH");
 assert.deepEqual(r.check,check);
});
test("historic warrant and present source-head freshness are distinct",()=>{
 for(const head of [null,"f".repeat(40)]){
  const x=fixture();x.currentPRHead=head;
  assert.equal(bind(x).state,"STALE_OR_UNOBSERVED_SOURCE_HEAD");
 }
});
test("withdrawal removes present applicability without refuting historical tests",()=>{
 const x=fixture();x.reviewedPolicy.withdrawn=true;
 const r=bind(x);assert.equal(r.state,"STALE_WITHDRAWN_EVIDENCE");
 assert.equal(r.check.conclusion,"neutral");
});
test("tampered bytes and false-authority receipt reject",()=>{
 const x=fixture();x.receiptBytes=Buffer.from("{}");
 assert.throws(()=>bind(x),/RECEIPT_DIGEST_CHANGED/);
 const y=fixture();const f={...receipt,code_repair_generated:"YES"};
 y.receiptBytes=Buffer.from(JSON.stringify(f));y.reviewedPolicy.receiptSha256=sum(y.receiptBytes);
 assert.throws(()=>bind(y),/RECEIPT_AUTHORITY_INVALID/);
});
test("false native success rejects even if caller updates digest",()=>{
 const x=fixture();const f=structuredClone(receipt);
 f.cases[0].after_source_with_head_tests.exit_code=1;
 x.receiptBytes=Buffer.from(JSON.stringify(f));x.reviewedPolicy.receiptSha256=sum(x.receiptBytes);
 assert.throws(()=>bind(x),/NATIVE_BEHAVIOR_NOT_QUALIFIED/);
});
test("unqualified producer or independent replay is not a trust basis",()=>{
 const x=fixture();x.originalRun.conclusion="failure";
 assert.throws(()=>bind(x),/PRODUCER_RUN_NOT_QUALIFIED/);
 const y=fixture();y.independentReplayRun.head_sha="f".repeat(40);
 assert.throws(()=>bind(y),/REPLAY_RUN_NOT_QUALIFIED/);
});
test("non-neutral publisher or forged review authority is rejected",()=>{
 const x=fixture();x.check.conclusion="success";
 assert.throws(()=>bind(x),/CHECK_AUTHORITY_ESCALATION/);
 const y=fixture();y.assessment.authority="WARRANTED";
 assert.throws(()=>bind(y),/APP_ASSESSMENT_NOT_ADVISORY/);
});
