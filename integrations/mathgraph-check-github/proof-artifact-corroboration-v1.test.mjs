import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash,generateKeyPairSync,sign} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {chmodSync,existsSync,mkdtempSync,mkdirSync,readFileSync,rmSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {corroborateLeanProofArtifact} from './proof-artifact-corroboration-v1.mjs';
import {admitCorroboratedSignedProjectionReview,projectionReviewBytes} from './signed-projection-review-v1.mjs';
import {githubSnapshot} from './authenticated-cycle-v1.mjs';
import {qualifyProtectedReview} from './protected-review-runner-v1.mjs';

const commit='b882e5b298b30b094f4154da7108a45e196cfcd3';
const theorem='MathGraph.WholeSource.CapstoneCommentBoundary.no_normative_iff_on_frozen_runtime';
const leanCommit='eb6cafb7290e8bd5f2937522d8d804f58f02bafc';
const axiomLine=`QUALIFIED_AXIOMS ${theorem}: [propext,\n Classical.choice,\n Quot.sound]`;
const proofType=`${theorem} (Language : String → Prop)\n  (hchar : ∀ (s : String), Language s → MathGraph.WholeSource.CapstoneCommentBoundary.NoRawSOH s) :\n  ¬∀ (s : String), MathGraph.WholeSource.CapstoneObstructions.Accepted s ↔ Language s`;

function fixture(overrides={}){
 const root=mkdtempSync(join(tmpdir(),'mathgraph-proof-artifact-test-'));
 try{
  const add=(path,content)=>{
   const full=join(root,path);mkdirSync(join(full,'..'),{recursive:true});writeFileSync(full,content);
  };
  const files={
   'directive-evidence/capstone/head.txt':`${commit}\n`,
   'directive-evidence/capstone/lean-version.txt':`Lean (version 4.35.0, x86_64, commit ${leanCommit}, Release)\n`,
   'directive-evidence/capstone/status.tsv':'CapstoneCommentBoundary\t0\nCapstoneQualification\t0\nDirectiveRed-expected-failure\t1\n',
   'directive-evidence/capstone/CapstoneQualification.log':`${proofType}\n${axiomLine}\n`,
   'directive-evidence/capstone/CapstoneCommentBoundary.log':`'${theorem}' depends on axioms: [propext,\n Classical.choice,\n Quot.sound]\n`,
   'research/whole-source/CapstoneCommentBoundary.lean':`def commentInput : String := "#\\x01"\ndef NoRawSOH (input : String) : Prop := True\n#guard (TokenParser.parseYaml commentInput).isOk\nlemma no_normative_iff_on_frozen_runtime (Language : String → Prop)\n    (hchar : ∀ s, Language s → NoRawSOH s) :\n    ¬ (∀ s, Accepted s ↔ Language s) := by\n  intro h\n  exact comment_violates_character_requirement\n#print axioms ${theorem}\n`,
   ...overrides,
  };
  Object.entries(files).forEach(([path,content])=>add(path,content));
  const archive=join(root,'proof.zip');
  execFileSync('zip',['-q','-r',archive,'directive-evidence','research'],{cwd:root,timeout:5000});
  const digest=createHash('sha256').update(readFileSync(archive)).digest('hex');
  const policy={repository:'metalogiclabs/L4YAML',commit,run:42420433923,
   job:128547467405,theorem,artifact_sha256:digest,lean_build_commit:leanCommit,
   expected_theorem_type:proofType};
  return {root,archive,policy};
 }catch(err){rmSync(root,{recursive:true,force:true});throw err;}
}
function withFixture(fn,overrides){const f=fixture(overrides);try{return fn(f);}finally{rmSync(f.root,{recursive:true,force:true});}}
async function withFixtureAsync(fn,overrides){const f=fixture(overrides);try{return await fn(f);}finally{rmSync(f.root,{recursive:true,force:true});}}

test('corroborates exact proof bytes and conservative historical boundary',()=>withFixture(({archive,policy})=>{
 const r=corroborateLeanProofArtifact(archive,policy);
 assert.equal(r.status,'CORROBORATED');
 assert.equal(r.theorem,theorem);
 assert.equal(r.receipt_ref,'metalogiclabs/L4YAML@'+commit+':run-42420433923:job-128547467405:'+theorem);
 assert.equal(r.proof_replay,'NOT_PERFORMED');
 assert.equal(r.complete_yaml_grammar,'UNKNOWN');
}));
test('artifact-byte inspection never executes an attacker-supplied unzip from PATH',()=>withFixture(({root,archive,policy})=>{
 const bin=join(root,'fake-bin'),marker=join(root,'malicious-unzip-ran');
 mkdirSync(bin);const executable=join(bin,'unzip');
 writeFileSync(executable,`#!/bin/sh\nprintf 'injected' > '${marker}'\nexit 99\n`);
 chmodSync(executable,0o755);
 const previous=process.env.PATH;
 try{
  process.env.PATH=bin+':'+previous;
  const result=corroborateLeanProofArtifact(archive,policy);
  assert.equal(result.status,'CORROBORATED');
  assert.equal(existsSync(marker),false);
 }finally{process.env.PATH=previous;}
}));
test('missing or untrusted receipt and digest mismatch fail closed',()=>withFixture(({archive,policy})=>{
 for(const p of [null,{...policy,artifact_sha256:'a'.repeat(64)},
   {...policy,expected_theorem_type:'True'},
   {...policy,commit:'a'.repeat(40)},
   {...policy,additional_source:'untrusted'}]){
  assert.equal(corroborateLeanProofArtifact(archive,p).status,'UNKNOWN');
 }
 assert.equal(corroborateLeanProofArtifact('/no/such/receipt.zip',policy).status,'UNKNOWN');
}));
test('changed reported theorem, unexpected axioms and failed qualification fail closed',()=>{
 for(const overrides of [
  {'directive-evidence/capstone/CapstoneQualification.log':`${proofType}\nQUALIFIED_AXIOMS ${theorem}: [sorryAx]`},
  {'directive-evidence/capstone/CapstoneQualification.log':`${proofType}\n${axiomLine}\nQUALIFIED_AXIOMS ${theorem}: [sorryAx]`},
  {'directive-evidence/capstone/CapstoneQualification.log':`False\n${axiomLine}`},
  {'directive-evidence/capstone/status.tsv':'CapstoneCommentBoundary\t1\nCapstoneQualification\t0\nDirectiveRed-expected-failure\t1'},
  {'directive-evidence/capstone/status.tsv':'CapstoneCommentBoundary\t0\nCapstoneCommentBoundary\t1\nCapstoneQualification\t0\nDirectiveRed-expected-failure\t1'},
  {'research/whole-source/CapstoneCommentBoundary.lean':'lemma irrelevant : True := by trivial'},
 ])withFixture(({archive,policy})=>assert.equal(
   corroborateLeanProofArtifact(archive,policy).status,'UNKNOWN'),overrides);
});
test('signed review requires matching reviewed receipt and independently pinned artifact bytes',()=>withFixture(({archive,policy})=>{
 const key=generateKeyPairSync('ed25519');
 const keys={'trusted-reviewer':key.publicKey.export({format:'pem',type:'spki'})};
 const subject={repository:'metalogiclabs/L4YAML',pr:9,base_sha:'a'.repeat(40),head_sha:'b'.repeat(40)};
 const receipt_ref=`${policy.repository}@${policy.commit}:run-${policy.run}:job-${policy.job}:${policy.theorem}`;
 const payload={schema:'mathgraph.projection.review.v1',subject,
  claim:{id:'NoRawSOH',statement:'A public parser success bit cannot decide NoRawSOH',
   observation:'TokenParser.parseYaml success',
   universe:{schema:'mathgraph.finite-warrant-quotient.v1',scope:'reviewed-finite-pair',rows:[
    {id:'legal',source_sha:subject.head_sha,alpha_key:'success',protected_status:'OBSERVED'},
    {id:'raw-soh',source_sha:subject.head_sha,alpha_key:'success',protected_status:'BLOCKED'}]}},
  evidence:{receipt_ref,artifact_sha256:policy.artifact_sha256}};
 const signed=x=>{const packet={key_id:'trusted-reviewer',payload:x};return {...packet,
  signature_b64:sign(null,projectionReviewBytes(packet),key.privateKey).toString('base64')};};
 const envelope=signed(payload);
 const good=admitCorroboratedSignedProjectionReview(subject,envelope,keys,{archivePath:archive,trustedReceipt:policy});
 assert.equal(good.status,'BLOCKED');
 assert.equal(good.review.artifact_corroboration,'CORROBORATED');
 assert.equal(good.review.proof_replay,'NOT_PERFORMED');
 for(const options of [
   {archivePath:'/no/such/zip',trustedReceipt:policy},
   {archivePath:archive,trustedReceipt:{...policy,artifact_sha256:'0'.repeat(64)}},
   {archivePath:archive,trustedReceipt:{...policy,run:policy.run+1}},
   {archivePath:archive},
 ])assert.equal(admitCorroboratedSignedProjectionReview(subject,envelope,keys,options).status,'UNKNOWN');
 const forged=signed({...payload,evidence:{...payload.evidence,receipt_ref:'other'}});
 assert.equal(admitCorroboratedSignedProjectionReview(subject,forged,keys,{archivePath:archive,trustedReceipt:policy}).status,'UNKNOWN');
}));
test('authenticated GitHub readback carries artifact corroboration but no universal proof',()=>withFixtureAsync(async({archive,policy})=>{
 const subject={repository:'metalogiclabs/L4YAML',pr:9,base_sha:'a'.repeat(40),head_sha:'b'.repeat(40)};
 const keys=generateKeyPairSync('ed25519');
 const reviewer={'trusted-reviewer':keys.publicKey.export({format:'pem',type:'spki'})};
 const evidence={receipt_ref:`${policy.repository}@${policy.commit}:run-${policy.run}:job-${policy.job}:${policy.theorem}`,
  artifact_sha256:policy.artifact_sha256};
 const claim={id:'NoRawSOH',statement:'A parser success bit cannot decide NoRawSOH',
  observation:'TokenParser.parseYaml success',
  universe:{schema:'mathgraph.finite-warrant-quotient.v1',scope:'reviewed-finite-pair',rows:[
   {id:'legal',source_sha:subject.head_sha,alpha_key:'success',protected_status:'OBSERVED'},
   {id:'raw-soh',source_sha:subject.head_sha,alpha_key:'success',protected_status:'BLOCKED'}]}};
 const packet={key_id:'trusted-reviewer',payload:{schema:'mathgraph.projection.review.v1',subject,claim,evidence}};
 const envelope={...packet,signature_b64:sign(null,projectionReviewBytes(packet),keys.privateKey).toString('base64')};
 const fetcher=async url=>({ok:true,json:async()=>url.includes('/pulls/')?
  {base:{sha:subject.base_sha,repo:{full_name:subject.repository}},
   head:{sha:subject.head_sha,repo:{full_name:subject.repository}}}:
  {total_count:1,check_runs:[{id:42,name:'Native',head_sha:subject.head_sha,
   status:'completed',conclusion:'success',started_at:'2026-11-08T00:00:00Z',app:{slug:'github-actions'}}]}});
 const result=await githubSnapshot({...subject,token:'fake-read-only-token',fetcher,
  signedProjectionReview:envelope,trustedReviewerKeys:reviewer,
  proofArtifactPath:archive,trustedProofReceipt:policy});
 assert.equal(result.projection.status,'BLOCKED');
 assert.equal(result.projection.review.artifact_corroboration,'CORROBORATED');
 assert.equal(result.projection.review.proof_replay,'NOT_PERFORMED');
 assert.equal(result.result.status,'BLOCKED');
 assert.equal(result.result.permission,'ADVISORY_ONLY');
}),);

test('protected operator checks GitHub job and ZIP bytes, then rechecks current head',()=>withFixtureAsync(async({archive,policy})=>{
 const subject={repository:'metalogiclabs/L4YAML',pr:9,base_sha:'a'.repeat(40),head_sha:'b'.repeat(40)};
 const key=generateKeyPairSync('ed25519');
 const reviewer={'approved-reviewer':key.publicKey.export({format:'pem',type:'spki'})};
 const receipt_ref=`${policy.repository}@${policy.commit}:run-${policy.run}:job-${policy.job}:${policy.theorem}`;
 const claim={id:'NoRawSOH',statement:'The parser success bit cannot decide NoRawSOH',
  observation:'parseYaml success',universe:{schema:'mathgraph.finite-warrant-quotient.v1',
   scope:'the-two-source-witnesses',rows:[
    {id:'valid',source_sha:subject.head_sha,alpha_key:'ok',protected_status:'OBSERVED'},
    {id:'invalid',source_sha:subject.head_sha,alpha_key:'ok',protected_status:'BLOCKED'}]}};
 const packet={key_id:'approved-reviewer',payload:{schema:'mathgraph.projection.review.v1',
  subject,claim,evidence:{receipt_ref,artifact_sha256:policy.artifact_sha256}}};
 const signedReview={...packet,signature_b64:sign(null,projectionReviewBytes(packet),key.privateKey).toString('base64')};
 const context={event_name:'workflow_dispatch',ref:'refs/heads/main',default_branch:'main',
  repository:subject.repository,pr:subject.pr,token:'readback-token',evidence_token:'evidence-token'};
 const base='https://api.github.com/repos/metalogiclabs/L4YAML';
 const makeFetcher=({changeHead=false,badDigest=false,badJob=false}={})=>{
  let pulls=0;const reads=[];
  const fetcher=async(url,init)=>{
   reads.push({url,auth:init?.headers?.Authorization});
   if(url===base+'/pulls/9'){
    const head=changeHead&&++pulls===2?'d'.repeat(40):subject.head_sha;
    return {ok:true,json:async()=>({base:{sha:subject.base_sha,repo:{full_name:subject.repository}},
     head:{sha:head,repo:{full_name:subject.repository}}})};
   }
   if(url.includes('/check-runs?'))return {ok:true,json:async()=>({total_count:0,check_runs:[]})};
   if(url===base+'/actions/artifacts/100')return {ok:true,json:async()=>({
    id:100,expired:false,digest:'sha256:'+(badDigest?'f'.repeat(64):policy.artifact_sha256),
    workflow_run:{id:policy.run,head_sha:policy.commit,repository_id:55,head_repository_id:55}})};
   if(url===base+'/actions/runs/'+policy.run+'/jobs?per_page=100')return {ok:true,json:async()=>({
    total_count:1,jobs:[{id:policy.job,name:'directive-proofs',run_id:policy.run,
     status:'completed',conclusion:badJob?'failure':'success',steps:[
      {name:'Qualify persistent capstone boundary and retained positive repair',conclusion:badJob?'failure':'success'}]}]})};
   throw Error('UNEXPECTED_API:'+url);
  };return {fetcher,reads};
 };
 const input={context,signedProjectionReview:signedReview,trustedReviewerKeys:reviewer,
  trustedProofReceipt:policy,artifactPath:archive,artifactId:100};
 const good=makeFetcher();
 const ok=await qualifyProtectedReview({...input,fetcher:good.fetcher});
 assert.equal(ok.status,'BLOCKED');
 assert.equal(ok.terminal_form,'NAMED_OBSTRUCTION');
 assert.equal(ok.artifact_corroboration,'CORROBORATED');
 assert.equal(ok.proof_replay,'NOT_PERFORMED');
 assert.equal(good.reads.filter(x=>x.url===base+'/pulls/9').length,2);
 assert.ok(good.reads.some(x=>x.url===base+'/actions/artifacts/100'&&x.auth==='Bearer evidence-token'));
 for(const variant of [{changeHead:true},{badDigest:true},{badJob:true}]){
  const x=makeFetcher(variant);
  assert.equal((await qualifyProtectedReview({...input,fetcher:x.fetcher})).status,'UNKNOWN');
 }
 const unauthorized=makeFetcher();
 assert.equal((await qualifyProtectedReview({...input,
  context:{...context,ref:'refs/pull/9/merge'},fetcher:unauthorized.fetcher})).status,'UNKNOWN');
 assert.equal(unauthorized.reads.length,0);
 const unreviewed=makeFetcher();
 assert.equal((await qualifyProtectedReview({...input,trustedReviewerKeys:{},
  fetcher:unreviewed.fetcher})).status,'UNKNOWN');
}));
