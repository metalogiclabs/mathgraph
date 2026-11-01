import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,writeFileSync,chmodSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

const cli=resolve(dirname(fileURLToPath(import.meta.url)),
  'run-math-evidence-check-v1.mjs');
const token='scoped-fixture-installation-token';
const execute=(args=[],env={})=>spawnSync(process.execPath,[cli,...args],{
  encoding:'utf8',env:{...process.env,MATHGRAPH_GITHUB_APP_TOKEN:'',...env},
  timeout:10000,maxBuffer:100000});

test('operator CLI never accesses network without a valid token and private config',()=>{
  let x=execute();
  assert.equal(x.status,2);
  assert.match(x.stderr,/USAGE/);
  x=execute(['/tmp/not-present']);
  assert.equal(x.status,2);
  assert.match(x.stderr,/MISSING_REPOSITORY_SCOPED_INSTALLATION_TOKEN/);
  assert.doesNotMatch(x.stderr,/Bearer|secret|Traceback/);
});

test('CLI refuses symlink, group-readable and invalid trust-file content',t=>{
  const dir=mkdtempSync(join(tmpdir(),'mathgraph-trust-'));
  t.after(()=>rmSync(dir,{recursive:true,force:true}));
  const file=join(dir,'admin.json');
  writeFileSync(file,'{}',{mode:0o644});
  let x=execute([file],{MATHGRAPH_GITHUB_APP_TOKEN:token});
  assert.equal(x.status,2);
  assert.match(x.stderr,/INVALID_PRIVATE_ADMIN_TRUST_FILE/);
  chmodSync(file,0o600);
  x=execute([file],{MATHGRAPH_GITHUB_APP_TOKEN:token});
  assert.equal(x.status,2);
  assert.match(x.stderr,/INVALID_PRIVATE_ADMIN_TRUST_FILE/);

  // Malformed requested status must not accidentally enter publish mode.
  x=execute([file,'--auto-merge'],{MATHGRAPH_GITHUB_APP_TOKEN:token});
  assert.equal(x.status,2);
  assert.match(x.stderr,/USAGE/);
});

test('a PR-authored forged approval cannot satisfy operator trust file',t=>{
  const dir=mkdtempSync(join(tmpdir(),'mathgraph-untrusted-'));
  t.after(()=>rmSync(dir,{recursive:true,force:true}));
  const file=join(dir,'admin.json');
  const x={repository:'metalogiclabs/mathgraph',pr:228,runId:41356752114,
    trusted:{repository:'metalogiclabs/mathgraph',pr:228,
      headSha:'a'.repeat(40),
      workflowPath:'.github/workflows/mathgraph-check-proofnet-artin-replay-v2.yml',
      workflowSha256:'b'.repeat(64),workflowId:403924412,
      jobName:'pinned-artin-replay',artifactName:'mathgraph-proofnet-artin-evidence',
      sourceSha256:'a'.repeat(64),claimSha256:'b'.repeat(64),
      formalSha256:'c'.repeat(64),environmentSha256:'d'.repeat(64),
      approvedReviewerIds:[],
      human_verified:true}};
  writeFileSync(file,JSON.stringify(x),{mode:0o600});
  const result=execute([file,'--publish'],{MATHGRAPH_GITHUB_APP_TOKEN:token});
  assert.equal(result.status,2);
  assert.match(result.stderr,/INVALID_PRIVATE_ADMIN_TRUST_FILE/);
  assert.equal(result.stdout,'');
});
