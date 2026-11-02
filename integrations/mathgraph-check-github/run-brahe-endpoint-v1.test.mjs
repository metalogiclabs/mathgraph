import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { parseBraheNativeV1,buildBraheRunReceiptV1,combineBraheReceiptsV1 } from './run-brahe-endpoint-v1.mjs';

const prefix='events::detection::tests::';
const negative=[
  'test_sscan_rejects_decreasing_detector_at_increasing_endpoint',
  'test_sscan_rejects_increasing_detector_at_decreasing_endpoint',
  'test_dscan_rejects_decreasing_detector_at_increasing_endpoint',
  'test_dscan_rejects_increasing_detector_at_decreasing_endpoint'
];
const positive=[
  'test_sscan_accepts_direction_matching_endpoint',
  'test_sscan_accepts_any_direction_at_endpoint',
  'test_dscan_accepts_direction_matching_endpoint',
  'test_dscan_accepts_any_direction_at_endpoint'
];
const legacy=[
  'test_bisection_search_time_event',
  'test_scan_for_event',
  'test_scan_for_event_backward',
  'test_step_reduction_factor_is_used',
  'test_bracket_termination',
  'test_event_near_bracket_boundary',
  'test_dscan_value_event_position_crossing',
  'test_dscan_value_event_no_crossing',
  'test_dscan_value_event_increasing_direction'
];
const basePanic=[
  "thread 'events::detection::tests::test_sscan_rejects_decreasing_detector_at_increasing_endpoint' panicked at src/events/detection.rs:1037:9:",
  'assertion failed: !static_endpoint_detected(-2.0, 0.0, EventDirection::Decreasing)',
  "thread 'events::detection::tests::test_sscan_rejects_increasing_detector_at_decreasing_endpoint' panicked at src/events/detection.rs:1047:9:",
  'assertion failed: !static_endpoint_detected(2.0, 0.0, EventDirection::Increasing)',
  "thread 'events::detection::tests::test_dscan_rejects_decreasing_detector_at_increasing_endpoint' panicked at src/events/detection.rs:1057:9:",
  'assertion failed: !dynamic_endpoint_detected(-2.0, 0.0, EventDirection::Decreasing)',
  "thread 'events::detection::tests::test_dscan_rejects_increasing_detector_at_decreasing_endpoint' panicked at src/events/detection.rs:1067:9:",
  'assertion failed: !dynamic_endpoint_detected(2.0, 0.0, EventDirection::Increasing)',
  'error: test failed, to rerun pass `-p brahe --lib`'
].join('\n');
function output(base=false) {
  const statuses=[...negative.map(name=>[name,base?'FAILED':'ok']),...positive.map(name=>[name,'ok']),...legacy.map(name=>[name,'ok'])];
  const summary=base?'test result: FAILED. 13 passed; 4 failed; 0 ignored; 0 measured; 1945 filtered out;':'test result: ok. 17 passed; 0 failed; 0 ignored; 0 measured; 1945 filtered out;';
  return ['running 17 tests',...statuses.map(([name,kind])=>`test ${prefix}${name} ... ${kind}`),summary,''].join('\n');
}

test('specific four wrong-direction endpoint failures with 13 passes is a bounded base regression',()=>{
  const x=parseBraheNativeV1({exitCode:101,stdout:output(true),stderr:basePanic,mode:'base'});
  assert.equal(x.reason,'EXPECTED_REGRESSION');
  assert.equal(x.testCount,17);
  assert.equal(x.regressionCount,4);
});

test('all 17 tests passing on fixed head is bounded PASS',()=>{
  const x=parseBraheNativeV1({exitCode:0,stdout:output(false),stderr:'',mode:'head'});
  assert.equal(x.reason,'PASSED');
  assert.equal(x.testCount,17);
});

test('Cargo test-failed trailer is not confused with compilation failure after four named regressions',()=>{
  const x=parseBraheNativeV1({
    exitCode:101,
    stdout:output(true),
    stderr:basePanic,
    mode:'base'
  });
  assert.equal(x.reason,'EXPECTED_REGRESSION');
});

test('an unnamed replacement among the nine legacy cases cannot satisfy an exact 17-test claim',()=>{
  const changed=output(true).replace(`test ${prefix}${legacy[0]} ... ok`,
    `test ${prefix}test_unrelated_replacement ... ok`);
  assert.equal(parseBraheNativeV1({exitCode:101,stdout:changed,stderr:basePanic,mode:'base'}).reason,'UNEXPECTED_FAILURE');
});

test('matching test names and counts without each genuine assertion panic cannot support the base regression',()=>{
  assert.equal(parseBraheNativeV1({exitCode:101,stdout:output(true),stderr:'unrelated panic',mode:'base'}).reason,'UNEXPECTED_FAILURE');
  assert.equal(parseBraheNativeV1({exitCode:101,stdout:output(true),stderr:basePanic.replace(
    'assertion failed: !static_endpoint_detected(-2.0, 0.0, EventDirection::Decreasing)',
    'assertion failed: unrelated_data_error'),mode:'base'}).reason,'UNEXPECTED_FAILURE');
});

test('setup failures, wrong test name, zero tests and unexpected failures are UNKNOWN rather than regressions',()=>{
  assert.equal(parseBraheNativeV1({exitCode:101,stdout:'',stderr:'error[E0432]: unresolved import',mode:'base'}).reason,'SETUP_FAILED');
  assert.equal(parseBraheNativeV1({exitCode:0,stdout:'running 0 tests\ntest result: ok. 0 passed; 0 failed;',mode:'head'}).reason,'ZERO_TESTS');
  assert.equal(parseBraheNativeV1({exitCode:101,stdout:output(true).replace(negative[0],'not_the_same_test'),stderr:basePanic,mode:'base'}).reason,'UNEXPECTED_FAILURE');
  assert.equal(parseBraheNativeV1({exitCode:101,stdout:output(true).replace('13 passed; 4 failed','12 passed; 5 failed'),stderr:basePanic,mode:'base'}).reason,'UNEXPECTED_FAILURE');
  assert.equal(parseBraheNativeV1({exitCode:101,stdout:output(true).replace('... FAILED','... ok'),stderr:basePanic,mode:'base'}).reason,'UNEXPECTED_FAILURE');
});

test('native receipts retain raw log hashes and source identities',()=>{
  const leg=buildBraheRunReceiptV1({mode:'base',sourceSha:'323c4542ad915aa1b6a1dbf65f1f6a8040609294',exitCode:101,stdout:output(true),stderr:basePanic});
  assert.equal(leg.logSha256,createHash('sha256').update(output(true)+'\n'+basePanic).digest('hex'));
  assert.equal(leg.reason,'EXPECTED_REGRESSION');
});

test('combined before/after stays CANDIDATE until independent run readback; swapped source fails closed',()=>{
  const base=buildBraheRunReceiptV1({mode:'base',sourceSha:'323c4542ad915aa1b6a1dbf65f1f6a8040609294',exitCode:101,stdout:output(true),stderr:basePanic});
  const head=buildBraheRunReceiptV1({mode:'head',sourceSha:'f40f97da4094fddbd3745158f0123f9bcd0f3bd3',exitCode:0,stdout:output(false),stderr:''});
  const opts={base,head,rustc:'rustc 1.99.1 (test)',cargoLockSha256:'a'.repeat(64),workflowRunUrl:'https://github.com/metalogiclabs/mathgraph/actions/runs/41419999999',basePatchedBlobSha:'b'.repeat(40)};
  assert.equal(combineBraheReceiptsV1(opts).verdict.status,'CANDIDATE_BOUNDED');
  assert.ok(combineBraheReceiptsV1(opts).verdict.unknowns.includes('RECEIPT_AUTHENTICITY_NOT_CHECKED'));
  assert.equal(combineBraheReceiptsV1({...opts,base:{...base,sourceSha:head.sourceSha}}).verdict.status,'UNKNOWN');
});
