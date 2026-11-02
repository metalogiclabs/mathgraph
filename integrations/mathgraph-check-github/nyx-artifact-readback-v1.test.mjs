import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { buildNyxRunReceiptV1, combineNyxRunReceiptsV1 } from './run-nyx-event-frame-v1.mjs';
import { verifyNyxArtifactReadbackV1 } from './nyx-artifact-readback-v1.mjs';

const baseSha='d1c3598d5ccf4c984a1d3dd82c450e2af363e821';
const headSha='ac819f7ab351eccb0b1ae9b5fd361a3a1a9e4a9b';
const testName='propagation::stopcond::longitude_event_in_rotating_frame';
const baseOut=`running 1 test\ntest ${testName} ... FAILED\nEarth-fixed longitude zero must be found in the requested event frame: EventNotFound\ntest result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 140 filtered out;\n`;
const headOut=`running 1 test\ntest ${testName} ... ok\ntest result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 140 filtered out;\n`;
const hash=s=>createHash('sha256').update(s).digest('hex');

function fixture() {
  const lockfile='version = 4\n# test-only resolved Cargo.lock\n';
  const base=buildNyxRunReceiptV1({mode:'base',sourceSha:baseSha,exitCode:101,stdout:baseOut,stderr:''});
  const head=buildNyxRunReceiptV1({mode:'head',sourceSha:headSha,exitCode:0,stdout:headOut,stderr:''});
  const combined=combineNyxRunReceiptsV1({base,head,rustc:'rustc 1.91.0 (test)',cargoLockSha256:hash(lockfile),workflowRunUrl:'https://github.com/metalogiclabs/mathgraph/actions/runs/41410086743'});
  const metadata={id:41410086743,repository:{full_name:'metalogiclabs/mathgraph'},head_sha:'4d7345a6343153fda5db81705c740b8457360c99',head_branch:'research/mathgraph-check-nyx-v1-20261102',path:'.github/workflows/mathgraph-check-nyx-event-frame-v1.yml',status:'completed',conclusion:'success'};
  return {combined,logs:{base:{stdout:baseOut,stderr:''},head:{stdout:headOut,stderr:''}},lockfile,metadata};
}

test('re-read exact artifact logs and lockfile; never equate caller metadata with authenticated GitHub',()=>{
  const result=verifyNyxArtifactReadbackV1(fixture());
  assert.equal(result.status,'READBACK_CONSISTENT');
  assert.equal(result.authority,'ADVISORY_ONLY');
  assert.ok(result.unknowns.includes('CALLER_SUPPLIED_GITHUB_METADATA_NOT_AUTHENTICATED'));
  assert.doesNotMatch(JSON.stringify(result),/WARRANTED_BOUNDED/);
});

test('a single changed log byte or dependency lock is not readback-consistent',()=>{
  const tampered=fixture();tampered.logs.base.stdout+='one byte';
  assert.equal(verifyNyxArtifactReadbackV1(tampered).status,'UNKNOWN');
  const wrongLock=fixture();wrongLock.lockfile+='[pkg]';
  assert.equal(verifyNyxArtifactReadbackV1(wrongLock).status,'UNKNOWN');
});

test('a run with incorrect identity, failed workflow or reversed source leg never qualifies',()=>{
  const wrongRun=fixture();wrongRun.metadata.id=41410086744;
  assert.equal(verifyNyxArtifactReadbackV1(wrongRun).status,'UNKNOWN');
  const wrongRepo=fixture();wrongRepo.metadata.repository.full_name='unrelated/repo';
  assert.equal(verifyNyxArtifactReadbackV1(wrongRepo).status,'UNKNOWN');
  const failed=fixture();failed.metadata.conclusion='failure';
  assert.equal(verifyNyxArtifactReadbackV1(failed).status,'UNKNOWN');
  const swapped=fixture();swapped.combined.receipt.base.sourceSha=headSha;
  assert.equal(verifyNyxArtifactReadbackV1(swapped).status,'UNKNOWN');
});
