import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {makeArtinEnvironmentReport}
  from './math-source-environment-closure-v1.mjs';
import {correlatePinnedEnvironmentArtifact}
  from './math-source-environment-correlation-v1.mjs';

const sha=b=>createHash('sha256').update(b).digest('hex');
const head='a'.repeat(40),repository='metalogiclabs/mathgraph';
const manifest={version:'1.1.0',packagesDir:'.lake/packages',packages:[{
  type:'git',name:'mathlib',url:'https://github.com/leanprover-community/mathlib4.git',
  inputRev:'v4.28.0',rev:'8f9d9cff6bd728b17a24e163c9402775d9e6a365',
}]};
const source={manifestBytes:Buffer.from(JSON.stringify(manifest)),
  toolchainBytes:Buffer.from('leanprover/lean4:v4.28.0\n'),
  leanVersionBytes:Buffer.from('Lean (version 4.28.0, linux)\n'),
  lakeVersionBytes:Buffer.from('Lake version 5.0.0-src (Lean version 4.28.0)\n')};
const names={'lake-manifest.json':'manifestBytes','artin-toolchain.txt':'toolchainBytes',
  'artin-lean-version.txt':'leanVersionBytes','artin-lake-version.txt':'lakeVersionBytes'};
function crc32(x){let c=0xffffffff;for(const b of x){c^=b;for(let i=0;i<8;i++)
  c=(c>>>1)^((c&1)?0xedb88320:0);}return(c^0xffffffff)>>>0;}
function zip(files){
  const local=[],central=[];let offset=0;
  for(const [name,b] of files){
    const n=Buffer.from(name),l=Buffer.alloc(30),c=Buffer.alloc(46),crc=crc32(b);
    l.writeUInt32LE(0x04034b50,0);l.writeUInt16LE(20,4);
    l.writeUInt32LE(crc,14);l.writeUInt32LE(b.length,18);
    l.writeUInt32LE(b.length,22);l.writeUInt16LE(n.length,26);
    c.writeUInt32LE(0x02014b50,0);c.writeUInt16LE(20,4);c.writeUInt16LE(20,6);
    c.writeUInt32LE(crc,16);c.writeUInt32LE(b.length,20);
    c.writeUInt32LE(b.length,24);c.writeUInt16LE(n.length,28);c.writeUInt32LE(offset,42);
    local.push(l,n,b);central.push(c,n);offset+=l.length+n.length+b.length;
  }
  const d=Buffer.concat(central),end=Buffer.alloc(22);end.writeUInt32LE(0x06054b50,0);
  end.writeUInt16LE(files.length,8);end.writeUInt16LE(files.length,10);
  end.writeUInt32LE(d.length,12);end.writeUInt32LE(offset,16);
  return Buffer.concat([...local,d,end]);
}
function fixture(){
  const report=makeArtinEnvironmentReport(source);
  const entries=Object.entries(names).map(([name,key])=>[name,source[key]]);
  entries.push(['artin-environment.json',Buffer.from(JSON.stringify(report))]);
  const zipBytes=zip(entries);
  const primary={schema:'mathgraph.artin-evidence-collector.v1',
    status:'EVIDENCE_BYTES_CORRELATED',subject:{repository,pr:12,head_sha:head},
    replay:{status:'PINNED_REPLAY_OBSERVED',run_id:991,run_attempt:1,job_id:300,
      artifact_id:7000,artifact_digest:'sha256:'+'a'.repeat(64)},
    review:{status:'UNKNOWN'},permission:'ADVISORY_ONLY',
    intent_verification:'NOT_ESTABLISHED',conclusion:'neutral'};
  const environmentArtifact={id:7001,name:'mathgraph-proofnet-artin-environment',
    expired:false,size_in_bytes:zipBytes.length,digest:'sha256:'+sha(zipBytes),
    workflow_run:{id:991,head_sha:head,repository_id:55}};
  const trusted={headSha:head,environmentSha256:report.environment_sha256};
  return {primary,environmentArtifact,trusted,zipBytes};
}

test('same-run digest-pinned environment yields a neutral correlated observation',()=>{
  const f=fixture();const r=correlatePinnedEnvironmentArtifact(f);
  assert.equal(r.status,'ENVIRONMENT_AND_REPLAY_CORRELATED');
  assert.equal(r.environment.environment_sha256,f.trusted.environmentSha256);
  assert.equal(r.environment.resolved_dependency_count,1);
  assert.equal(r.replay.run_id,991);
  assert.equal(r.review.status,'UNKNOWN');
  assert.equal(r.intent_verification,'NOT_ESTABLISHED');
  assert.equal(r.permission,'ADVISORY_ONLY');
  assert.equal(r.receipt_qualification,'NOT_YET_CONTRACT_BOUND');
  assert.equal(r.conclusion,'neutral');
});

test('different run, head, stale artifact or wrong environment trust fails',()=>{
  for(const mutate of [
    f=>{f.environmentArtifact.workflow_run.id=992;},
    f=>{f.environmentArtifact.workflow_run.head_sha='b'.repeat(40);},
    f=>{f.environmentArtifact.expired=true;},
    f=>{f.environmentArtifact.id=f.primary.replay.artifact_id;},
    f=>{f.trusted.environmentSha256='f'.repeat(64);},
    f=>{f.environmentArtifact.digest='sha256:'+'f'.repeat(64);},
    f=>{f.primary.status='UNKNOWN';},
  ]){
    const f=fixture();mutate(f);
    const r=correlatePinnedEnvironmentArtifact(f);
    assert.equal(r.status,'UNKNOWN');
    assert.equal(r.permission,'ADVISORY_ONLY');
  }
});

test('corrupt environment bytes do not inherit original replay success',()=>{
  const f=fixture();f.zipBytes=Buffer.from(f.zipBytes);
  f.zipBytes[40]^=1;
  const r=correlatePinnedEnvironmentArtifact(f);
  assert.equal(r.status,'UNKNOWN');
  assert.equal(r.intent_verification,'NOT_ESTABLISHED');
});
