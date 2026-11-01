import test from 'node:test';
import assert from 'node:assert/strict';
import {ARTIN_PIN} from './proofnet-artin-replay-v1.mjs';
import {buildMathEvidenceCheck,publishMathEvidenceCheck} from './math-evidence-check-run-v1.mjs';

const repository='metalogiclabs/mathgraph',headSha='a'.repeat(40);
const hash=c=>c.repeat(64);
function fixture(){
  return {schema:'mathgraph.artin-environment-correlation.v1',
    status:'ENVIRONMENT_AND_REPLAY_CORRELATED',
    subject:{repository,pr:228,head_sha:headSha},
    replay:{status:'PINNED_REPLAY_OBSERVED',run_id:41356752114,
      run_attempt:1,job_id:99,artifact_id:13103253610,
      artifact_digest:'sha256:'+hash('1')},
    environment_artifact_id:13103218833,
    environment_artifact_digest:'sha256:'+hash('2'),
    environment:{status:'ENVIRONMENT_MANIFEST_BYTES_PINNED',
      environment_sha256:hash('3'),manifest_sha256:hash('4'),
      mathlib_revision:'8f9d9cff6bd728b17a24e163c9402775d9e6a365',
      resolved_dependency_count:1,resolved_dependencies:[{name:'mathlib',
        rev:'8f9d9cff6bd728b17a24e163c9402775d9e6a365'}]},
    review:{status:'UNKNOWN'},conclusion:'neutral',
    intent_verification:'NOT_ESTABLISHED',
    permission:'ADVISORY_ONLY',
    receipt_qualification:'NOT_YET_CONTRACT_BOUND'};
}

test('real provenance-shaped observation renders neutral, honest PR Check Run',()=>{
  const payload=buildMathEvidenceCheck(fixture(),{repository,headSha});
  assert.equal(payload.status,'completed');
  assert.equal(payload.conclusion,'neutral');
  assert.equal(payload.head_sha,headSha);
  assert.match(payload.name,/mathematical evidence/);
  assert.match(payload.output.title,/review pending/);
  assert.match(payload.output.summary,/meaning.*UNKNOWN|UNKNOWN.*review/);
  assert.match(payload.output.summary,/NOT ESTABLISHED/);
  assert.match(payload.output.summary,/NOT_YET_CONTRACT_BOUND/);
  assert.match(payload.output.summary,/not a mathematical equivalence certificate/i);
  assert.match(payload.output.summary,/41356752114/);
  assert.match(payload.output.summary,new RegExp(ARTIN_PIN.formalSha256));
  assert.doesNotMatch(payload.output.summary,/semantic fidelity: verified|merge approved/i);
});

test('an explicit review is an attestation, never formal semantic equivalence',()=>{
  const x=fixture();
  x.review={status:'SOURCE_TO_FORMAL_REVIEWED',review_id:90,reviewer_id:50,
    evidence_scope:'INDEPENDENT_REVIEW_ATTESTATION_ONLY'};
  const p=buildMathEvidenceCheck(x,{repository,headSha});
  assert.match(p.output.title,/review attested/);
  assert.match(p.output.summary,/NOT ESTABLISHED/);
  assert.equal(p.conclusion,'neutral');
  assert.equal(p.status,'completed');
});

test('unqualified proof, environment, stale head, unknown authority and forged status fail closed',()=>{
  const changes=[
    x=>{x.status='UNKNOWN';},
    x=>{x.subject.head_sha='b'.repeat(40);},
    x=>{x.subject.repository='other/repo';},
    x=>{x.replay.status='UNKNOWN';},
    x=>{x.replay.run_attempt=2;},
    x=>{x.replay.artifact_id=x.environment_artifact_id;},
    x=>{x.replay.artifact_digest='invalid';},
    x=>{x.environment.status='UNKNOWN';},
    x=>{x.environment.environment_sha256='not a hash';},
    x=>{x.environment.resolved_dependency_count=0;},
    x=>{x.environment.resolved_dependencies=[];},
    x=>{x.environment.mathlib_revision='c'.repeat(40);},
    x=>{x.receipt_qualification='CERTIFIED';},
    x=>{x.intent_verification='ESTABLISHED';},
    x=>{x.permission='MERGE_ALLOWED';},
    x=>{x.conclusion='success';},
    x=>{x.review={status:'SOURCE_TO_FORMAL_REVIEWED'};},
    x=>{x.review={status:'APPROVED'};},
  ];
  for(const change of changes){
    const x=fixture();change(x);
    assert.throws(()=>buildMathEvidenceCheck(x,{repository,headSha}),
      /UNQUALIFIED_MATH_EVIDENCE|UNQUALIFIED_HUMAN_REVIEW/);
  }
});

test('dry-run is default and does not need a GitHub token',async()=>{
  const result=await publishMathEvidenceCheck(fixture(),{repository,headSha,
    fetcher:async()=>{throw Error('network forbidden in preview');}});
  assert.equal(result.mode,'PREVIEW');
  assert.equal(result.request.conclusion,'neutral');
});

test('opt-in publisher checks exact live PR head before any GitHub write',async()=>{
  const calls=[];
  const fetcher=async(url,options)=>{
    calls.push({url,method:options.method,authorization:options.headers.Authorization,
      body:options.body});
    if(options.method==='GET')return {ok:true,json:async()=>({
      number:228,head:{sha:headSha,repo:{full_name:repository}},
      base:{repo:{full_name:repository}}})};
    const b=JSON.parse(options.body);
    return {ok:true,json:async()=>({
      id:1000,head_sha:headSha,name:b.name,conclusion:b.conclusion,
      html_url:'https://github.com/metalogiclabs/mathgraph/runs/1000'})};
  };
  const result=await publishMathEvidenceCheck(fixture(),{
    repository,headSha,token:'scoped-test-github-app-token',fetcher,dryRun:false});
  assert.equal(result.mode,'PUBLISHED');
  assert.equal(calls.length,2);
  assert.equal(calls[0].method,'GET');
  assert.equal(calls[1].method,'POST');
  assert.equal(calls[1].authorization,'Bearer scoped-test-github-app-token');
  const posted=JSON.parse(calls[1].body);
  assert.equal(posted.conclusion,'neutral');
  assert.equal(posted.head_sha,headSha);
  assert.equal(posted.output.summary.includes('NOT ESTABLISHED'),true);
});

test('stale HEAD and non-allowlisted repository prevent POST',async()=>{
  const calls=[];
  const fetcher=async(url,options)=>{
    calls.push(options.method);
    return {ok:true,json:async()=>({
      number:228,head:{sha:'b'.repeat(40),repo:{full_name:repository}},
      base:{repo:{full_name:repository}}})};
  };
  await assert.rejects(()=>publishMathEvidenceCheck(fixture(),{
    repository,headSha,token:'scoped-test-github-app-token',fetcher,dryRun:false}),
    /GITHUB_HEAD_MOVED/);
  assert.deepEqual(calls,['GET']);
  assert.throws(()=>buildMathEvidenceCheck(fixture(),{
    repository:'another/repo',headSha}),/UNQUALIFIED_MATH_EVIDENCE/);
});
