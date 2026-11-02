import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {BRAHE_SOURCE_V1} from './brahe-endpoint-v1.mjs';
import {buildBraheRunReceiptV1,combineBraheReceiptsV1} from './run-brahe-endpoint-v1.mjs';
import {verifyBraheArtifactReadbackV1} from './brahe-artifact-readback-v1.mjs';

const ns='events::detection::tests::';
const negative=['test_sscan_rejects_decreasing_detector_at_increasing_endpoint','test_sscan_rejects_increasing_detector_at_decreasing_endpoint','test_dscan_rejects_decreasing_detector_at_increasing_endpoint','test_dscan_rejects_increasing_detector_at_decreasing_endpoint'];
const positive=['test_sscan_accepts_direction_matching_endpoint','test_sscan_accepts_any_direction_at_endpoint','test_dscan_accepts_direction_matching_endpoint','test_dscan_accepts_any_direction_at_endpoint'];
const other=Array.from({length:9},(_,i)=>'test_legacy_'+i);
const hash=text=>createHash('sha256').update(text).digest('hex');

function logs(base) {
  const names=[...negative,...positive,...other];
  const status=name=>base&&negative.includes(name)?'FAILED':'ok';
  return `running 17 tests\n${names.map(name=>`test ${ns}${name} ... ${status(name)}`).join('\n')}\n${base?'test result: FAILED. 13 passed; 4 failed;':'test result: ok. 17 passed; 0 failed;'}\n`;
}
function fixture() {
  const baseOut=logs(true),headOut=logs(false),lockfile='version = 4\n';
  const base=buildBraheRunReceiptV1({mode:'base',sourceSha:BRAHE_SOURCE_V1.baseSha,exitCode:101,stdout:baseOut,stderr:''});
  const head=buildBraheRunReceiptV1({mode:'head',sourceSha:BRAHE_SOURCE_V1.headSha,exitCode:0,stdout:headOut,stderr:''});
  const combined=combineBraheReceiptsV1({base,head,rustc:'rustc 1.99.1 (fixture)',cargoLockSha256:hash(lockfile),workflowRunUrl:'https://github.com/metalogiclabs/mathgraph/actions/runs/41414043619',basePatchedBlobSha:'b'.repeat(40)});
  return {combined,logs:{base:{stdout:baseOut,stderr:''},head:{stdout:headOut,stderr:''}},lockfile,transplantManifest:{source:{...BRAHE_SOURCE_V1},baseProductionBytes:1000,headTestModuleBytes:2000,patchedSourceSha256:'a'.repeat(64)},metadata:{id:41414043619,repository:{full_name:'metalogiclabs/mathgraph'},head_sha:'9b37e4ee2cf25fdaef32d721572527a79802a329',head_branch:'research/mathgraph-check-brahe-v1-20261102',path:'.github/workflows/mathgraph-check-brahe-endpoint-v1.yml',status:'completed',conclusion:'success'}};
}

test('consistent archived bytes and run metadata are readback-consistent, never automatically warranted',()=>{
  const result=verifyBraheArtifactReadbackV1(fixture());
  assert.equal(result.status,'READBACK_CONSISTENT');
  assert.equal(result.authority,'ADVISORY_ONLY');
  assert.ok(result.unknowns.includes('CALLER_SUPPLIED_GITHUB_METADATA_NOT_AUTHENTICATED'));
});

test('tampered Rust output, lockfile or transplant manifest fail closed',()=>{
  const corrupt=fixture();corrupt.logs.head.stdout+='tampered';
  assert.equal(verifyBraheArtifactReadbackV1(corrupt).status,'UNKNOWN');
  const lock=fixture();lock.lockfile+='tampered';
  assert.equal(verifyBraheArtifactReadbackV1(lock).status,'UNKNOWN');
  const manifest=fixture();manifest.transplantManifest.source.baseSha='0'.repeat(40);
  assert.equal(verifyBraheArtifactReadbackV1(manifest).status,'UNKNOWN');
});

test('a failed or wrong-repository GitHub run cannot authorize its self-asserted candidate',()=>{
  const failed=fixture();failed.metadata.conclusion='failure';
  assert.equal(verifyBraheArtifactReadbackV1(failed).status,'UNKNOWN');
  const foreign=fixture();foreign.metadata.repository.full_name='other/other';
  assert.equal(verifyBraheArtifactReadbackV1(foreign).status,'UNKNOWN');
  const mismatched=fixture();mismatched.metadata.id++;
  assert.equal(verifyBraheArtifactReadbackV1(mismatched).status,'UNKNOWN');
});
