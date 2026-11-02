import test from 'node:test';
import assert from 'node:assert/strict';
import { renderNyxEvidenceV1 } from './nyx-evidence-presentation-v1.mjs';

const base='d1c3598d5ccf4c984a1d3dd82c450e2af363e821';
const head='ac819f7ab351eccb0b1ae9b5fd361a3a1a9e4a9b';
const verdict={
  status:'CANDIDATE_BOUNDED',authority:'ADVISORY_ONLY',
  source:{repository:'nyx-space/nyx',baseSha:base,headSha:head,testBlobSha:'830919f246536ccc65be4041e9a4b775220f57bb'},
  evidence:{base:{reason:'EXPECTED_REGRESSION',regressionMarker:'EventNotFound'},head:{reason:'PASSED'},runner:{workflowRunUrl:'https://github.com/metalogiclabs/mathgraph/actions/runs/41409999999'}},
  unknowns:['REQUIREMENT_AUTHOR_INTENT_NOT_INDEPENDENTLY_AUTHENTICATED','RECEIPT_AUTHENTICITY_NOT_CHECKED']
};

test('a readable neutral Check marks evidence candidate and source identities without authorizing merge',()=>{
  const result=renderNyxEvidenceV1(verdict,{headSha:head,checks:[{name:'Tests (ubuntu-latest, stable)',conclusion:'success'},{name:'Lints',conclusion:'failure'}]});
  assert.equal(result.checkOutput.conclusion,'neutral');
  assert.equal(result.checkOutput.status,'completed');
  assert.match(result.markdown,/CANDIDATE_BOUNDED/);
  assert.match(result.markdown,/ADVISORY_ONLY/);
  assert.match(result.markdown,/EventNotFound/);
  assert.match(result.markdown,/d1c3598/);
  assert.match(result.markdown,/ac819f7/);
  assert.match(result.markdown,/RECEIPT_AUTHENTICITY_NOT_CHECKED/);
  assert.doesNotMatch(result.markdown,/all CI green|merge approved/i);
  assert.match(result.markdown,/Lints.*failure/);
});

test('wrong-head CI is not presented as current and impossible receipt stays unknown',()=>{
  const result=renderNyxEvidenceV1({...verdict,status:'UNKNOWN',evidence:null},{headSha:base,checks:[{name:'Tests',conclusion:'success'}]});
  assert.match(result.markdown,/UNKNOWN/);
  assert.match(result.markdown,/CI_HEAD_MISMATCH/);
  assert.doesNotMatch(result.markdown,/Tests: success/);
});

test('untrusted check names cannot inject markdown or HTML into reviewer output',()=>{
  const result=renderNyxEvidenceV1(verdict,{headSha:head,checks:[{name:'<script>alert(1)</script> @all [click](bad)',conclusion:'failure'}]});
  assert.doesNotMatch(result.markdown,/<script>|@all|\[click\]\(bad\)/);
});
