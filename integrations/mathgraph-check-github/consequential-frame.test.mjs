import test from "node:test";
import assert from "node:assert/strict";
import {createHash, generateKeyPairSync, sign} from "node:crypto";
import {verifyConfiguredOwnerContract} from "./cloudflare/owner-auth.mjs";
import {assessConsequentialFrame} from "./consequential-frame.mjs";

const SHA="a04aa77aaebd81d11274560e8d24d90c6f417589";
const source={repository:"metalogiclabs/go-ethereum",pr:19,sha:SHA};
const snapshot={repository:source.repository,number:19,sha:SHA};
const signer=generateKeyPairSync("rsa",{modulusLength:2048});
const publicKey=signer.publicKey.export({type:"spki",format:"pem"}).toString();
const condition=(name,status)=>({name,scope:"bal-v19",
  source:"SYNTHETIC_SIGNED_ASSERTION",status,
  on_false:"FAIL_"+name.toUpperCase(),
  on_unresolved:"UNRESOLVED_"+name.toUpperCase()});

const contract=()=>({
  schema:"mathgraph.owner-contract.v1",subject:structuredClone(source),
  policy_version:"synthetic-boundary-v1",actor:"test-owner",
  action:"merge",scope:"bal-v19",
  grant:{id:"synthetic-grant",issuer:"test-issuer",actor:"test-owner",
    action:"merge",scope:"bal-v19",issued_at:100,expires_at:300},
  conditions:[condition("predicate","WARRANTED_TRUE"),
    condition("remote_conflicting_fcu","INSUFFICIENT"),
    condition("concurrent_fcu","INSUFFICIENT")]
});

const frame=()=>({
  schema:"mathgraph.consequential-research-frame.v1",
  authority:"FROZEN_RESEARCH_ORACLE_ONLY",
  subject:structuredClone(source),policy_version:"synthetic-boundary-v1",
  action:"merge",scope:"bal-v19",
  native_profile:{state:"WARRANTED_BOUNDED_HISTORICAL_NATIVE_ARTIFACT",
    subject:structuredClone(source)},
  required:[
    {name:"predicate",source:"V19_NATIVE_ARTIFACT_11725753900",native_status:"WARRANTED_TRUE"},
    {name:"remote_conflicting_fcu",source:"goeth-v19-not-tested",native_status:"INSUFFICIENT"},
    {name:"concurrent_fcu",source:"goeth-v19-not-tested",native_status:"INSUFFICIENT"}
  ]
});
const native=()=>({state:"WARRANTED_BOUNDED_HISTORICAL_NATIVE_ARTIFACT",
  subject:structuredClone(source),observations:[
    {name:"predicate",scope:"bal-v19",status:"WARRANTED_TRUE",
      source:"V19_NATIVE_ARTIFACT_11725753900"}
  ]});
const digest=raw=>createHash("sha256").update(raw).digest("hex");
function verified(c){
  const payload_b64=Buffer.from(JSON.stringify(c)).toString("base64url");
  const signature_b64=sign("RSA-SHA256",
    Buffer.from("MathGraph owner-contract v1\n"+payload_b64),signer.privateKey)
    .toString("base64url");
  const result=verifyConfiguredOwnerContract(JSON.stringify({
    schema:"mathgraph.signed-owner-contract.v1",payload_b64,signature_b64
  }),publicKey);
  assert.equal(result.verified,true);
  return result;
}
function assess({c=contract(),f=frame(),n=native(),asOf=200,wrongDigest=false,
  owner=undefined,s=snapshot}={}){
  const frameBytes=JSON.stringify(f);
  return assessConsequentialFrame({snapshot:s,
    verifiedOwner:owner??verified(c),frameBytes,
    frameSha256:wrongDigest?"f".repeat(64):digest(frameBytes),
    nativeReceipt:n,asOf});
}

test("signed falsely-true native assertions cannot erase two source-native UNKNOWN obligations",()=>{
  const c=contract();
  c.conditions.forEach(x=>x.status="WARRANTED_TRUE");
  const result=assess({c});
  assert.equal(result.decision,"ABSTAIN");
  assert.deepEqual(result.missing_observations,
    ["remote_conflicting_fcu","concurrent_fcu"]);
  assert.ok(result.residuals.some(x=>x.code==="UNRESOLVED_REMOTE_CONFLICTING_FCU"));
  assert.equal(result.boundary,"FROZEN_RESEARCH_FRAME_ADVISORY_ONLY");
});

test("signed omission of either required obligation cannot authorize merge",()=>{
  for(const omitted of ["remote_conflicting_fcu","concurrent_fcu"]){
    const c=contract();
    c.conditions=c.conditions.filter(x=>x.name!==omitted);
    const result=assess({c});
    assert.equal(result.decision,"ABSTAIN");
    assert.ok(result.residuals.some(x=>x.code==="UNRESOLVED_OBLIGATION_FRAME_INCOMPLETE"));
  }
});

test("exact historical receipt qualifies predicate but not undocumented FCU behavior",()=>{
  const result=assess();
  assert.equal(result.decision,"ABSTAIN");
  assert.equal(result.evidence.find(x=>x.name==="predicate").status,"WARRANTED_TRUE");
  assert.equal(result.evidence.find(x=>x.name==="concurrent_fcu").status,"INSUFFICIENT");
});

test("real missing native receipt or wrong subject withdraws even the predicate warrant",()=>{
  for(const n of [null,{...native(),state:"UNKNOWN_NATIVE_RUN_IDENTITY_MISMATCH"},
    {...native(),subject:{...source,sha:"b".repeat(40)}}]){
    const result=assess({n});
    assert.equal(result.decision,"ABSTAIN");
    assert.ok(result.missing_observations.includes("predicate"));
  }
});

test("matching receipt envelope without native observation cannot confer predicate truth",()=>{
  const result=assess({n:{...native(),observations:[]}});
  assert.equal(result.decision,"ABSTAIN");
  assert.ok(result.missing_observations.includes("predicate"));
});

test("native observation cannot overrule the frozen unknown obligation ceiling",()=>{
  const n=native();n.observations.push({name:"remote_conflicting_fcu",
    scope:"bal-v19",status:"WARRANTED_TRUE",source:"goeth-v19-not-tested"});
  const c=contract();c.conditions.forEach(x=>x.status="WARRANTED_TRUE");
  const result=assess({n,c});
  assert.equal(result.decision,"ABSTAIN");
  assert.ok(result.missing_observations.includes("remote_conflicting_fcu"));
});

test("receipt contradicting the frozen true ceiling is CONFLICTING, not a fabricated positive or false refusal",()=>{
  const n=native();n.observations[0].status="WARRANTED_FALSE";
  const result=assess({n});
  assert.equal(result.decision,"ABSTAIN");
  assert.equal(result.evidence.find(x=>x.name==="predicate").status,"CONFLICTING");
  assert.ok(result.missing_observations.includes("predicate"));
  assert.ok(!result.residuals.some(x=>x.code==="FAIL_PREDICATE"));
});

test("a separately framed test-only action has a non-vacuous synthetic positive",()=>{
  const f=frame(),c=contract();
  f.action="test";f.required=f.required.slice(0,1);
  c.action="test";c.grant.action="test";c.conditions=c.conditions.slice(0,1);
  const result=assess({f,c});
  assert.equal(result.decision,"ADMIT");
  assert.deepEqual(result.missing_observations,[]);
  assert.equal(result.future.grant_expires_at,300);
  assert.equal(result.boundary,"FROZEN_RESEARCH_FRAME_ADVISORY_ONLY");
});

test("a supported native FALSE overrides a contradictory signed TRUE",()=>{
  const f=frame();
  f.required[0].native_status="WARRANTED_FALSE";
  const n=native();n.observations[0].status="WARRANTED_FALSE";
  const result=assess({f,n});
  assert.equal(result.decision,"REFUSE");
  assert.ok(result.residuals.some(x=>x.code==="FAIL_PREDICATE"));
});

test("grant expiry and revocation defeat even a positive framed test",()=>{
  const f=frame(),c=contract();
  f.action="test";f.required=f.required.slice(0,1);
  c.action="test";c.grant.action="test";c.conditions=c.conditions.slice(0,1);
  assert.equal(assess({f,c,asOf:299}).decision,"ADMIT");
  assert.equal(assess({f,c,asOf:300}).decision,"REFUSE");
  c.grant.revoked_at=190;
  assert.equal(assess({f,c,asOf:200}).decision,"REFUSE");
});

test("wrong frame digest, subject, action and unverified signature ABSTAIN",()=>{
  assert.equal(assess({wrongDigest:true}).decision,"ABSTAIN");
  const f=frame();f.subject.sha="e".repeat(40);
  assert.equal(assess({f}).decision,"ABSTAIN");
  const c=contract();c.action="deploy";c.grant.action="deploy";
  assert.equal(assess({c}).decision,"ABSTAIN");
  const wrongPolicy=frame();wrongPolicy.policy_version="unrelated-v2";
  assert.equal(assess({f:wrongPolicy}).decision,"ABSTAIN");
  assert.equal(assess({owner:{verified:false,code:"UNRESOLVED_OWNER_SIGNATURE"}}).decision,"ABSTAIN");
});

test("duplicate or structurally ambiguous frozen requirements fail closed",()=>{
  const duplicate=frame();duplicate.required.push(duplicate.required[0]);
  assert.equal(assess({f:duplicate}).decision,"ABSTAIN");
  const malformed=frame();malformed.required=[];
  assert.equal(assess({f:malformed}).decision,"ABSTAIN");
});
