import test from 'node:test';
import assert from 'node:assert/strict';
import {renderBraheEvidenceV1} from './brahe-evidence-presentation-v1.mjs';

const source={baseSha:'323c4542ad915aa1b6a1dbf65f1f6a8040609294',headSha:'f40f97da4094fddbd3745158f0123f9bcd0f3bd3'};
const verdict={status:'CANDIDATE_BOUNDED',authority:'ADVISORY_ONLY',source,evidence:{base:{reason:'EXPECTED_REGRESSION',regressionCount:4,testCount:17},head:{reason:'PASSED',testCount:17}},unknowns:['RECEIPT_AUTHENTICITY_NOT_CHECKED','EXTERNAL_CHECK_USE_UNKNOWN']};

test('Brahe preview shows the bounded before/after observation with no customer or Check adoption claim',()=>{
  const r=renderBraheEvidenceV1(verdict,{headSha:source.headSha,checks:[{name:'Rust tests',conclusion:'success'},{name:'lint',conclusion:'failure'}]});
  assert.equal(r.checkOutput.conclusion,'neutral');
  assert.match(r.markdown,/CANDIDATE_BOUNDED/);
  assert.match(r.markdown,/4\/17/);
  assert.match(r.markdown,/323c4542/);
  assert.match(r.markdown,/f40f97da/);
  assert.match(r.markdown,/lint: failure/);
  assert.match(r.markdown,/EXTERNAL_CHECK_USE_UNKNOWN/);
  assert.doesNotMatch(r.markdown,/all CI green|customer pilot|merge approved/i);
});

test('UNKNOWN and wrong-head CI cannot present the regression as reproduced',()=>{
  const r=renderBraheEvidenceV1({...verdict,status:'UNKNOWN',evidence:null},{headSha:source.baseSha,checks:[{name:'Rust tests',conclusion:'success'}]});
  assert.match(r.markdown,/UNKNOWN/);
  assert.match(r.markdown,/CI_HEAD_MISMATCH/);
  assert.doesNotMatch(r.markdown,/Rust tests: success|4\/17/);
});

test('untrusted check names cannot inject raw HTML, mentions or Markdown links',()=>{
  const r=renderBraheEvidenceV1(verdict,{headSha:source.headSha,checks:[{name:'<script>@all [click](url)</script>',conclusion:'success'}]});
  assert.doesNotMatch(r.markdown,/<script>|@all|\[click\]\(url\)/);
});
