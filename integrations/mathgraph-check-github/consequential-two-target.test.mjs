import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync,existsSync} from "node:fs";
import {createHash,generateKeyPairSync,sign} from "node:crypto";
import {join,dirname,resolve} from "node:path";
import {fileURLToPath} from "node:url";
import {spawnSync} from "node:child_process";
import {verifyConfiguredOwnerContract} from "./cloudflare/owner-auth.mjs";
import {analyze,checkOutput} from "./analysis.mjs";
import {appendGethV19NativeEvidence,V19} from "./geth-v19-evidence.mjs";
import {appendExternalNativeReceipt,EVIDENCE} from "./external-native-receipt.mjs";
import {replayFrameCase,conventionalReference} from "./consequential-two-target-replay.mjs";

const root=dirname(fileURLToPath(import.meta.url));
const read=name=>readFileSync(join(root,"fixtures",name),"utf8");
const goethFrame=read("consequential-goeth-v19.v1.json").trimEnd();
const goccyFrame=read("consequential-goccy-pr958.v1.json").trimEnd();
const sha256=text=>createHash("sha256").update(text).digest("hex");
// Independent review pins for the canonical UTF-8 JSON bytes (no terminal LF).
const FRAME_PINS={
  "metalogiclabs/go-ethereum":"b6ee6aee99405607e924b8eba6a6b668522b0c40fdace4c7f0d9ecb3bf2e50cd",
  "goccy/go-yaml":"0f36816614d9b7464a437f60680b663e25783161f9831c2bff6067f912c1736c"
};
const keys=generateKeyPairSync("rsa",{modulusLength:2048});
const pub=keys.publicKey.export({type:"spki",format:"pem"}).toString();
const condition=(name,status,scope)=>({name,status,scope,
  source:"SYNTHETIC_ASSERTION_ONLY",on_false:"FAIL_"+name.toUpperCase(),
  on_unresolved:"UNRESOLVED_"+name.toUpperCase()});
function signed(frame,overrides={}){
  const c={schema:"mathgraph.owner-contract.v1",subject:frame.subject,
    policy_version:frame.policy_version,actor:"test-reviewer",
    action:frame.action,scope:frame.scope,
    grant:{id:"synthetic-grant",issuer:"not-a-real-owner",
      actor:"test-reviewer",action:frame.action,scope:frame.scope,
      issued_at:100,expires_at:300},
    conditions:frame.required.map(r=>condition(r.name,"WARRANTED_TRUE",frame.scope)),
    ...overrides};
  const payload_b64=Buffer.from(JSON.stringify(c)).toString("base64url");
  const signature_b64=sign("RSA-SHA256",
    Buffer.from("MathGraph owner-contract v1\n"+payload_b64),keys.privateKey)
    .toString("base64url");
  const verified=verifyConfiguredOwnerContract(JSON.stringify({
    schema:"mathgraph.signed-owner-contract.v1",payload_b64,signature_b64
  }),pub);
  assert.equal(verified.verified,true);
  return verified;
}
const snapshot=frame=>({repository:frame.subject.repository,
  number:frame.subject.pr,sha:frame.subject.sha});

async function gethNative(){
  const s={...snapshot(JSON.parse(goethFrame)),
    files_visibility:"COMPLETE",ci_visibility:"COMPLETE",
    files:[{filename:V19.workflow,patch:"+remote_conflicting_fcu=UNKNOWN;concurrent_fcu=UNKNOWN"}],
    runs:[{id:V19.run,name:"BAL V19 Engine Crossfork Qualification (Fork Only)",
      head_sha:V19.sha,status:"completed",conclusion:"success"}]};
  const assessment=analyze(s),check=checkOutput(assessment);
  const api=async path=>path.includes("/artifacts")?{
    total_count:1,artifacts:[{id:V19.artifact,name:V19.artifactName,
      expired:false,digest:V19.zipDigest,
      workflow_run:{id:V19.run,head_sha:V19.sha}}]
  }:{id:V19.run,status:"completed",conclusion:"success",head_sha:V19.sha,
    repository:{full_name:V19.repository},path:V19.workflow,
    event:"push",run_attempt:1};
  const r=await appendGethV19NativeEvidence(assessment,check,api,"local-research-read-token");
  assert.equal(r.state,"WARRANTED_BOUNDED_HISTORICAL_NATIVE_ARTIFACT");
  assert.deepEqual(r.stillUnqualified,["remote_conflicting_fcu","concurrent_fcu"]);
  // Native source identity and named observations come from the existing
  // pinned adapter, never from the test frame being assessed.
  return {state:r.state,
    subject:{repository:V19.repository,pr:V19.pr,sha:V19.sha},
    observations:r.historicalTestObservations};
}

async function goccyNative(){
  const carrier="b".repeat(40);
  const manifest=read("external-native-evidence.v1.json");
  const reportText=read("one-finding-report.v1.json");
  const safeFile=(content,sha)=>({sha,encoding:"base64",
    content:Buffer.from(content).toString("base64")});
  const report={authority:"ADVISORY_ONLY",source:{
    repository:EVIDENCE.carrier,pr:21,sha:carrier}};
  const check={name:"MathGraph Check / evidence scope",status:"completed",
    conclusion:"neutral",output:{title:"SCOPE_UNKNOWN",summary:"Source-bound carrier"}};
  const snap={...snapshot(JSON.parse(goccyFrame)),
    number:21,repository:EVIDENCE.carrier,sha:carrier,
    files_visibility:"COMPLETE",files:EVIDENCE.carrierFiles.map(filename=>({filename}))};
  const api=async path=>{
    assert.equal(path,"/repos/"+EVIDENCE.carrier+"/contents/"+
      EVIDENCE.manifest+"?ref="+carrier);
    return safeFile(manifest,EVIDENCE.manifestBlob);
  };
  const fetcher=async url=>{
    const parsed=new URL(url),path=parsed.pathname;
    if(path.includes("/contents/"))
      return new Response(JSON.stringify(safeFile(reportText,EVIDENCE.reportBlob)),{status:200});
    const id=Number(path.match(/actions\/runs\/(\d+)/)?.[1]);
    const p=EVIDENCE.runs.find(x=>x.id===id);
    assert.ok(p);
    if(path.endsWith("/artifacts")) return new Response(JSON.stringify({
      total_count:1,artifacts:[{id:p.artifact,name:p.name,digest:p.digest,
        expired:false,workflow_run:{id:p.id,head_sha:p.head}}]
    }),{status:200});
    return new Response(JSON.stringify({id:p.id,status:"completed",
      conclusion:"success",head_sha:p.head,repository:{full_name:EVIDENCE.reporter},
      path:p.path,event:"push",run_attempt:1}),{status:200});
  };
  const r=await appendExternalNativeReceipt(report,check,api,
    "local-research-read-token",snap,{fetcher});
  assert.equal(r.state,"WARRANTED_BOUNDED_EXTERNAL_NATIVE_METADATA_RECHECKED");
  assert.equal(r.subject,EVIDENCE.subjectRepo);
  assert.equal(r.sourceSha,EVIDENCE.subjectHead);
  // Research-only typed projection of the previously reviewed, byte-pinned
  // report's bounded 69/0/20 facts. This is not a native test rerun or policy.
  return {state:r.state,
    subject:{repository:EVIDENCE.subjectRepo,pr:EVIDENCE.subjectPR,
      sha:EVIDENCE.subjectHead},
    observations:[
      {name:"author_pr_repairs",scope:"pr958-declared-matrix",
        source:"goccy-native-130-case-matrix",status:"WARRANTED_TRUE"},
      {name:"no_introduced_regressions",scope:"pr958-declared-matrix",
        source:"goccy-native-130-case-matrix",status:"WARRANTED_TRUE"},
      {name:"inherited_issue872_fixed",scope:"pr958-declared-matrix",
        source:"goccy-pr958-inherited-20",status:"WARRANTED_FALSE"}
    ]};
}
function replaySynthetic(frameBytes,nativeReceipt,ownerOverride={},frozenPin=sha256(frameBytes)){
  const f=JSON.parse(frameBytes),verifiedOwner=signed(f,ownerOverride);
  return replayFrameCase({snapshot:snapshot(f),verifiedOwner,
    frameBytes,frameSha256:frozenPin,nativeReceipt,asOf:200});
}
function replay(frameBytes,nativeReceipt,ownerOverride={}){
  const repository=JSON.parse(frameBytes).subject.repository;
  const pin=FRAME_PINS[repository];
  assert.equal(sha256(frameBytes),pin,"FROZEN_FRAME_PIN_CHANGED");
  return replaySynthetic(frameBytes,nativeReceipt,ownerOverride,pin);
}

test("exact source obligation frames match independently frozen digests",()=>{
  assert.equal(sha256(goethFrame),FRAME_PINS["metalogiclabs/go-ethereum"]);
  assert.equal(sha256(goccyFrame),FRAME_PINS["goccy/go-yaml"]);
});

test("same framed evaluator refuses GOETH semantic packet lie but conservatively admits finite goccy report",async()=>{
  const geth=replay(goethFrame,await gethNative());
  const goccy=replay(goccyFrame,await goccyNative());
  assert.equal(geth.framed.decision,"ABSTAIN");
  assert.equal(geth.packetOnly.decision,"ADMIT");
  assert.deepEqual(geth.framed.missing_observations,
    ["remote_conflicting_fcu","concurrent_fcu"]);
  assert.equal(goccy.framed.decision,"ADMIT");
  assert.equal(goccy.packetOnly.decision,"ADMIT");
  assert.equal(geth.framed.boundary,goccy.framed.boundary);
});

test("trusted native evidence cannot transfer across independently pinned source subjects",async()=>{
  const goccyNativeReceipt=await goccyNative();
  assert.equal(replay(goethFrame,goccyNativeReceipt).framed.decision,"ABSTAIN");
  const gethNativeReceipt=await gethNative();
  assert.equal(replay(goccyFrame,gethNativeReceipt).framed.decision,"ABSTAIN");
});

test("altered source frame and snapshot cannot launder the original native receipt",async()=>{
  const frame=JSON.parse(goethFrame);
  frame.subject.sha="c".repeat(40);
  frame.native_profile.subject.sha="c".repeat(40);
  const modified=JSON.stringify(frame),nativeReceipt=await gethNative();
  assert.throws(()=>replay(modified,nativeReceipt),/FROZEN_FRAME_PIN_CHANGED/);
  assert.equal(replaySynthetic(modified,nativeReceipt).framed.decision,"ABSTAIN");
});

test("native observation source labels are independent and cannot be relabeled by the frame",async()=>{
  const receipt=await gethNative();
  receipt.observations=[{...receipt.observations[0],source:"forged-observation"}];
  const result=replay(goethFrame,receipt);
  assert.equal(result.framed.decision,"ABSTAIN");
  assert.ok(result.framed.missing_observations.includes("predicate"));
});

test("source-support withdrawal removes derived goccy report admission",async()=>{
  const r=await goccyNative();
  assert.equal(replay(goccyFrame,r).framed.decision,"ADMIT");
  assert.equal(replay(goccyFrame,{...r,state:"UNKNOWN_DIGEST_CHANGED"}).framed.decision,"ABSTAIN");
  assert.equal(replay(goccyFrame,null).framed.decision,"ABSTAIN");
});

test("inherited 20-case unresolved repair is a separately framed negative, not PR-introduced regression",async()=>{
  const frame=JSON.parse(goccyFrame);
  frame.required.push({name:"inherited_issue872_fixed",
    source:"goccy-pr958-inherited-20",native_status:"WARRANTED_FALSE"});
  const r=replaySynthetic(JSON.stringify(frame),await goccyNative());
  assert.equal(r.framed.decision,"REFUSE");
  assert.ok(r.framed.residuals.some(x=>x.code==="FAIL_INHERITED_ISSUE872_FIXED"));
});

test("independently coded fixed-frame conventional comparator ties rather than proving superiority",async()=>{
  const records=[
    [goethFrame,await gethNative(),"ABSTAIN"],
    [goccyFrame,await goccyNative(),"ADMIT"],
    [goccyFrame,null,"ABSTAIN"]
  ];
  for(const [bytes,nativeReceipt,expected] of records){
    const result=replay(bytes,nativeReceipt);
    assert.equal(result.framed.decision,expected);
    assert.equal(conventionalReference({frame:JSON.parse(bytes),
      verifiedOwner:result.verifiedOwner,nativeReceipt,asOf:200}),expected);
  }
});

test("real native adapters feed both framed decisions into pinned Metatron causal memory",async t=>{
  const checkout=process.env.METATRON_SOURCE_CHECKOUT||resolve(root,"../../../metatron");
  if(!existsSync(join(checkout,"runtime/metatron/nucleus.py"))){
    assert.notEqual(process.env.METATRON_REQUIRED,"1",
      "CI_REQUIRED_PINNED_METATRON_CHECKOUT_MISSING");
    return t.skip("requires pinned Metatron checkout");
  }
  const goeth=replay(goethFrame,await gethNative());
  const goccy=replay(goccyFrame,await goccyNative());
  assert.deepEqual([goeth.framed.decision,goccy.framed.decision],
    ["ABSTAIN","ADMIT"]);
  const input={schema:"mathgraph.two-target-replay.v1",research_only:true,
    cases:[
      {id:"goeth_v19",decision:goeth.framed.decision,
        frame_sha256:FRAME_PINS["metalogiclabs/go-ethereum"],
        source:"metalogiclabs/go-ethereum#19@"+V19.sha},
      {id:"goccy_pr958",decision:goccy.framed.decision,
        frame_sha256:FRAME_PINS["goccy/go-yaml"],
        source:EVIDENCE.subjectRepo+"#"+EVIDENCE.subjectPR+"@"+EVIDENCE.subjectHead}
    ]};
  const result=spawnSync("python3",[
    join(root,"consequential-metatron-replay.py"),"--checkout",checkout],{
      input:JSON.stringify(input),encoding:"utf8",timeout:20000});
  assert.equal(result.status,0,result.stderr);
  const parsed=JSON.parse(result.stdout);
  assert.deepEqual(parsed.after_goeth_source_withdrawal,[
    "goccy_pr958_source","goccy_pr958_receipt","goccy_pr958_decision"]);
  assert.deepEqual(parsed.after_cold_restart,["goccy_pr958_source"]);
  assert.equal(parsed.no_external_authorization,true);
});
