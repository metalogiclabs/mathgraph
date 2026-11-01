import test from 'node:test';
import assert from 'node:assert/strict';
import {copyFileSync,mkdirSync,mkdtempSync,readFileSync,rmSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {dirname,join} from 'node:path';
import {ARTIN_PIN,preflightArtinFixture} from './proofnet-artin-replay-v1.mjs';

test('the upstream commit must be independently observed, not inferred from fixture text',()=>{
  assert.throws(()=>preflightArtinFixture('/untrusted',{observedCommit:null}),/UNPINNED_UPSTREAM_COMMIT/);
  assert.throws(()=>preflightArtinFixture('/untrusted',{observedCommit:'0'.repeat(40)}),/UNPINNED_UPSTREAM_COMMIT/);
});

test('the exact third-party Artin gold artifact is identified, not misreported as replayed',t=>{
  const original=process.env.MATHGRAPH_PROOFNET_FIXTURE_DIR;
  if(!original){t.skip('External upstream fixture is optional for the normal JS suite');return;}
  const actual=preflightArtinFixture(original,{observedCommit:ARTIN_PIN.commit});
  assert.equal(actual.source_sha256,ARTIN_PIN.sourceSha256);
  assert.equal(actual.statement_sha256,ARTIN_PIN.formalSha256);
  assert.equal(actual.gold_archive_sha256,ARTIN_PIN.zipSha256);
  assert.equal(actual.gold_proof_sha256,ARTIN_PIN.goldSha256);
  assert.equal(actual.native_lean_replay,'NOT_RUN');
  assert.equal(actual.qualified_human_review,'UNKNOWN');
  assert.equal(actual.intent_verification,'NOT_ESTABLISHED');
  assert.equal(actual.permission,'ADVISORY_ONLY');
  assert.doesNotMatch(JSON.stringify(actual),/closure_induction₂|Lean proof completed/i);

  const temp=mkdtempSync(join(tmpdir(),'mathgraph-artin-pin-'));
  t.after(()=>rmSync(temp,{recursive:true,force:true}));
  for(const path of [ARTIN_PIN.sourcePath,ARTIN_PIN.zipPath,ARTIN_PIN.jsonlPath]){
    const dest=join(temp,path);
    mkdirSync(dirname(dest),{recursive:true});
    copyFileSync(join(original,path),dest);
  }

  const sourcePath=join(temp,ARTIN_PIN.sourcePath);
  const originalSource=readFileSync(sourcePath);
  writeFileSync(sourcePath,Buffer.concat([originalSource,Buffer.from('\n-- mutation\n')]));
  assert.throws(()=>preflightArtinFixture(temp,{observedCommit:ARTIN_PIN.commit}),/SOURCE_BYTES_CHANGED/);
  writeFileSync(sourcePath,originalSource);

  const zipPath=join(temp,ARTIN_PIN.zipPath);
  const originalZip=readFileSync(zipPath);
  writeFileSync(zipPath,Buffer.concat([originalZip,Buffer.from('mutation')]));
  assert.throws(()=>preflightArtinFixture(temp,{observedCommit:ARTIN_PIN.commit}),/GOLD_ARCHIVE_CHANGED/);
  writeFileSync(zipPath,originalZip);

  const jsonlPath=join(temp,ARTIN_PIN.jsonlPath);
  const originalJsonl=readFileSync(jsonlPath,'utf8');
  const entries=originalJsonl.split('\n');
  const first=JSON.parse(entries[0]);
  first.formal_stmt=first.formal_stmt.replace('x * y = y * x','x = x');
  entries[0]=JSON.stringify(first);
  writeFileSync(jsonlPath,entries.join('\n'));
  assert.throws(()=>preflightArtinFixture(temp,{observedCommit:ARTIN_PIN.commit}),/FORMAL_STATEMENT_CHANGED/);
});
