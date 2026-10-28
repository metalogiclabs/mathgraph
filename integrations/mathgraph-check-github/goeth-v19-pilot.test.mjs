// First-party, source-pinned GOETH pilot. All normative grants and condition
// values in this file are SYNTHETIC controls, never permissions to merge.
import test from "node:test";
import assert from "node:assert/strict";
import {generateKeyPairSync,sign} from "node:crypto";
import {analyze} from "./analysis.mjs";
import {verifyConfiguredOwnerContract} from "./cloudflare/owner-auth.mjs";
import {V19} from "./geth-v19-evidence.mjs";

const snapshot={
  repository:V19.repository,number:V19.pr,sha:V19.sha,
  files_visibility:"COMPLETE",ci_visibility:"COMPLETE",
  files:[
    {filename:V19.workflow,
      patch:'+echo "V19_BOUNDARY=predicate_plus_valid_engine_controls;remote_conflicting_fcu=UNKNOWN;concurrent_fcu=UNKNOWN"'},
    {filename:"eth/catalyst/bal_engine_crossfork_v19_test.go",
      patch:"+func TestBALV19CrossForkAdmissionPredicate(t *testing.T) {}"},
    {filename:"research/bal_v19_engine_crossfork_gate.md",patch:"+Status: CANDIDATE"}
  ],
  runs:[{id:V19.run,name:"BAL V19 Engine Crossfork Qualification (Fork Only)",
    head_sha:V19.sha,status:"completed",conclusion:"success"}]
};

const condition=(name,status)=>({name,scope:"bal-v19",status,
  source:"SYNTHETIC_CONTROL_ONLY",
  on_false:"FAIL_"+name.toUpperCase(),
  on_unresolved:"UNRESOLVED_"+name.toUpperCase()});
const policy=()=>({
  schema:"mathgraph.owner-contract.v1",
  subject:{repository:V19.repository,pr:V19.pr,sha:V19.sha},
  policy_version:"synthetic-goeth-v0",actor:"synthetic-maintainer",
  action:"merge",scope:"bal-v19",
  grant:{id:"synthetic-g1",issuer:"synthetic-issuer",actor:"synthetic-maintainer",
    action:"merge",scope:"bal-v19",issued_at:100,expires_at:300},
  conditions:[
    condition("predicate","WARRANTED_TRUE"),
    condition("remote_conflicting_fcu","INSUFFICIENT"),
    condition("concurrent_fcu","INSUFFICIENT")
  ]
});

const signer=generateKeyPairSync("rsa",{modulusLength:2048});
const publicKey=signer.publicKey.export({type:"spki",format:"pem"}).toString();
function signed(c){
  const payload_b64=Buffer.from(JSON.stringify(c)).toString("base64url");
  const signature_b64=sign("RSA-SHA256",
    Buffer.from("MathGraph owner-contract v1\n"+payload_b64),signer.privateKey)
    .toString("base64url");
  return {schema:"mathgraph.signed-owner-contract.v1",payload_b64,signature_b64};
}
function assess(c,asOf=200){
  if(c===null) return analyze(snapshot,null,asOf).warrant;
  const verified=verifyConfiguredOwnerContract(JSON.stringify(signed(c)),publicKey);
  assert.equal(verified.verified,true);
  return analyze(snapshot,verified.contract,asOf).warrant;
}
function setStatus(c,name,status){
  const x=c.conditions.find(x=>x.name===name);
  assert.ok(x);
  x.status=status;
}

test("GOETH source-boundary fixture retains both declared UNKNOWNs",()=>{
  const r=analyze(snapshot);
  assert.equal(r.authority,"ADVISORY_ONLY");
  assert.equal(r.ci.state,"GITHUB_REPORTED_SUCCESS_AT_EXACT_HEAD");
  assert.equal(r.finding.code,"DECLARED_VERIFICATION_RESIDUAL");
  assert.deepEqual(r.declared_limits.map(x=>x.name),
    ["concurrent_fcu","remote_conflicting_fcu"]);
  assert.equal(assess(null).decision,"ABSTAIN");
});

test("GOETH synthetic same-packet controls preserve negative, positive and future distinctions",()=>{
  const cases=[];
  const add=(name,c,expected,asOf=200)=>{
    const result=assess(c,asOf);
    cases.push({name,expected,observed:result.decision,
      residuals:result.residuals.map(x=>x.code)});
    assert.equal(result.decision,expected,name);
  };
  const unknown=policy();
  add("known-native-control-but-two-missing-tests",unknown,"ABSTAIN");
  const extra=structuredClone(unknown);
  extra.conditions.push(condition("redundant_attestation","WARRANTED_TRUE"));
  add("more-nondiscriminating-evidence",extra,"ABSTAIN");
  const partial=structuredClone(unknown);
  setStatus(partial,"remote_conflicting_fcu","WARRANTED_TRUE");
  add("one-hypothetically-separating-observation",partial,"ABSTAIN");
  const resolved=structuredClone(partial);
  setStatus(resolved,"concurrent_fcu","WARRANTED_TRUE");
  add("both-hypothetically-resolved",resolved,"ADMIT");
  const failed=structuredClone(resolved);
  setStatus(failed,"remote_conflicting_fcu","WARRANTED_FALSE");
  add("negative-remote-test",failed,"REFUSE");
  const revoked=structuredClone(resolved);revoked.grant.revoked_at=190;
  add("revoked-grant",revoked,"REFUSE");
  const wrongScope=structuredClone(resolved);wrongScope.grant.scope="other";
  add("wrong-grant-scope",wrongScope,"ABSTAIN");
  const wrongHead=structuredClone(resolved);wrongHead.subject.sha="f".repeat(40);
  add("wrong-source-sha",wrongHead,"ABSTAIN");
  add("valid-grant-before-expiry",resolved,"ADMIT",299);
  add("valid-grant-after-expiry",resolved,"REFUSE",300);
  const long=structuredClone(resolved);long.grant.expires_at=900;
  add("same-present-decision-later-expiry",long,"ADMIT",300);
  const allowedTest=structuredClone(resolved);
  allowedTest.action="test";allowedTest.grant.action="test";
  add("already-authorized-test-proceeds",allowedTest,"ADMIT");
  assert.equal(assess(resolved,200).future.grant_expires_at,300);
  assert.equal(assess(long,200).future.grant_expires_at,900);
  assert.ok(cases.every(x=>x.expected===x.observed));
  const baseline=cases.map(x=>({name:x.name,decision:"ADMIT"}));
  const baselineFalseAdmits=cases.filter(x=>x.expected!=="ADMIT").length;
  assert.ok(baselineFalseAdmits>0);
  console.log("GOETH_SYNTHETIC_MECHANICS "+JSON.stringify({
    source:V19.repository+"#"+V19.pr+"@"+V19.sha,
    controls:cases.length,packetAgreement:cases.length,
    ciOnlyAdmits:baseline.length,ciOnlyUnsupportedAdmissions:baselineFalseAdmits,
    comparator:"CI_ONLY_HEURISTIC_NOT_FRONTIER_AGENT",
    evidentiaryLimit:"SYNTHETIC_GRANTS_AND_CONDITIONS_NOT_OWNER_AUTHORITY"
  }));
});

test("GOETH signed claims can still hide the missing frame (known design residual)",()=>{
  // Signatures establish origin/bytes only. The current generic evaluator has
  // no independent oracle requiring these specific BAL V19 obligations.
  const falseResolution=policy();
  for(const x of falseResolution.conditions) x.status="WARRANTED_TRUE";
  const omitted=policy();
  omitted.conditions=omitted.conditions.slice(0,1);
  const observed=[assess(falseResolution),assess(omitted)];
  assert.deepEqual(observed.map(x=>x.decision),["ADMIT","ADMIT"]);
  assert.deepEqual(analyze(snapshot).declared_limits.map(x=>x.name),
    ["concurrent_fcu","remote_conflicting_fcu"]);
  console.log("GOETH_KNOWN_SEMANTIC_GAPS "+JSON.stringify({
    source:V19.sha,controls:2,unjustifiedPacketAdmits:2,
    independentReference:"ABSTAIN_PENDING_ACTUAL_REMOTE_AND_CONCURRENT_TESTS",
    rootCause:"AUTHENTIC_SIGNATURE_DOES_NOT_VERIFY_EVIDENCE_OR_FRAME_COMPLETENESS",
    severity:"PACKET_RELATIVE_ONLY;PUBLIC_CHECK_REMAINS_NEUTRAL"
  }));
});

test("GOETH altered signed evidence cannot pass the pinned key",()=>{
  const packet=signed(policy());
  packet.payload_b64=Buffer.from('{"tampered":true}').toString("base64url");
  assert.deepEqual(verifyConfiguredOwnerContract(JSON.stringify(packet),publicKey),
    {verified:false,code:"UNRESOLVED_OWNER_SIGNATURE"});
});
