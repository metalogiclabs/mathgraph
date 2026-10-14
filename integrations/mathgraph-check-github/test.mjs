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
