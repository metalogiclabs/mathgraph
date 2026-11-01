import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {makeArtinEnvironmentReport,verifyPinnedArtinEnvironmentArtifactBytes}
  from './math-source-environment-closure-v1.mjs';

const sha=x=>createHash('sha256').update(x).digest('hex');
const mathlibRev='8f9d9cff6bd728b17a24e163c9402775d9e6a365';
const manifest={version:'1.1.0',packagesDir:'.lake/packages',packages:[
  {name:'mathlib',type:'git',url:'https://github.com/leanprover-community/mathlib4.git',
    rev:mathlibRev,inputRev:'v4.28.0'},
  {name:'aesop',type:'git',url:'https://github.com/leanprover-community/aesop',
    rev:'a'.repeat(40),inputRev:'master'},
]};
const source={
  manifestBytes:Buffer.from(JSON.stringify(manifest)),
  toolchainBytes:Buffer.from('leanprover/lean4:v4.28.0\n'),
  leanVersionBytes:Buffer.from('Lean (version 4.28.0, x86_64-unknown-linux-gnu)\n'),
  lakeVersionBytes:Buffer.from('Lake version 5.0.0 (Lean version 4.28.0)\n'),
};

function crc32(bytes){let c=0xffffffff;for(const b of bytes){c^=b;
  for(let i=0;i<8;i++)c=(c>>>1)^((c&1)?0xedb88320:0);}return(c^0xffffffff)>>>0;}
function zip(files){
  const locals=[],centrals=[];let offset=0;
  for(const [name,b] of files){
    const n=Buffer.from(name),l=Buffer.alloc(30),c=Buffer.alloc(46);
    const crc=crc32(b);
    l.writeUInt32LE(0x04034b50,0);l.writeUInt16LE(20,4);l.writeUInt32LE(crc,14);
    l.writeUInt32LE(b.length,18);l.writeUInt32LE(b.length,22);l.writeUInt16LE(n.length,26);
    c.writeUInt32LE(0x02014b50,0);c.writeUInt16LE(20,4);c.writeUInt16LE(20,6);
    c.writeUInt32LE(crc,16);c.writeUInt32LE(b.length,20);
    c.writeUInt32LE(b.length,24);c.writeUInt16LE(n.length,28);c.writeUInt32LE(offset,42);
    locals.push(l,n,b);centrals.push(c,n);offset+=l.length+n.length+b.length;
  }
  const dir=Buffer.concat(centrals),end=Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50,0);end.writeUInt16LE(files.length,8);
  end.writeUInt16LE(files.length,10);end.writeUInt32LE(dir.length,12);
  end.writeUInt32LE(offset,16);
  return Buffer.concat([...locals,dir,end]);
}
const names={
  'lake-manifest.json':'manifestBytes',
  'artin-toolchain.txt':'toolchainBytes',
  'artin-lean-version.txt':'leanVersionBytes',
  'artin-lake-version.txt':'lakeVersionBytes',
};
function artifact(overrides={}){
  const x={...source,...overrides};
  const report=makeArtinEnvironmentReport(x);
  const entries=Object.entries(names).map(([name,key])=>[name,x[key]]);
  entries.push(['artin-environment.json',Buffer.from(JSON.stringify(report))]);
  return zip(entries);
}

test('a real ZIP of the resolved Lake manifest and reported versions pins all Git revisions',()=>{
  assert.equal(makeArtinEnvironmentReport(source).schema,
    'mathgraph.artin-resolved-environment.v1');
  const bytes=artifact();
  const a=verifyPinnedArtinEnvironmentArtifactBytes({zipBytes:bytes,
    artifactDigest:'sha256:'+sha(bytes)});
  assert.equal(a.status,'ENVIRONMENT_MANIFEST_BYTES_PINNED');
  assert.equal(a.manifest_sha256,sha(source.manifestBytes));
  assert.match(a.environment_sha256,/^[a-f0-9]{64}$/);
  assert.notEqual(a.environment_sha256,a.manifest_sha256);
  assert.equal(a.mathlib_revision,mathlibRev);
  assert.equal(a.resolved_dependency_count,2);
  assert.equal(a.native_replay,'WORKFLOW_SUCCESS_STILL_REQUIRED');
  assert.equal(a.permission,'ADVISORY_ONLY');
  assert.equal(a.receipt_qualification,'NOT_YET_CONTRACT_BOUND');
});

test('Mathlib must resolve the independently checked 4.28.0 tag to the pinned Git commit',()=>{
  for(const mutant of [
    {...manifest,packages:[{...manifest.packages[0],rev:'f'.repeat(40)},manifest.packages[1]]},
    {...manifest,packages:[{...manifest.packages[0],inputRev:'main'},manifest.packages[1]]},
    {...manifest,packages:[manifest.packages[0],{...manifest.packages[1],type:'path'}]},
    {...manifest,packages:[manifest.packages[0],{...manifest.packages[0]}]},
  ])assert.throws(()=>makeArtinEnvironmentReport({...source,
    manifestBytes:Buffer.from(JSON.stringify(mutant))}),/INVALID_RESOLVED_LAKE_MANIFEST/);
});

test('toolchain and observed Lean version must agree, not just requested names',()=>{
  for(const patch of [
    {toolchainBytes:Buffer.from('leanprover/lean4:v4.29.0\n')},
    {leanVersionBytes:Buffer.from('Lean (version 4.29.0, linux)')},
    {lakeVersionBytes:Buffer.from('unexpected')},
  ])assert.throws(()=>makeArtinEnvironmentReport({...source,...patch}),
    /INVALID_PINNED_LEAN_ENVIRONMENT/);
});

test('environment ZIP rejects wrong digest, missing, extra or altered report data',()=>{
  const bytes=artifact();
  assert.throws(()=>verifyPinnedArtinEnvironmentArtifactBytes({zipBytes:bytes,
    artifactDigest:'sha256:'+'f'.repeat(64)}),/ENVIRONMENT_ARTIFACT_DIGEST_MISMATCH/);
  const missing=zip(Object.entries(names).map(([name,key])=>[name,source[key]]));
  assert.throws(()=>verifyPinnedArtinEnvironmentArtifactBytes({zipBytes:missing,
    artifactDigest:'sha256:'+sha(missing)}),/ARTIFACT_ZIP_/);
  const altered=zip([...Object.entries(names).map(([name,key])=>[name,source[key]]),
    ['artin-environment.json',Buffer.from(JSON.stringify({
      ...makeArtinEnvironmentReport(source),native_lean_replay:'VERIFIED'}))]]);
  assert.throws(()=>verifyPinnedArtinEnvironmentArtifactBytes({zipBytes:altered,
    artifactDigest:'sha256:'+sha(altered)}),/ENVIRONMENT_REPORT_MISMATCH/);
});
