import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {join} from 'node:path';
import {ARTIN_PIN} from './proofnet-artin-replay-v1.mjs';
import {collectMathSourceEvidence}
  from './math-source-evidence-collector-v1.mjs';

const sha=x=>createHash('sha256').update(x).digest('hex');
const h=x=>x.repeat(64);
const repository='metalogiclabs/mathgraph',pr=12,runId=991;
const head='a'.repeat(40),base='b'.repeat(40),token='scoped-installation-token';
const workflowPath='.github/workflows/mathgraph-check-proofnet-artin-replay-v1.yml';
const workflow='name: Checked source replay\non: workflow_dispatch\n';
const signed='https://proof-results.blob.core.windows.net/results/evidence.zip?sig=opaque';

function crc32(bytes){let c=0xffffffff;for(const b of bytes){c^=b;
  for(let i=0;i<8;i++)c=(c>>>1)^((c&1)?0xedb88320:0);}return(c^0xffffffff)>>>0;}

function zip(files){
  const local=[],central=[];let offset=0;
  for(const [name,content] of files){
    const n=Buffer.from(name),b=Buffer.from(JSON.stringify(content));
    const crc=crc32(b),l=Buffer.alloc(30),c=Buffer.alloc(46);
    l.writeUInt32LE(0x04034b50,0);l.writeUInt16LE(20,4);
    l.writeUInt32LE(crc,14);l.writeUInt32LE(b.length,18);
    l.writeUInt32LE(b.length,22);l.writeUInt16LE(n.length,26);
    c.writeUInt32LE(0x02014b50,0);c.writeUInt16LE(20,4);c.writeUInt16LE(20,6);
    c.writeUInt32LE(crc,16);c.writeUInt32LE(b.length,20);
    c.writeUInt32LE(b.length,24);c.writeUInt16LE(n.length,28);
    c.writeUInt32LE(offset,42);
    local.push(l,n,b);central.push(c,n);offset+=l.length+n.length+b.length;
  }
  const directory=Buffer.concat(central),end=Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50,0);end.writeUInt16LE(files.length,8);
  end.writeUInt16LE(files.length,10);end.writeUInt32LE(directory.length,12);
  end.writeUInt32LE(offset,16);
  return Buffer.concat([...local,directory,end]);
}

const preflight={schema:'mathgraph.proofnet-artin-preflight.v1',
  upstream:{repository:ARTIN_PIN.repository,commit:ARTIN_PIN.commit},
  theorem:ARTIN_PIN.theorem,source_sha256:ARTIN_PIN.sourceSha256,
  claim_sha256:'a908ad4a14106793dec67703b4051fd3587be202fcd94c5778981cab409051a0',
  statement_sha256:ARTIN_PIN.formalSha256,
  gold_archive_sha256:ARTIN_PIN.zipSha256,gold_proof_sha256:ARTIN_PIN.goldSha256,
  requested_lean:ARTIN_PIN.targetLean,requested_mathlib:ARTIN_PIN.targetMathlib,
  artifact_preflight:'PINNED_GOLD_PROOF_IDENTIFIED',native_lean_replay:'NOT_RUN',
  qualified_human_review:'UNKNOWN',intent_verification:'NOT_ESTABLISHED',
  permission:'ADVISORY_ONLY'};
const audit={schema:'mathgraph.artin-axiom-audit.v1',
  theorem:ARTIN_PIN.theorem,
  allowed_axioms:['propext','Classical.choice','Quot.sound'],
  observed_axioms:['propext','Classical.choice','Quot.sound'],
  verdict:'AXIOMS_WITHIN_CLASSICAL_LEAN_ALLOWLIST',source_review:'UNKNOWN',
  intent_verification:'NOT_ESTABLISHED',permission:'ADVISORY_ONLY'};

function fixture(){
  const evidence=zip([['artin-preflight.json',preflight],['artin-axiom-audit.json',audit]]);
  const trusted={repository,pr,headSha:head,workflowPath,workflowSha256:sha(workflow),
    workflowId:700,jobName:'pinned-artin-replay',artifactName:'mathgraph-proofnet-artin-evidence',
    approvedReviewerIds:[],sourceSha256:ARTIN_PIN.sourceSha256,
    claimSha256:preflight.claim_sha256,formalSha256:ARTIN_PIN.formalSha256,
    environmentSha256:h('4')};
  const data={
    [`/pulls/${pr}`]:{number:pr,base:{sha:base,repo:{full_name:repository}},
      head:{sha:head,repo:{full_name:repository}},user:{id:123,type:'User'}},
    [`/actions/runs/${runId}`]:{id:runId,workflow_id:700,head_sha:head,
      path:workflowPath+'@refs/heads/research/fixture',event:'push',
      repository:{id:55,full_name:repository},head_repository:{id:55,full_name:repository},
      actor:{id:65,type:'User'},run_attempt:1,
      run_started_at:'2026-11-01T20:00:00Z',status:'completed',conclusion:'success'},
    [`/actions/runs/${runId}/jobs?per_page=100`]:{total_count:1,jobs:[{
      id:300,run_id:runId,name:'pinned-artin-replay',status:'completed',conclusion:'success',
      steps:[
        {name:'Fetch exactly pinned third-party audited benchmark',conclusion:'success'},
        {name:'Bind exact source, theorem statement and archived proof hashes',conclusion:'success'},
        {name:'Native Lean replay and scoped theorem axiom audit',conclusion:'success'},
        {name:'Save bounded machine evidence (never the gold proof)',conclusion:'success'},
      ]}]},
    [`/actions/runs/${runId}/artifacts?per_page=100`]:{total_count:1,artifacts:[{
      id:7000,name:'mathgraph-proofnet-artin-evidence',expired:false,
      created_at:'2026-11-01T20:05:00Z',size_in_bytes:evidence.length,
      digest:'sha256:'+sha(evidence),
      workflow_run:{id:runId,head_sha:head,repository_id:55}}]},
    [`/contents/${workflowPath}?ref=${head}`]:{encoding:'base64',
      content:Buffer.from(workflow).toString('base64')},
    [`/pulls/${pr}/reviews?per_page=100`]:[],
  };
  const dir=process.env.MATHGRAPH_PROOFNET_FIXTURE_DIR;
  const originalSource=dir?readFileSync(join(dir,ARTIN_PIN.sourcePath)):Buffer.from('unavailable');
  const originalJsonl=dir?readFileSync(join(dir,ARTIN_PIN.jsonlPath)):Buffer.from('{}');
  let source=originalSource,jsonl=originalJsonl;
  let apiPrReads=0,apiRunReads=0;
  const fetcher=async(url,init)=>{
    const prefix='https://api.github.com/repos/'+repository;
    if(url.startsWith(prefix)){
      assert.equal(init.headers.Authorization,'Bearer '+token);
      const path=url.slice(prefix.length);
      if(path===`/pulls/${pr}`)apiPrReads++;
      if(path===`/actions/runs/${runId}`)apiRunReads++;
      if(path==='/actions/artifacts/7000/zip')
        return new Response(null,{status:302,headers:{Location:signed}});
      if(!(path in data))return new Response(null,{status:404});
      return new Response(JSON.stringify(data[path]),{status:200,
        headers:{'content-type':'application/json'}});
    }
    if(url===signed){
      assert.equal(init.headers.Authorization,undefined);
      return new Response(evidence,{status:200});
    }
    const raw=`https://raw.githubusercontent.com/${ARTIN_PIN.repository}/${ARTIN_PIN.commit}/`;
    if(url===raw+ARTIN_PIN.sourcePath)return new Response(source);
    if(url===raw+ARTIN_PIN.jsonlPath)return new Response(jsonl);
    throw Error('unrecognized endpoint');
  };
  const input={repository,pr,runId,token,trusted,fetcher};
  return {input,trusted,data,evidence,fetcher,
    setSource:x=>{source=x;},setJsonl:x=>{jsonl=x;},
    prReads:()=>apiPrReads,runReads:()=>apiRunReads};
}

test('real host+ZIP+upstream produce correlated advisory evidence without a reviewer',async t=>{
  if(!process.env.MATHGRAPH_PROOFNET_FIXTURE_DIR){t.skip('Pinned upstream checkout supplied by CI');return;}
  const x=fixture();
  const result=await collectMathSourceEvidence(x.input);
  assert.equal(result.status,'EVIDENCE_BYTES_CORRELATED');
  assert.equal(result.replay.run_id,991);
  assert.equal(result.replay.artifact_id,7000);
  assert.equal(result.review.status,'UNKNOWN');
  assert.equal(result.artifact.archive_sha256,sha(x.evidence));
  assert.equal(result.upstream.source_sha256,ARTIN_PIN.sourceSha256);
  assert.equal(result.intent_verification,'NOT_ESTABLISHED');
  assert.equal(result.receipt_qualification,'NOT_YET_CONTRACT_BOUND');
  assert.equal(result.permission,'ADVISORY_ONLY');
  assert.equal(result.conclusion,'neutral');
  assert.equal(x.prReads(),4); // two readbacks each observe live PR twice
  assert.equal(x.runReads(),4);
});

test('allowlisted APPROVED declaration may attest review but never mathematically certify meaning',async t=>{
  if(!process.env.MATHGRAPH_PROOFNET_FIXTURE_DIR){t.skip('Pinned upstream checkout supplied by CI');return;}
  const x=fixture();x.trusted.approvedReviewerIds=[47];
  x.data['/pulls/12/reviews?per_page=100']=[{id:900,user:{id:47,type:'User'},
    state:'APPROVED',commit_id:head,submitted_at:'2026-11-01T21:00:00Z',
    body:JSON.stringify({schema:'mathgraph.source-to-formal-review.v1',
      source_sha256:ARTIN_PIN.sourceSha256,claim_sha256:preflight.claim_sha256,
      statement_sha256:ARTIN_PIN.formalSha256,
      environment_sha256:h('4'),verdict:'SOURCE_TO_FORMAL_REVIEWED'})}];
  const r=await collectMathSourceEvidence(x.input);
  assert.equal(r.status,'EVIDENCE_BYTES_CORRELATED');
  assert.equal(r.review.status,'SOURCE_TO_FORMAL_REVIEWED');
  assert.equal(r.intent_verification,'NOT_ESTABLISHED');
  assert.equal(r.permission,'ADVISORY_ONLY');
});

test('unqualified run, wrong trust pins, artifact failure and unpinned source all remain UNKNOWN',async()=>{
  for(const mutate of [
    x=>{x.data['/actions/runs/991'].conclusion='failure';},
    x=>{x.trusted.sourceSha256=h('f');},
    x=>{x.data['/actions/runs/991/artifacts?per_page=100'].artifacts[0].digest='sha256:'+h('c');},
    x=>{x.setSource(Buffer.from('changed upstream'));},
  ]){
    const x=fixture();mutate(x);
    const r=await collectMathSourceEvidence(x.input);
    assert.equal(r.status,'UNKNOWN');
    assert.equal(r.intent_verification,'NOT_ESTABLISHED');
    assert.equal(r.conclusion,'neutral');
    assert.equal(r.permission,'ADVISORY_ONLY');
  }
});

test('changed attempt, artifact digest or head on second readback withdraws result',async t=>{
  if(!process.env.MATHGRAPH_PROOFNET_FIXTURE_DIR){t.skip('Pinned upstream checkout supplied by CI');return;}
  for(const kind of ['attempt','artifact','head']){
    const x=fixture();let run=0,prReads=0,artifactReads=0;
    const baseFetch=x.fetcher;
    x.input.fetcher=async(url,init)=>{
      if(url.endsWith('/actions/runs/991')&&++run>=3&&kind==='attempt'){
        const record=structuredClone(x.data['/actions/runs/991']);
        record.run_attempt=2;
        return new Response(JSON.stringify(record),{status:200});
      }
      if(url.endsWith('/actions/runs/991/artifacts?per_page=100')&&
        ++artifactReads>=2&&kind==='artifact'){
        const record=structuredClone(x.data['/actions/runs/991/artifacts?per_page=100']);
        record.artifacts[0].digest='sha256:'+h('c');
        return new Response(JSON.stringify(record),{status:200});
      }
      if(url.endsWith('/pulls/12')&&++prReads>=3&&kind==='head'){
        const record=structuredClone(x.data['/pulls/12']);record.head.sha='d'.repeat(40);
        return new Response(JSON.stringify(record),{status:200});
      }
      return baseFetch(url,init);
    };
    const r=await collectMathSourceEvidence(x.input);
    assert.equal(r.status,'UNKNOWN',kind);
    assert.equal(r.permission,'ADVISORY_ONLY',kind);
  }
});
