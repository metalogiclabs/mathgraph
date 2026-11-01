import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {observeGitHubMathSource} from './math-source-github-host-v1.mjs';

const g=x=>x.repeat(40);
const h=x=>x.repeat(64);
const sha=x=>createHash('sha256').update(x).digest('hex');
const repository='metalogiclabs/mathgraph',pr=12,runId=991;
const workflowPath='.github/workflows/mathgraph-check-proofnet-artin-replay-v1.yml';
const workflow='name: Qualified replay\non: workflow_dispatch\n';
const head=g('a'),base=g('b');

function fixture(){
  const trusted={repository,pr,headSha:head,workflowPath,workflowSha256:sha(workflow),
    workflowId:700,jobName:'pinned-artin-replay',artifactName:'mathgraph-proofnet-artin-evidence',
    approvedReviewerIds:[47],sourceSha256:h('1'),claimSha256:h('2'),
    formalSha256:h('3'),environmentSha256:h('4')};
  const declaration={schema:'mathgraph.source-to-formal-review.v1',
    source_sha256:h('1'),claim_sha256:h('2'),statement_sha256:h('3'),
    environment_sha256:h('4'),verdict:'SOURCE_TO_FORMAL_REVIEWED'};
  const data={
    [`/pulls/${pr}`]:{number:pr,base:{sha:base,repo:{full_name:repository}},
      head:{sha:head,repo:{full_name:repository}},user:{id:123,type:'User'}},
    [`/actions/runs/${runId}`]:{id:runId,workflow_id:700,head_sha:head,
      path:workflowPath+'@refs/heads/research/fixture',event:'push',
      repository:{id:55,full_name:repository},head_repository:{id:55,full_name:repository},
      actor:{id:65,type:'User'},
      run_attempt:1,run_started_at:'2026-11-01T20:00:00Z',
      status:'completed',conclusion:'success'},
    [`/actions/runs/${runId}/jobs?per_page=100`]:{total_count:1,jobs:[{
      id:300,run_id:runId,name:'pinned-artin-replay',status:'completed',conclusion:'success',
      steps:[{name:'Fetch exactly pinned third-party audited benchmark',conclusion:'success'},
        {name:'Bind exact source, theorem statement and archived proof hashes',conclusion:'success'},
        {name:'Native Lean replay and scoped theorem axiom audit',conclusion:'success'},
        {name:'Save bounded machine evidence (never the gold proof)',conclusion:'success'}]}]},
    [`/actions/runs/${runId}/artifacts?per_page=100`]:{total_count:1,artifacts:[{
      id:7000,name:'mathgraph-proofnet-artin-evidence',expired:false,
      created_at:'2026-11-01T20:05:00Z',size_in_bytes:1200,digest:'sha256:'+h('c'),
      workflow_run:{id:runId,head_sha:head,repository_id:55}}]},
    [`/contents/${workflowPath}?ref=${head}`]:{encoding:'base64',
      content:Buffer.from(workflow).toString('base64')},
    [`/pulls/${pr}/reviews?per_page=100`]:[{id:900,user:{id:47,login:'reviewer',type:'User'},
      state:'APPROVED',commit_id:head,submitted_at:'2026-11-01T21:00:00Z',
      body:JSON.stringify(declaration)}],
  };
  const fetcher=async(url,init)=>{
    const prefix='https://api.github.com/repos/'+repository;
    assert.ok(url.startsWith(prefix));
    assert.equal(init.headers.Authorization,'Bearer scoped-token-for-test');
    const path=url.slice(prefix.length);
    if(!(path in data))return {ok:false,status:404};
    return {ok:true,json:async()=>structuredClone(data[path])};
  };
  const input={repository,pr,runId,token:'scoped-token-for-test',trusted,fetcher};
  return {data,trusted,declaration,input};
}

test('a pinned GitHub run and separate explicit human review produce bounded observations only',async()=>{
  const {input}=fixture();
  const r=await observeGitHubMathSource(input);
  assert.equal(r.status,'OBSERVED');
  assert.equal(r.replay.status,'PINNED_REPLAY_OBSERVED');
  assert.equal(r.review.status,'SOURCE_TO_FORMAL_REVIEWED');
  assert.equal(r.replay.run_id,991);
  assert.equal(r.review.reviewer_id,47);
  assert.equal(r.permission,'ADVISORY_ONLY');
  assert.equal(r.intent_verification,'NOT_ESTABLISHED');
  assert.equal(r.conclusion,'neutral');
  assert.equal(r.receipt_qualification,'NOT_YET_CONTRACT_BOUND');
});

test('changed PR head, run head or repository cannot inherit the replay',async()=>{
  for(const mutate of [
    x=>{x.data['/pulls/12'].head.sha=g('d');},
    x=>{x.data['/actions/runs/991'].head_sha=g('d');},
    x=>{x.data['/actions/runs/991'].repository.full_name='other/repo';},
    x=>{x.data['/actions/runs/991'].head_repository.id=90;},
    x=>{x.data['/actions/runs/991'].workflow_id=701;},
    x=>{x.data['/actions/runs/991'].path='untrusted.yml@refs/heads/main';},
  ]){
    const x=fixture();mutate(x);
    const r=await observeGitHubMathSource(x.input);
    assert.equal(r.replay.status,'UNKNOWN');
    assert.equal(r.status,'UNKNOWN');
  }
});

test('PR-authored workflow changes, incomplete CI, stale artifact, and duplicated evidence fail closed',async()=>{
  for(const mutate of [
    x=>{x.data[`/contents/${workflowPath}?ref=${head}`].content=Buffer.from('evil').toString('base64');},
    x=>{x.data['/actions/runs/991'].conclusion='failure';},
    x=>{x.data['/actions/runs/991'].status='in_progress';},
    x=>{x.data['/actions/runs/991/jobs?per_page=100'].jobs[0].steps[2].conclusion='failure';},
    x=>{x.data['/actions/runs/991/jobs?per_page=100'].jobs.push(
      structuredClone(x.data['/actions/runs/991/jobs?per_page=100'].jobs[0]));
      x.data['/actions/runs/991/jobs?per_page=100'].total_count=2;},
    x=>{x.data['/actions/runs/991/artifacts?per_page=100'].artifacts[0].expired=true;},
    x=>{x.data['/actions/runs/991/artifacts?per_page=100'].artifacts[0].created_at='2026-11-01T19:00:00Z';},
    x=>{x.data['/actions/runs/991/artifacts?per_page=100'].artifacts[0].workflow_run.head_sha=g('f');},
    x=>{x.data['/actions/runs/991/artifacts?per_page=100'].total_count=2;},
  ]){
    const x=fixture();mutate(x);
    const r=await observeGitHubMathSource(x.input);
    assert.equal(r.replay.status,'UNKNOWN');
    assert.equal(r.status,'UNKNOWN');
  }
});

test('ordinary APPROVED review, PR author, bot, unapproved user, stale head and changed claims do not review meaning',async()=>{
  for(const mutate of [
    x=>{x.data['/pulls/12/reviews?per_page=100'][0].body='LGTM';},
    x=>{x.data['/pulls/12/reviews?per_page=100'][0].user.id=123;},
    x=>{x.data['/pulls/12/reviews?per_page=100'][0].user.id=65;
      x.trusted.approvedReviewerIds=[65];},
    x=>{x.data['/pulls/12/reviews?per_page=100'][0].user.type='Bot';},
    x=>{x.data['/pulls/12/reviews?per_page=100'][0].user.id=71;},
    x=>{x.data['/pulls/12/reviews?per_page=100'][0].commit_id=g('d');},
    x=>{x.declaration.statement_sha256=h('7');
      x.data['/pulls/12/reviews?per_page=100'][0].body=JSON.stringify(x.declaration);},
    x=>{x.data['/pulls/12/reviews?per_page=100'][0].state='COMMENTED';},
  ]){
    const x=fixture();mutate(x);
    const r=await observeGitHubMathSource(x.input);
    assert.equal(r.review.status,'UNKNOWN');
    assert.equal(r.status,'UNKNOWN');
  }
});

test('later dismissal or changes request withdraws the same human review',async()=>{
  for(const state of ['DISMISSED','CHANGES_REQUESTED']){
    const x=fixture();x.data['/pulls/12/reviews?per_page=100'].push({
      id:901,user:{id:47,login:'reviewer',type:'User'},state,commit_id:head,
      submitted_at:'2026-11-01T22:00:00Z',body:'Review changed'});
    const r=await observeGitHubMathSource(x.input);
    assert.equal(r.review.status,'UNKNOWN');
  }
});

test('GitHub API denial and incomplete paginated reviews never become endorsements',async()=>{
  const a=fixture();a.data['/pulls/12/reviews?per_page=100']={message:'not a page'};
  assert.equal((await observeGitHubMathSource(a.input)).review.status,'UNKNOWN');
  const b=fixture();b.input.fetcher=async()=>({ok:false,status:403});
  const r=await observeGitHubMathSource(b.input);
  assert.equal(r.status,'UNKNOWN');
  assert.equal(r.review.status,'UNKNOWN');
  assert.equal(r.replay.status,'UNKNOWN');
});

test('a PR head change during the readback withdraws all observations',async()=>{
  const x=fixture();const read=x.input.fetcher;let count=0;
  x.input.fetcher=async(url,init)=>{
    if(url.endsWith('/pulls/12')&&++count===2)return {ok:true,json:async()=>({
      ...x.data['/pulls/12'],head:{...x.data['/pulls/12'].head,sha:g('d')}})};
    return read(url,init);
  };
  const r=await observeGitHubMathSource(x.input);
  assert.equal(r.status,'UNKNOWN');
  assert.equal(r.replay.status,'UNKNOWN');
  assert.equal(r.review.status,'UNKNOWN');
});

test('a new rerun attempt during the readback withdraws replay evidence',async()=>{
  const x=fixture();const read=x.input.fetcher;let count=0;
  x.input.fetcher=async(url,init)=>{
    if(url.endsWith('/actions/runs/991')&&++count===2)return {ok:true,json:async()=>({
      ...x.data['/actions/runs/991'],run_attempt:2,status:'in_progress',conclusion:null})};
    return read(url,init);
  };
  const r=await observeGitHubMathSource(x.input);
  assert.equal(r.status,'UNKNOWN');
  assert.equal(r.replay.status,'UNKNOWN');
});
