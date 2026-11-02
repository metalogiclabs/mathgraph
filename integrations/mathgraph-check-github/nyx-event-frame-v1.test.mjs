import test from 'node:test';
import assert from 'node:assert/strict';
import { evaluateNyxEventFrameV1 } from './nyx-event-frame-v1.mjs';

const hash = c => c.repeat(64);
const good = () => ({
  source: {
    repository: 'nyx-space/nyx',
    baseSha: 'd1c3598d5ccf4c984a1d3dd82c450e2af363e821',
    headSha: 'ac819f7ab351eccb0b1ae9b5fd361a3a1a9e4a9b',
    testBlobSha: '830919f246536ccc65be4041e9a4b775220f57bb'
  },
  base: { exitCode: 101, testCount: 1, logSha256: hash('a'), regressionMarker: 'EventNotFound', reason: 'EXPECTED_REGRESSION' },
  head: { exitCode: 0, testCount: 1, logSha256: hash('b'), reason: 'PASSED' },
  toolchain: { rustc: 'rustc 1.91.0 (test fixture)', cargoLockSha256: hash('c') },
  runner: { workflowRunUrl: 'https://github.com/metalogiclabs/mathgraph/actions/runs/41409999999' }
});

test('source-identified base failure and fixed-head pass are only a bounded candidate before readback', () => {
  const result = evaluateNyxEventFrameV1(good());
  assert.equal(result.status, 'CANDIDATE_BOUNDED');
  assert.equal(result.authority, 'ADVISORY_ONLY');
  assert.equal(result.source.baseSha, good().source.baseSha);
  assert.equal(result.source.headSha, good().source.headSha);
  assert.ok(result.unknowns.includes('REQUIREMENT_AUTHOR_INTENT_NOT_INDEPENDENTLY_AUTHENTICATED'));
  assert.ok(result.unknowns.includes('RECEIPT_AUTHENTICITY_NOT_CHECKED'));
  assert.ok(result.scope.includes('longitude_event_in_rotating_frame'));
});

test('changed source identity or transplanted-test blob fails closed', () => {
  for (const mutate of [
    x => x.source.baseSha = hash('f').slice(0, 40),
    x => x.source.headSha = hash('f').slice(0, 40),
    x => x.source.testBlobSha = hash('f').slice(0, 40),
    x => x.source.repository = 'somebody/nyx'
  ]) {
    const fixture = good(); mutate(fixture);
    assert.equal(evaluateNyxEventFrameV1(fixture).status, 'UNKNOWN');
  }
});

test('missing or malformed native evidence never establishes the before-after result', () => {
  for (const mutate of [
    x => delete x.base.logSha256,
    x => x.base.exitCode = 0,
    x => x.base.regressionMarker = 'COMPILATION_FAILED',
    x => x.base.reason = 'SETUP_FAILED',
    x => x.head.exitCode = 101,
    x => x.head.testCount = 0,
    x => x.toolchain.cargoLockSha256 = 'bad',
    x => x.runner.workflowRunUrl = 'https://example.com/forged'
  ]) {
    const fixture = good(); mutate(fixture);
    assert.equal(evaluateNyxEventFrameV1(fixture).status, 'UNKNOWN');
  }
});

test('passing head alone without a reproduced failing base remains unknown', () => {
  const fixture = good(); fixture.base.testCount = 0;
  assert.equal(evaluateNyxEventFrameV1(fixture).status, 'UNKNOWN');
});

test('leg source identities cannot contradict the outer source manifest', () => {
  const fixture = good();
  fixture.base.sourceSha = fixture.source.headSha;
  assert.equal(evaluateNyxEventFrameV1(fixture).status, 'UNKNOWN');
});
