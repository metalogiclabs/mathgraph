import test from 'node:test';
import assert from 'node:assert/strict';
import {admitPlan,admitPatch,assessProbe,assessProbeDelta,assessRepair,compareProtectedSuites} from './contracts.mjs';
const sha='a'.repeat(40),other='b'.repeat(40);
const snapshot={repository:'metalogiclabs/gnss_lib_py',base_sha:other,head_sha:sha,files:[{path:'gnss_lib_py/utils/coordinates.py',head:'def f(x): return x\n',base:'def f(x): return x\n'}]};
const plan=()=>({summary:'Check empty input',tests:[{id:'empty_input',hypothesis:'Empty inputs preserve the documented shape',contract:'Source documentation states empty input is supported',source_path:'gnss_lib_py/utils/coordinates.py',code:'def test_empty():\n    assert 1 == 1\n'}]});
const receipt=(failures=0)=>({subject_sha:sha,test_digest:'c'.repeat(64),exit_code:failures?1:0,tests:1,failures,errors:0,skipped:0,timeout:false,cases:[{id:'test_x',status:failures?'failed':'passed',exception:failures?'AssertionError':null,assertions_reached:1}]});
test('generated plan accepts unfamiliar implementation path, not a target registry',()=>assert.equal(admitPlan(plan(),snapshot).tests.length,1));
for(const [name,change] of [['traversal',p=>p.tests[0].source_path='../secret.py'],['unseen file',p=>p.tests[0].source_path='other.py'],['too many tests',p=>p.tests.push(...Array(3).fill(p.tests[0]))],['duplicate ID',p=>p.tests.push(p.tests[0])],['empty probe',p=>p.tests[0].code=''],['oversize code',p=>p.tests[0].code='x'.repeat(20001)]])test(name+' rejected',()=>{const p=plan();change(p);assert.throws(()=>admitPlan(p,snapshot));});
test('candidate patch replaces only an existing implementation file',()=>assert.equal(admitPatch({summary:'Handle empty input',files:[{path:snapshot.files[0].path,content:'def f(x): return [] if x is None else x\n'}]},snapshot).files.length,1));
for(const path of ['tests/test_x.py','.github/workflows/x.py','../x.py','setup.py','pyproject.toml','gnss_lib_py/new.py'])test('patch path refused: '+path,()=>assert.throws(()=>admitPatch({summary:'patch',files:[{path,content:'pass\n'}]},snapshot)));
test('native failure is reproduced candidate, not semantic approval',()=>{const r=assessProbe(receipt(1),{subjectSha:sha,testDigest:'c'.repeat(64)});assert.equal(r.execution,'CANDIDATE_FAILURE_REPRODUCED');assert.equal(r.meaning,'UNVERIFIED');});
for(const [name,mutate] of [['wrong source',r=>r.subject_sha=other],['wrong test',r=>r.test_digest='d'.repeat(64)],['no tests',r=>r.tests=0],['only skipped',r=>r.skipped=1],['import failure',r=>r.errors=1],['timeout',r=>r.timeout=true],['inconsistent return',r=>r.exit_code=0]])test(name+' cannot be admitted',()=>{const r=receipt(1);mutate(r);assert.equal(assessProbe(r,{subjectSha:sha,testDigest:'c'.repeat(64)}).execution,'UNKNOWN');});
test('repair requires original failure, same frozen tests and protected suite passing',()=>{const original=receipt(1),fixed=receipt();assert.equal(assessRepair({original,fixed,protectedBefore:receipt(),protectedAfter:receipt()},{subjectSha:sha,testDigest:'c'.repeat(64)}).status,'REPAIR_VERIFIED_FOR_FROZEN_TESTS');});
test('reject-all or changed-test repair cannot pass',()=>{const original=receipt(1),fixed=receipt();fixed.test_digest='d'.repeat(64);assert.equal(assessRepair({original,fixed,protectedBefore:receipt(),protectedAfter:receipt()},{subjectSha:sha,testDigest:'c'.repeat(64)}).status,'UNKNOWN');});
test('remaining protected failure cannot be silently called a verified repair',()=>assert.equal(assessRepair({original:receipt(1),fixed:receipt(),protectedBefore:receipt(1),protectedAfter:receipt(1)},{subjectSha:sha,testDigest:'c'.repeat(64)}).status,'UNKNOWN'));
test('trusted control IDs cannot be replaced by generated tests',()=>{const p=plan();p.tests[0].id='control_fail';assert.throws(()=>admitPlan(p,snapshot));});
test('partial skips cannot qualify',()=>{const r={...receipt(),tests:2,skipped:1};assert.equal(assessProbe(r,{subjectSha:sha,testDigest:'c'.repeat(64)}).execution,'UNKNOWN');});
test('unexpected NameError is not a reproduced assertion failure',()=>{const r=receipt(1);r.cases=[{id:'test_x',status:'failed',exception:'NameError',assertions_reached:1}];assert.equal(assessProbe(r,{subjectSha:sha,testDigest:'c'.repeat(64)}).execution,'UNKNOWN');});
test('a pinned, reached lookup assertion with KeyError is a candidate failure, not a setup crash',()=>{
 const r=receipt(1);r.cases[0].exception='KeyError';r.cases[0].exception_in_assertion=true;
 assert.equal(assessProbe(r,{subjectSha:sha,testDigest:'c'.repeat(64)}).execution,'CANDIDATE_FAILURE_REPRODUCED');
 r.cases[0].exception_in_assertion=false;
 assert.equal(assessProbe(r,{subjectSha:sha,testDigest:'c'.repeat(64)}).execution,'UNKNOWN');
});
test('a passing test without a reached assertion is unknown',()=>{const r=receipt();r.cases=[{id:'test_x',status:'passed',exception:null,assertions_reached:0}];assert.equal(assessProbe(r,{subjectSha:sha,testDigest:'c'.repeat(64)}).execution,'UNKNOWN');});
test('generated probes cannot qualify on assertion reach without touching reviewed source',()=>{
 const r=receipt();r.cases[0].subject_lines_reached=0;
 assert.equal(assessProbe(r,{subjectSha:sha,testDigest:'c'.repeat(64),requireReviewedSourceUse:true}).execution,'UNKNOWN');
 r.cases[0].subject_lines_reached=2;
 assert.equal(assessProbe(r,{subjectSha:sha,testDigest:'c'.repeat(64),requireReviewedSourceUse:true}).execution,'PROBE_PASSED');
 r.cases[0].subject_lines_reached=0;
 r.cases[0].subject_import_assertions_reached=1;
 assert.equal(assessProbe(r,{subjectSha:sha,testDigest:'c'.repeat(64),requireReviewedSourceUse:true}).execution,'PROBE_PASSED');
});
test('protected suite may not shrink after repair',()=>{const before=receipt(),after=receipt();before.cases=[{id:'test_a',status:'passed',exception:null,assertions_reached:1}];after.cases=[{id:'test_b',status:'passed',exception:null,assertions_reached:1}];assert.equal(assessRepair({original:receipt(1),fixed:receipt(),protectedBefore:before,protectedAfter:after},{subjectSha:sha,testDigest:'c'.repeat(64)}).status,'UNKNOWN');});

test('a repair can restore an already failing existing test without dropping it',()=>assert.equal(assessRepair({original:receipt(1),fixed:receipt(),protectedBefore:receipt(1),protectedAfter:receipt()},{subjectSha:sha,testDigest:'c'.repeat(64)}).status,'REPAIR_VERIFIED_FOR_FROZEN_TESTS'));

const delta=(base,head,extra={})=>assessProbeDelta({base,head},{baseSha:other,headSha:sha,testDigest:'c'.repeat(64),...extra});
const atBase=(failures=0)=>({...receipt(failures),subject_sha:other});
test('matched original pass and head assertion failure is a bounded head-only candidate',()=>{
 const r=delta(atBase(),receipt(1));
 assert.equal(r.status,'HEAD_ONLY_FAILURE');
 assert.equal(r.meaning,'UNVERIFIED');
 assert.equal(r.permission,'ADVISORY_ONLY');
});
test('same failure on base and head is not a newly introduced PR regression',()=>{
 assert.equal(delta(atBase(1),receipt(1)).status,'SHARED_FAILURE');
});
test('head recovery and both passing remain distinct from new failures',()=>{
 assert.equal(delta(atBase(1),receipt()).status,'BASE_ONLY_FAILURE');
 assert.equal(delta(atBase(),receipt()).status,'BOTH_PASSED');
});
test('unknown base cannot certify head-only regression',()=>{
 const base=atBase();base.errors=1;
 assert.equal(delta(base,receipt(1)).status,'UNKNOWN');
});
test('different collected testcase IDs cannot establish cross-revision difference',()=>{
 const head=receipt(1);head.cases[0].id='test_different';
 assert.equal(delta(atBase(),head).status,'UNKNOWN');
});
test('source, frozen test bytes and distinct revision identities are required',()=>{
 assert.equal(delta(atBase(),receipt(1),{baseSha:sha}).status,'UNKNOWN');
 assert.equal(delta(atBase(),receipt(1),{testFileDigest:'f'.repeat(64)}).status,'UNKNOWN');
 assert.equal(delta(atBase(),receipt(1),{headSha:other}).status,'UNKNOWN');
});
test('no head-only attribution without exercising the reviewed implementation on both revisions',()=>{
 const base=atBase(),head=receipt(1);
 base.cases[0].subject_lines_reached=0;head.cases[0].subject_lines_reached=0;
 assert.equal(delta(base,head,{requireReviewedSourceUse:true}).status,'UNKNOWN');
 base.cases[0].subject_lines_reached=3;head.cases[0].subject_lines_reached=2;
 assert.equal(delta(base,head,{requireReviewedSourceUse:true}).status,'HEAD_ONLY_FAILURE');
 base.cases[0].subject_lines_reached=0;head.cases[0].subject_lines_reached=0;
 base.cases[0].subject_import_assertions_reached=1;head.cases[0].subject_import_assertions_reached=1;
 assert.equal(delta(base,head,{requireReviewedSourceUse:true}).status,'HEAD_ONLY_FAILURE');
});
test('matched protected failures remain visible while a new passing upstream test is separately counted',()=>{
 const base={...atBase(1),test_digest:'d'.repeat(64),cases:[{id:'shared_network',status:'failed',exception:'gaierror',assertions_reached:0}]};
 const head={...receipt(1),test_digest:'e'.repeat(64),tests:2,cases:[
  {id:'shared_network',status:'failed',exception:'gaierror',assertions_reached:0},
  {id:'new_valid_test',status:'passed',exception:null,assertions_reached:0}]};
 const result=compareProtectedSuites({base,head},{baseSha:other,headSha:sha});
 assert.equal(result.status,'MATCHED_NO_NEW_FAILURES');
 assert.equal(result.baseline_failures,1);
 assert.equal(result.head_added_passes,1);
 assert.equal(result.shared_cases,1);
 assert.equal(result.meaning,'UNVERIFIED');
 head.cases[1].status='failed';head.cases[1].exception='AssertionError';head.failures=2;
 assert.equal(compareProtectedSuites({base,head},{baseSha:other,headSha:sha}).status,'HEAD_NEW_FAILURE');
});
test('missing protected cases, altered failure signatures or incomplete native receipts cannot qualify',()=>{
 const base={...atBase(1),cases:[{id:'old',status:'failed',exception:'gaierror'}]};
 const head={...receipt(1),cases:[{id:'old',status:'failed',exception:'gaierror'}]};
 assert.equal(compareProtectedSuites({base,head},{baseSha:other,headSha:sha}).status,'MATCHED_NO_NEW_FAILURES');
 head.cases=[];head.tests=0;head.failures=0;head.exit_code=0;
 assert.equal(compareProtectedSuites({base,head},{baseSha:other,headSha:sha}).status,'UNKNOWN');
 const altered={...receipt(1),cases:[{id:'old',status:'failed',exception:'ConnectionError'}]};
 assert.equal(compareProtectedSuites({base,head:altered},{baseSha:other,headSha:sha}).status,'UNKNOWN');
});
