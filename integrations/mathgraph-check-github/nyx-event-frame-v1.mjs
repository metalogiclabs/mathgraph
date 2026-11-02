// One source-pinned, retrospective Nyx #613 observation boundary.
// Caller-provided receipts are not authenticated by this pure module.
const SOURCE = Object.freeze({
  repository: 'nyx-space/nyx',
  baseSha: 'd1c3598d5ccf4c984a1d3dd82c450e2af363e821',
  headSha: 'ac819f7ab351eccb0b1ae9b5fd361a3a1a9e4a9b',
  testBlobSha: '830919f246536ccc65be4041e9a4b775220f57bb'
});
const DIGEST = /^[a-f0-9]{64}$/;
const RUN_URL = /^https:\/\/github\.com\/metalogiclabs\/mathgraph\/actions\/runs\/[1-9][0-9]*$/;
const SCOPE = 'nyx-space/nyx #613: longitude_event_in_rotating_frame; same transplanted Rust regression on pinned base and head only';

function valid(r) {
  if (!r || typeof r !== 'object' || Array.isArray(r)) return false;
  if (!r.source || Object.entries(SOURCE).some(([key, value]) => r.source[key] !== value)) return false;
  if (!r.base || r.base.exitCode === 0 || !Number.isSafeInteger(r.base.exitCode) ||
      r.base.testCount !== 1 || r.base.reason !== 'EXPECTED_REGRESSION' ||
      r.base.regressionMarker !== 'EventNotFound' || !DIGEST.test(r.base.logSha256 ?? '') ||
      (r.base.sourceSha !== undefined && r.base.sourceSha !== SOURCE.baseSha)) return false;
  if (!r.head || r.head.exitCode !== 0 || r.head.testCount !== 1 ||
      r.head.reason !== 'PASSED' || !DIGEST.test(r.head.logSha256 ?? '') ||
      (r.head.sourceSha !== undefined && r.head.sourceSha !== SOURCE.headSha)) return false;
  if (!r.toolchain || typeof r.toolchain.rustc !== 'string' || !/^rustc [0-9]/.test(r.toolchain.rustc) ||
      !DIGEST.test(r.toolchain.cargoLockSha256 ?? '')) return false;
  if (!r.runner || !RUN_URL.test(r.runner.workflowRunUrl ?? '')) return false;
  return true;
}

export function evaluateNyxEventFrameV1(receipt) {
  const isCandidate = valid(receipt);
  return {
    schema: 'mathgraph.nyx-event-frame-retrospective.v1',
    status: isCandidate ? 'CANDIDATE_BOUNDED' : 'UNKNOWN',
    authority: 'ADVISORY_ONLY',
    scope: SCOPE,
    source: { ...SOURCE },
    evidence: isCandidate ? {
      base: { ...receipt.base },
      head: { ...receipt.head },
      toolchain: { ...receipt.toolchain },
      runner: { ...receipt.runner }
    } : null,
    unknowns: [
      'REQUIREMENT_AUTHOR_INTENT_NOT_INDEPENDENTLY_AUTHENTICATED',
      'RECEIPT_AUTHENTICITY_NOT_CHECKED',
      'GENERAL_RUST_CORRECTNESS_UNKNOWN',
      ...(isCandidate ? [] : ['EVIDENCE_INCOMPLETE_OR_MISMATCHED'])
    ]
  };
}
