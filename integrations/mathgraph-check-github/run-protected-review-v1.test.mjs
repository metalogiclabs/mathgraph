import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {mkdtempSync,rmSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

const script=new URL('./run-protected-review-v1.mjs',import.meta.url).pathname;
const execute=env=>spawnSync(process.execPath,[script],{
 env:{...process.env,...env},encoding:'utf8',timeout:8000});
const base={GITHUB_REPOSITORY:'metalogiclabs/L4YAML',
 GITHUB_EVENT_NAME:'workflow_dispatch',GITHUB_REF:'refs/heads/main',
 MATHGRAPH_DEFAULT_BRANCH:'main',MATHGRAPH_PR_NUMBER:'9',
 GITHUB_TOKEN:'dummy-github-token-do-not-print',
 MATHGRAPH_EVIDENCE_TOKEN:'dummy-evidence-token-do-not-print',
 MATHGRAPH_PROOF_ARTIFACT_ID:'100'};

test('missing externally administered policy files remain UNKNOWN without leaking tokens',()=>{
 const r=execute({...base,MATHGRAPH_SIGNED_REVIEW_FILE:'/missing/signed.json',
  MATHGRAPH_TRUSTED_REVIEWER_KEYS_FILE:'/missing/keys.json',
  MATHGRAPH_TRUSTED_PROOF_RECEIPT_FILE:'/missing/receipt.json',
  MATHGRAPH_PROOF_ARTIFACT_PATH:'/missing/proof.zip'});
 assert.equal(r.status,3);
 const report=JSON.parse(r.stdout);
 assert.equal(report.status,'UNKNOWN');
 assert.equal(report.permission,'ADVISORY_ONLY');
 assert.ok(!r.stdout.includes(base.GITHUB_TOKEN)&&!r.stderr.includes(base.MATHGRAPH_EVIDENCE_TOKEN));
});
test('PR-context runner refuses before it attempts to read any privileged policy file',()=>{
 const r=execute({...base,GITHUB_EVENT_NAME:'pull_request',GITHUB_REF:'refs/pull/9/merge',
  MATHGRAPH_SIGNED_REVIEW_FILE:'/missing/signed.json',
  MATHGRAPH_TRUSTED_REVIEWER_KEYS_FILE:'/missing/keys.json',
  MATHGRAPH_TRUSTED_PROOF_RECEIPT_FILE:'/missing/receipt.json',
  MATHGRAPH_PROOF_ARTIFACT_PATH:'/missing/proof.zip'});
 assert.equal(r.status,3);
 assert.equal(JSON.parse(r.stdout).reason,'PROTECTED_DEFAULT_BRANCH_DISPATCH_REQUIRED');
});
test('malformed protected policy JSON never triggers a GitHub request',()=>{
 const dir=mkdtempSync(join(tmpdir(),'mathgraph-protected-cli-test-'));
 try{
  const keyfile=join(dir,'keys.json'),receipt=join(dir,'receipt.json'),review=join(dir,'review.json');
  writeFileSync(keyfile,'{"reviewer":"some-key"}');
  writeFileSync(receipt,'NOT JSON');
  writeFileSync(review,'{}');
  const r=execute({...base,MATHGRAPH_SIGNED_REVIEW_FILE:review,
   MATHGRAPH_TRUSTED_REVIEWER_KEYS_FILE:keyfile,
   MATHGRAPH_TRUSTED_PROOF_RECEIPT_FILE:receipt,
   MATHGRAPH_PROOF_ARTIFACT_PATH:'/missing/proof.zip'});
  assert.equal(r.status,3);
  assert.equal(JSON.parse(r.stdout).status,'UNKNOWN');
  assert.ok(!r.stdout.includes('NOT JSON')&&!r.stderr.includes('NOT JSON'));
 }finally{rmSync(dir,{recursive:true,force:true});}
});
