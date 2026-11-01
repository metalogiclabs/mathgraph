import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {join} from 'node:path';
import {ARTIN_PIN} from './proofnet-artin-replay-v1.mjs';
import {
  verifyPinnedArtinArtifactBytes,verifyPinnedArtinUpstreamBytes,
} from './math-source-evidence-bytes-v1.mjs';

const sha=b=>createHash('sha256').update(b).digest('hex');
const hex=x=>Buffer.from(x,'utf8');
const h32=x=>{let c=0xffffffff;for(const b of x){c^=b;for(let i=0;i<8;i++)
  c=(c>>>1)^((c&1)?0xedb88320:0);}return(c^0xffffffff)>>>0;};

// Minimal, actual, in-memory ZIP (not a mocked ZIP decoder).
function zip(entries){
  const locals=[],centrals=[];
  let offset=0;
  for(const {name,bytes,declaredSize,externalAttr=0,madeBy=20} of entries){
    const n=hex(name),data=Buffer.isBuffer(bytes)?bytes:hex(bytes);
    const crc=h32(data);
    const l=Buffer.alloc(30);
    l.writeUInt32LE(0x04034b50,0);l.writeUInt16LE(20,4);
    l.writeUInt32LE(crc,14);l.writeUInt32LE(data.length,18);
    l.writeUInt32LE(declaredSize??data.length,22);l.writeUInt16LE(n.length,26);
    locals.push(l,n,data);
    const c=Buffer.alloc(46);
    c.writeUInt32LE(0x02014b50,0);c.writeUInt16LE(madeBy,4);
    c.writeUInt16LE(20,6);c.writeUInt32LE(crc,16);
    c.writeUInt32LE(data.length,20);c.writeUInt32LE(declaredSize??data.length,24);
    c.writeUInt16LE(n.length,28);c.writeUInt32LE(externalAttr,38);
    c.writeUInt32LE(offset,42);
    centrals.push(c,n);
    offset+=l.length+n.length+data.length;
  }
  const directory=Buffer.concat(centrals);
  const end=Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50,0);
  end.writeUInt16LE(entries.length,8);end.writeUInt16LE(entries.length,10);
  end.writeUInt32LE(directory.length,12);end.writeUInt32LE(offset,16);
  return Buffer.concat([...locals,directory,end]);
}

const preflight={
  schema:'mathgraph.proofnet-artin-preflight.v1',
  upstream:{repository:ARTIN_PIN.repository,commit:ARTIN_PIN.commit},
  theorem:ARTIN_PIN.theorem,
  source_sha256:ARTIN_PIN.sourceSha256,
  claim_sha256:'a908ad4a14106793dec67703b4051fd3587be202fcd94c5778981cab409051a0',
  statement_sha256:ARTIN_PIN.formalSha256,
  gold_archive_sha256:ARTIN_PIN.zipSha256,
  gold_proof_sha256:ARTIN_PIN.goldSha256,
  requested_lean:ARTIN_PIN.targetLean,requested_mathlib:ARTIN_PIN.targetMathlib,
  artifact_preflight:'PINNED_GOLD_PROOF_IDENTIFIED',native_lean_replay:'NOT_RUN',
  qualified_human_review:'UNKNOWN',intent_verification:'NOT_ESTABLISHED',
  permission:'ADVISORY_ONLY',
};
const audit={
  schema:'mathgraph.artin-axiom-audit.v1',theorem:ARTIN_PIN.theorem,
  allowed_axioms:['propext','Classical.choice','Quot.sound'],
  observed_axioms:['propext','Classical.choice','Quot.sound'],
  verdict:'AXIOMS_WITHIN_CLASSICAL_LEAN_ALLOWLIST',source_review:'UNKNOWN',
  intent_verification:'NOT_ESTABLISHED',permission:'ADVISORY_ONLY',
};
const files=(p=preflight,a=audit)=>[
  {name:'artin-preflight.json',bytes:JSON.stringify(p)},
  {name:'artin-axiom-audit.json',bytes:JSON.stringify(a)},
];
const verify=bytes=>verifyPinnedArtinArtifactBytes({zipBytes:bytes,artifactDigest:'sha256:'+sha(bytes)});

test('real ZIP parser pins exact compressed artifact bytes and two audit JSONs',()=>{
  const bytes=zip(files());
  const value=verify(bytes);
  assert.equal(value.status,'ARTIFACT_BYTES_PINNED');
  assert.equal(value.archive_sha256,sha(bytes));
  assert.equal(value.native_replay,'WORKFLOW_SUCCESS_STILL_REQUIRED');
  assert.equal(value.source_review,'UNKNOWN');
  assert.equal(value.receipt_qualification,'NOT_YET_CONTRACT_BOUND');
  assert.equal(value.intent_verification,'NOT_ESTABLISHED');
  assert.equal(value.permission,'ADVISORY_ONLY');
});

test('artifact digest must be independently supplied and byte-exact',()=>{
  const original=zip(files());
  assert.throws(()=>verifyPinnedArtinArtifactBytes({zipBytes:original}),/INVALID_INDEPENDENT_ARTIFACT_DIGEST/);
  const tampered=Buffer.from(original);
  tampered[tampered.length-30]^=1;
  assert.throws(()=>verifyPinnedArtinArtifactBytes({zipBytes:tampered,
    artifactDigest:'sha256:'+sha(original)}),/ARTIFACT_DIGEST_MISMATCH/);
});

test('missing, duplicated, unexpected and path-traversing files all fail closed',()=>{
  for(const entries of [
    files().slice(0,1),[...files(),files()[0]],
    [...files(),{name:'unexpected.json',bytes:'{}'}],
    [{name:'../artin-preflight.json',bytes:JSON.stringify(preflight)},files()[1]],
    [{...files()[0],externalAttr:0xa0000000,madeBy:(3<<8)|20},files()[1]],
  ])assert.throws(()=>verify(zip(entries)),/ARTIFACT_ZIP_/);
});

test('declared zip bombs and malformed/truncated ZIP files are rejected',()=>{
  assert.throws(()=>verify(zip([{...files()[0],declaredSize:40*1024*1024},files()[1]])),/ARTIFACT_ZIP_/);
  assert.throws(()=>verify(Buffer.from('not a zip')),/ARTIFACT_ZIP_/);
  assert.throws(()=>verify(Buffer.concat([zip(files()),Buffer.from('garbage')])),/ARTIFACT_ZIP_/);
});

test('tampered source, claim, statement and gold digests in preflight fail',()=>{
  for(const key of ['source_sha256','claim_sha256','statement_sha256',
    'gold_archive_sha256','gold_proof_sha256']){
    const p={...preflight,[key]:'0'.repeat(64)};
    assert.throws(()=>verify(zip(files(p))),/ARTIFACT_PREFLIGHT_MISMATCH/);
  }
});

test('machine report cannot impersonate completed replay or human review',()=>{
  for(const p of [
    {...preflight,native_lean_replay:'PASSED'},
    {...preflight,qualified_human_review:'APPROVED'},
    {...preflight,permission:'AUTO_APPROVE'},
    {...preflight,replay_verified:true},
  ])assert.throws(()=>verify(zip(files(p))),/ARTIFACT_PREFLIGHT_MISMATCH/);
  for(const a of [
    {...audit,source_review:'REVIEWED'},
    {...audit,observed_axioms:[...audit.observed_axioms,'sorryAx']},
    {...audit,verdict:'VERIFIED'},
    {...audit,auto_approved:true},
  ])assert.throws(()=>verify(zip(files(preflight,a))),/ARTIFACT_AXIOM_AUDIT_MISMATCH/);
});

test('upstream source requires exact independently authenticated git commit',()=>{
  assert.throws(()=>verifyPinnedArtinUpstreamBytes({observedCommit:'0'.repeat(40),
    sourceBytes:hex('a'),jsonlBytes:hex('{}')}),/UNPINNED_UPSTREAM_COMMIT/);
  assert.throws(()=>verifyPinnedArtinUpstreamBytes({observedCommit:ARTIN_PIN.commit,
    sourceBytes:hex('a'),jsonlBytes:hex('{}')}),/UPSTREAM_SOURCE_BYTES_CHANGED/);
});

test('actual pinned upstream source and JSONL are checked if fixture is present',t=>{
  const dir=process.env.MATHGRAPH_PROOFNET_FIXTURE_DIR;
  if(!dir){t.skip('Pinned upstream fixture supplied in replay CI only');return;}
  const sourceBytes=readFileSync(join(dir,ARTIN_PIN.sourcePath));
  const jsonlBytes=readFileSync(join(dir,ARTIN_PIN.jsonlPath));
  const result=verifyPinnedArtinUpstreamBytes({observedCommit:ARTIN_PIN.commit,
    sourceBytes,jsonlBytes});
  assert.equal(result.status,'UPSTREAM_SOURCE_BYTES_PINNED');
  assert.equal(result.claim_sha256,preflight.claim_sha256);
  assert.equal(result.statement_sha256,ARTIN_PIN.formalSha256);
  assert.equal(result.permission,'ADVISORY_ONLY');
  const corrupted=Buffer.from(jsonlBytes);
  const pos=corrupted.indexOf(Buffer.from('Artin_exercise_2_2_9'));
  assert.ok(pos>=0);
  corrupted[pos]^=1;
  assert.throws(()=>verifyPinnedArtinUpstreamBytes({observedCommit:ARTIN_PIN.commit,
    sourceBytes,jsonlBytes:corrupted}),/UPSTREAM_/);
});

test('published GitHub artifact ZIP matches the independent digest, when supplied',t=>{
  const path=process.env.MATHGRAPH_ARTIN_EVIDENCE_ZIP;
  if(!path){t.skip('Published ZIP is supplied out of band; it is not committed');return;}
  const bytes=readFileSync(path);
  const result=verifyPinnedArtinArtifactBytes({zipBytes:bytes,
    artifactDigest:'sha256:74a7838a82728a8326c15b1115992ac1519bf117d608ab497c92df3c07e2bd09'});
  assert.equal(result.status,'ARTIFACT_BYTES_PINNED');
  assert.equal(result.intent_verification,'NOT_ESTABLISHED');
});
