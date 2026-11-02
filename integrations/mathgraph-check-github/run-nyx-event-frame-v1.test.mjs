import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtemp, readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { parseNyxNativeRunV1, buildNyxRunReceiptV1, combineNyxRunReceiptsV1, runNyxCliV1 } from './run-nyx-event-frame-v1.mjs';

const name = 'propagation::stopcond::longitude_event_in_rotating_frame';
const base = `running 1 test\ntest ${name} ... FAILED\n\nthread '${name}' panicked at nyx-core/tests/propagation/stopcond.rs:311:\nEarth-fixed longitude zero must be found in the requested event frame: EventNotFound\n\ntest result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 140 filtered out; finished in 0.01s\n`;
const head = `running 1 test\ntest ${name} ... ok\n\ntest result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 140 filtered out; finished in 0.01s\n`;

test('pinpointed base panic with EventNotFound counts as regression, not a generic failed command', () => {
  assert.deepEqual(parseNyxNativeRunV1({ exitCode: 101, stdout: base, stderr: '', expectedMode: 'base' }), {
    exitCode: 101, testCount: 1, regressionMarker: 'EventNotFound', reason: 'EXPECTED_REGRESSION'
  });
});

test('exact named native test pass establishes a finite observed head result', () => {
  assert.deepEqual(parseNyxNativeRunV1({ exitCode: 0, stdout: head, stderr: '', expectedMode: 'head' }), {
    exitCode: 0, testCount: 1, regressionMarker: null, reason: 'PASSED'
  });
});

test('zero tests and compile failure are not mistaken for native verification', () => {
  assert.equal(parseNyxNativeRunV1({exitCode:0, stdout:'running 0 tests\ntest result: ok. 0 passed; 0 failed;', stderr:'', expectedMode:'head'}).reason, 'ZERO_TESTS');
  assert.equal(parseNyxNativeRunV1({exitCode:101, stdout:'', stderr:'error: could not compile `nyx-space`', expectedMode:'base'}).reason, 'SETUP_FAILED');
});

test('base success, head failure or a different panic cannot establish the PR before-after claim', () => {
  assert.equal(parseNyxNativeRunV1({exitCode:0,stdout:head,stderr:'',expectedMode:'base'}).reason,'UNEXPECTED_PASS');
  assert.equal(parseNyxNativeRunV1({exitCode:101,stdout:base,stderr:'',expectedMode:'head'}).reason,'UNEXPECTED_FAILURE');
  assert.equal(parseNyxNativeRunV1({exitCode:101,stdout:base.replace(/EventNotFound/g,'Timeout'),stderr:'',expectedMode:'base'}).reason,'UNEXPECTED_FAILURE');
});

test('a foreign test name or ambiguous summary is rejected', () => {
  assert.equal(parseNyxNativeRunV1({exitCode:0,stdout:head.replace(name,'propagation::stopcond::another_test'),stderr:'',expectedMode:'head'}).reason,'UNEXPECTED_FAILURE');
  assert.equal(parseNyxNativeRunV1({exitCode:0,stdout:head.replace('running 1 test','running 2 tests'),stderr:'',expectedMode:'head'}).reason,'UNEXPECTED_FAILURE');
});

test('a native leg receipt preserves exact combined log identity and the finite outcome', () => {
  const result = buildNyxRunReceiptV1({mode:'base',exitCode:101,stdout:base,stderr:'',sourceSha:'d1c3598d5ccf4c984a1d3dd82c450e2af363e821'});
  assert.equal(result.reason,'EXPECTED_REGRESSION');
  assert.equal(result.testCount,1);
  assert.equal(result.sourceSha,'d1c3598d5ccf4c984a1d3dd82c450e2af363e821');
  assert.equal(result.logSha256,createHash('sha256').update(base+'\n').digest('hex'));
});

test('combined receipt remains a candidate until GitHub and log readback', () => {
  const a = buildNyxRunReceiptV1({mode:'base',exitCode:101,stdout:base,stderr:'',sourceSha:'d1c3598d5ccf4c984a1d3dd82c450e2af363e821'});
  const b = buildNyxRunReceiptV1({mode:'head',exitCode:0,stdout:head,stderr:'',sourceSha:'ac819f7ab351eccb0b1ae9b5fd361a3a1a9e4a9b'});
  const result = combineNyxRunReceiptsV1({base:a,head:b,rustc:'rustc 1.91.0 (test fixture)',cargoLockSha256:'c'.repeat(64),workflowRunUrl:'https://github.com/metalogiclabs/mathgraph/actions/runs/41409999999'});
  assert.equal(result.verdict.status,'CANDIDATE_BOUNDED');
  assert.ok(result.verdict.unknowns.includes('RECEIPT_AUTHENTICITY_NOT_CHECKED'));
  assert.equal(result.receipt.base.logSha256,a.logSha256);
});

test('swapped leg source commits cannot be promoted by the combined receipt builder', () => {
  const a = buildNyxRunReceiptV1({mode:'base',exitCode:101,stdout:base,stderr:'',sourceSha:'ac819f7ab351eccb0b1ae9b5fd361a3a1a9e4a9b'});
  const b = buildNyxRunReceiptV1({mode:'head',exitCode:0,stdout:head,stderr:'',sourceSha:'d1c3598d5ccf4c984a1d3dd82c450e2af363e821'});
  const result = combineNyxRunReceiptsV1({base:a,head:b,rustc:'rustc 1.91.0 (test fixture)',cargoLockSha256:'c'.repeat(64),workflowRunUrl:'https://github.com/metalogiclabs/mathgraph/actions/runs/41409999999'});
  assert.equal(result.verdict.status,'UNKNOWN');
});

test('CLI reads actual log bytes and writes a parseable source-bound leg receipt', async () => {
  const dir=await mkdtemp(join(tmpdir(),'mathgraph-nyx-test-'));
  const stdout=join(dir,'stdout'),stderr=join(dir,'stderr'),out=join(dir,'base.json');
  await writeFile(stdout,base); await writeFile(stderr,'');
  await runNyxCliV1(['--mode','base','--exit','101','--source-sha','d1c3598d5ccf4c984a1d3dd82c450e2af363e821','--stdout',stdout,'--stderr',stderr,'--out',out]);
  const result=JSON.parse(await readFile(out,'utf8'));
  assert.equal(result.sourceSha,'d1c3598d5ccf4c984a1d3dd82c450e2af363e821');
  assert.equal(result.reason,'EXPECTED_REGRESSION');
});
