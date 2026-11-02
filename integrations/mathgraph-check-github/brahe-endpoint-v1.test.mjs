import test from 'node:test';
import assert from 'node:assert/strict';
import { transplantBraheTestsV1 } from './brahe-endpoint-v1.mjs';

const guard='if !crossed && current_crossing.abs() > detector.value_tolerance() {';
const fixed='let near_target_in_direction = current_crossing.abs() <= detector.value_tolerance()';
const baseCode=`// original Brahe implementation\n${guard}\nreturn None;\n}\n${guard}\nreturn None;\n}\n`;
const headCode=`// corrected Brahe implementation\n${fixed}\n${fixed}\n`;
const marker='#[cfg(test)]\nmod tests {';
const baseSource=baseCode+marker+'\n#[test] fn preexisting() {}\n}\n';
const headSource=headCode+marker+'\n#[test] fn preexisting() {}\n#[test] fn new_regression() { assert!(true); }\n}\n';

test('transplant copies only head tests; original buggy base implementation is byte-for-byte retained',()=>{
  const result=transplantBraheTestsV1({baseSource,headSource});
  assert.equal(result.patchedBaseSource,baseCode+headSource.slice(headCode.length));
  assert.equal(result.baseProductionBytes,Buffer.byteLength(baseCode));
  assert.equal(result.headTestModuleBytes,Buffer.byteLength(headSource.slice(headCode.length)));
  assert.equal(result.patchedBaseSource.includes(fixed),false);
  assert.equal(result.patchedBaseSource.match(/if !crossed && current_crossing.abs\(\) > detector.value_tolerance\(\)/g).length,2);
});

test('missing or duplicated module boundary never silently overlays source',()=>{
  assert.throws(()=>transplantBraheTestsV1({baseSource:'unmarked',headSource}),/TEST_BOUNDARY/);
  assert.throws(()=>transplantBraheTestsV1({baseSource,headSource:headSource+marker}),/TEST_BOUNDARY/);
});

test('wrong base or head implementation shape fails rather than producing misleading base comparison',()=>{
  assert.throws(()=>transplantBraheTestsV1({baseSource:headSource,headSource}),/BASE_GUARD/);
  assert.throws(()=>transplantBraheTestsV1({baseSource,headSource:baseSource}),/HEAD_GUARD/);
});
