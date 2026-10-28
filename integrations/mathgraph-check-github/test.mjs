import test from "node:test";
import assert from "node:assert/strict";
import {createHmac,generateKeyPairSync,verify} from "node:crypto";
import {analyze,checkOutput,loadPR} from "./core.mjs";
import {signatureOK,makeJWT,accepted} from "./webhook.mjs";
const SHA="a04aa77aaebd81d11274560e8d24d90c6f417589";
const fixture={
  repository:"metalogiclabs/go-ethereum",number:19,sha:SHA,
  files_visibility:"COMPLETE",ci_visibility:"COMPLETE",
  files:[{filename:".github/workflows/bal-engine-crossfork-v19.yml",
      patch:"+echo remote_conflicting_fcu=UNKNOWN;concurrent_fcu=UNKNOWN\n"},
    {filename:"eth/catalyst/bal_engine_crossfork_v19_test.go",patch:"+func TestBALV19CrossForkAdmissionPredicate() {}"}],
  runs:[{id:38202260024,name:"BAL V19 Engine Crossfork Qualification (Fork Only)",
    head_sha:SHA,status:"completed",conclusion:"success"},
    {id:38202263201,name:"PR Format Validation",head_sha:SHA,
    status:"completed",conclusion:"success"}]
};
const ownerContract={
  schema:"mathgraph.owner-contract.v1",
  subject:{repository:fixture.repository,pr:fixture.number,sha:SHA},
  policy_version:"release-policy-v1",actor:"release-operator",
  action:"deploy",scope:"a",
  grant:{id:"g-a",issuer:"independent-release-owner",actor:"release-operator",
    action:"deploy",scope:"a",issued_at:100,expires_at:300},
  conditions:[
    {name:"safety",scope:"a",status:"WARRANTED_TRUE",source:"safety-assessment-v1",
      on_false:"FAIL_SAFETY_VIOLATION",on_unresolved:"UNRESOLVED_SAFETY_EVIDENCE"},
    {name:"viability",scope:"a",status:"WARRANTED_TRUE",source:"viability-assessment-v1",
      on_false:"FAIL_VIABILITY",on_unresolved:"UNRESOLVED_VIABILITY"}
  ]
};

test("green CI or PR-authored owner claims cannot grant admission",()=>{
  const x=structuredClone(fixture);
  x.owner_contract=structuredClone(ownerContract);
  const r=analyze(x);
  assert.equal(r.warrant.decision,"ABSTAIN");
  assert.deepEqual(r.warrant.residuals.map(x=>x.code),["UNRESOLVED_OWNER_CONTRACT"]);
  assert.equal(checkOutput(r).conclusion,"neutral");
});
test("externally configured exact-head grant with qualified conditions is packet-admitted only",()=>{
  const r=analyze(structuredClone(fixture),structuredClone(ownerContract),200);
  assert.equal(r.warrant.decision,"ADMIT");
  assert.deepEqual(r.warrant.residuals,[]);
  assert.equal(r.warrant.boundary,"OPERATOR_CONFIGURED_PACKET_ONLY");
  assert.equal(r.warrant.future.grant_expires_at,300);
  assert.equal(checkOutput(r).conclusion,"neutral");
  assert.match(checkOutput(r).output.summary,/not independent confirmation of the owner's intent/i);
});
test("wrong PR head and cross-scope grants fail closed without claiming definite absence",()=>{
  const stale=structuredClone(ownerContract);
  stale.subject.sha="f".repeat(40);
  const mismatch=analyze(structuredClone(fixture),stale,200).warrant;
  assert.equal(mismatch.decision,"ABSTAIN");
  assert.deepEqual(mismatch.residuals.map(x=>x.code),["UNRESOLVED_OWNER_CONTRACT_BINDING"]);
  const scope=structuredClone(ownerContract);
  scope.grant.scope="b";
  const wrongScope=analyze(structuredClone(fixture),scope,200).warrant;
  assert.equal(wrongScope.decision,"ABSTAIN");
  assert.ok(wrongScope.residuals.some(x=>x.code==="UNRESOLVED_AUTHORITY"));
});
test("the same present admissibility retains a different future expiration",()=>{
  const later=structuredClone(ownerContract);
  later.grant.expires_at=900;
  const today=analyze(structuredClone(fixture),ownerContract,200).warrant;
  const other=analyze(structuredClone(fixture),later,200).warrant;
  assert.equal(today.decision,"ADMIT");
  assert.equal(other.decision,"ADMIT");
  assert.notEqual(today.future.grant_expires_at,other.future.grant_expires_at);
  assert.equal(analyze(structuredClone(fixture),ownerContract,300).warrant.decision,"REFUSE");
  assert.equal(analyze(structuredClone(fixture),later,300).warrant.decision,"ADMIT");
});
test("revocation and evidence failures are retained, without losing unresolved obligations",()=>{
  const x=structuredClone(ownerContract);
  x.grant.revoked_at=180;
  x.conditions[0].status="WARRANTED_FALSE";
  x.conditions[1].status="CONFLICTING";
  const r=analyze(structuredClone(fixture),x,200).warrant;
  assert.equal(r.decision,"REFUSE");
  assert.deepEqual(r.residuals.map(x=>x.code),[
    "FAIL_GRANT_REVOKED","FAIL_SAFETY_VIOLATION","UNRESOLVED_VIABILITY"]);
});
test("bad operator packet never authorizes and names coverage uncertainty",()=>{
  const x=structuredClone(ownerContract);
  x.conditions[0].on_false="ADMIT_ANYTHING";
  const r=analyze(structuredClone(fixture),x,200).warrant;
  assert.equal(r.decision,"ABSTAIN");
  assert.deepEqual(r.residuals.map(x=>x.code),["UNRESOLVED_MODEL_COVERAGE"]);
});
test("green exact-head CI plus two explicit UNKNOWN scopes remains advisory",()=>{
  const r=analyze(structuredClone(fixture));
  assert.equal(r.ci.state,"GITHUB_REPORTED_SUCCESS_AT_EXACT_HEAD");
  assert.deepEqual(r.declared_limits.map(x=>x.name),["concurrent_fcu","remote_conflicting_fcu"]);
  assert.equal(r.finding.code,"DECLARED_VERIFICATION_RESIDUAL");
  assert.equal(r.authority,"ADVISORY_ONLY");
  assert.equal(checkOutput(r).conclusion,"neutral");
});
test("a successful run from a different head does not count",()=>{
  const x=structuredClone(fixture);x.runs[0].head_sha="f".repeat(40);
  assert.equal(analyze(x).ci.state,"NO_SUBSTANTIVE_CI_AT_HEAD");
});
test("later red same-name run supersedes earlier green",()=>{
  const x=structuredClone(fixture);
  x.runs.push({...x.runs[0],id:38299999999,conclusion:"failure"});
  assert.equal(analyze(x).finding.code,"CURRENT_HEAD_CI_UNRESOLVED");
});
test("deleted and context lines cannot declare current scope",()=>{
  const x=structuredClone(fixture);
  x.files[0].patch="-old_boundary=UNKNOWN\n context_unknown=UNKNOWN\n+ready=true\n";
  assert.deepEqual(analyze(x).declared_limits,[]);
});
test("truncated source and missing Actions permission fail closed",()=>{
  const x=structuredClone(fixture);
  x.files_visibility="TRUNCATED_AT_300";x.ci_visibility="UNKNOWN_NO_ACTIONS_ACCESS";
  const r=analyze(x);
  assert.equal(r.finding.code,"DIFF_SCOPE_INCOMPLETE");
  assert.equal(r.ci.state,"CI_VISIBILITY_UNKNOWN");
});
test("code changed without test file is question not failed verification",()=>{
  const x=structuredClone(fixture);
  x.files=[{filename:"core/engine.go",patch:"+return true"}];
  assert.equal(analyze(x).finding.code,"TEST_DELTA_ABSENT");
  assert.equal(checkOutput(analyze(x)).conclusion,"neutral");
});
test("invalid source identity rejected",()=>{
  for(const c of [{sha:"main"},{repository:"https://evil"},{number:0},{files:null}])
    assert.throws(()=>analyze({...fixture,...c}),/INVALID_PINNED_SNAPSHOT/);
});
test("HMAC checks raw bytes and rejects mutation",()=>{
  const raw=Buffer.from('{"action":"opened"}'),secret="test-secret";
  const signature="sha256="+createHmac("sha256",secret).update(raw).digest("hex");
  assert.equal(signatureOK(raw,signature,secret),true);
  assert.equal(signatureOK(Buffer.from("tamper"),signature,secret),false);
  assert.equal(signatureOK(raw,"",secret),false);
});
test("signed app JWT independently verifies using generated public key",()=>{
  const keys=generateKeyPairSync("rsa",{modulusLength:2048});
  const token=makeJWT(123,keys.privateKey,1700000000),parts=token.split(".");
  assert.equal(parts.length,3);
  assert.equal(verify("RSA-SHA256",Buffer.from(parts[0]+"."+parts[1]),
    keys.publicKey,Buffer.from(parts[2],"base64url")),true);
});
test("recommended GitHub Client ID works as JWT issuer without a secret leak",()=>{
  const keys=generateKeyPairSync("rsa",{modulusLength:2048});
  const issuer="Iv23lioiUs5KfHD7mkkw";
  const parts=makeJWT(issuer,keys.privateKey,1700000000).split(".");
  assert.equal(JSON.parse(Buffer.from(parts[1],"base64url")).iss,issuer);
  assert.equal(verify("RSA-SHA256",Buffer.from(parts[0]+"."+parts[1]),
    keys.publicKey,Buffer.from(parts[2],"base64url")),true);
  assert.throws(()=>makeJWT("invalid issuer!",keys.privateKey),/INVALID_APP_AUTH/);
});
test("only allowlisted PR events are accepted",()=>{
  const allow=new Set(["metalogiclabs/go-ethereum"]);
  assert.equal(accepted("pull_request","opened","metalogiclabs/go-ethereum",allow),true);
  assert.equal(accepted("push","opened","metalogiclabs/go-ethereum",allow),false);
  assert.equal(accepted("pull_request","opened","ethereum/go-ethereum",allow),false);
});

test("source-pinned GitHub PR loader validates repository and exact head before admission", async()=>{
  for(const bad of ["https://evil.example/test","../../../other","owner/second/third",""]){
    await assert.rejects(()=>loadPR(bad,19,"fixture"),/INVALID_REPO_PR/);
  }
  await assert.rejects(()=>loadPR("metalogiclabs/go-ethereum",0,"fixture"),
    /INVALID_REPO_PR/);
  const originalFetch=globalThis.fetch;
  const calls=[];
  const expectedSha="a04aa77aaebd81d11274560e8d24d90c6f417589";
  globalThis.fetch=async (input,opts)=>{
    const path=new URL(input).pathname;
    calls.push(path);
    assert.equal(opts.headers.Authorization,"Bearer fixture");
    if(path.endsWith("/pulls/19"))
      return new Response(JSON.stringify({head:{sha:expectedSha}}),{status:200});
    if(path.endsWith("/pulls/19/files"))
      return new Response(JSON.stringify([{filename:"eth/catalyst/check_test.go",
        patch:"+func TestSourceCase() {}"}]),{status:200});
    if(path.endsWith("/actions/runs"))
      return new Response(JSON.stringify({total_count:1,workflow_runs:[{
        id:12,name:"native source verifier",head_sha:expectedSha,
        status:"completed",conclusion:"success"}]}),{status:200});
    throw Error("UNEXPECTED_PATH "+path);
  };
  try{
    const snapshot=await loadPR("metalogiclabs/go-ethereum",19,"fixture");
    assert.equal(snapshot.sha,expectedSha);
    assert.equal(snapshot.files_visibility,"COMPLETE");
    assert.equal(snapshot.ci_visibility,"COMPLETE");
    assert.equal(snapshot.runs[0].head_sha,expectedSha);
    assert.equal(calls.length,3);
    const report=analyze(snapshot);
    assert.equal(report.source.sha,expectedSha);
    assert.equal(checkOutput(report).conclusion,"neutral");
  }finally{
    globalThis.fetch=originalFetch;
  }
});
