// Brahe #608 source-pinned, test-only transplant. A first-party retrospective,
// not a claim of independent discovery or production Check use.
export const BRAHE_SOURCE_V1=Object.freeze({
  repository:'duncaneddy/brahe',
  baseSha:'323c4542ad915aa1b6a1dbf65f1f6a8040609294',
  headSha:'f40f97da4094fddbd3745158f0123f9bcd0f3bd3',
  baseBlobSha:'e161f52140cbcff04d0d7cbf0500b1c7cbd7dccf',
  headBlobSha:'eb4172629778a63f874871629ddebc8fe0701858',
  path:'src/events/detection.rs'
});

const MARKER='#[cfg(test)]\nmod tests {';
const BASE_GUARD='if !crossed && current_crossing.abs() > detector.value_tolerance() {';
const HEAD_GUARD='let near_target_in_direction = current_crossing.abs() <= detector.value_tolerance()';

function boundary(source) {
  if (typeof source!=='string') throw new Error('TEST_BOUNDARY_INVALID_INPUT');
  const idx=source.indexOf(MARKER);
  if (idx<0 || source.indexOf(MARKER,idx+1)!==-1) throw new Error('TEST_BOUNDARY_NOT_UNIQUE');
  return idx;
}

function count(haystack,needle) {
  return haystack.split(needle).length-1;
}

export function transplantBraheTestsV1({baseSource,headSource}={}) {
  const baseIdx=boundary(baseSource);
  const headIdx=boundary(headSource);
  const baseCode=baseSource.slice(0,baseIdx);
  const headCode=headSource.slice(0,headIdx);
  if (count(baseCode,BASE_GUARD)!==2 || count(baseCode,HEAD_GUARD)!==0)
    throw new Error('BASE_GUARD_NOT_EXACT_BUGGY_FORM');
  if (count(headCode,HEAD_GUARD)!==2 || count(headCode,BASE_GUARD)!==0)
    throw new Error('HEAD_GUARD_NOT_EXACT_CORRECTED_FORM');
  const tests=headSource.slice(headIdx);
  return {
    patchedBaseSource:baseCode+tests,
    baseProductionBytes:Buffer.byteLength(baseCode),
    headTestModuleBytes:Buffer.byteLength(tests)
  };
}
