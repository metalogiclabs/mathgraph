import test from 'node:test';
import assert from 'node:assert/strict';
import {ARTIN_PIN} from './proofnet-artin-replay-v1.mjs';
import {fetchPinnedArtifactZip,fetchPinnedArtinUpstream}
  from './math-source-evidence-fetch-v1.mjs';

const REPO='metalogiclabs/mathgraph';
const ID=13098749856;
const API=`https://api.github.com/repos/${REPO}/actions/artifacts/${ID}/zip`;
const SIGNED='https://proof-results.blob.core.windows.net/results/evidence.zip?sig=opaque';
const ZIP=Buffer.from('PK\x03\x04example binary ZIP');

test('artifact ZIP comes from fixed GitHub API and one separate uncredentialed HTTPS hop',async()=>{
  const calls=[];
  const fetcher=async(url,init)=>{
    calls.push({url,init});
    if(url===API)return new Response(null,{status:302,headers:{Location:SIGNED}});
    if(url===SIGNED)return new Response(ZIP,{status:200,headers:{'content-length':ZIP.length}});
    throw Error('unexpected URL');
  };
  const actual=await fetchPinnedArtifactZip({repository:REPO,artifactId:ID,
    token:'scoped-installation-token',fetcher});
  assert.deepEqual(actual,ZIP);
  assert.equal(calls.length,2);
  assert.equal(calls[0].url,API);
  assert.equal(calls[0].init.headers.Authorization,'Bearer scoped-installation-token');
  assert.equal(calls[0].init.redirect,'manual');
  assert.equal(calls[1].url,SIGNED);
  assert.equal(calls[1].init.headers?.Authorization,undefined);
  assert.equal(calls[1].init.redirect,'error');
});

test('artifact downloader disallows off-domain redirects, insecure URLs and double redirect',async()=>{
  for(const location of ['http://proof-results.blob.core.windows.net/file',
    'https://evil.example/steal','http://127.0.0.1/','https://proof-results.blob.core.windows.net.evil.example/']){
    let count=0;
    const fetcher=async()=>{count++;return new Response(null,{status:302,headers:{Location:location}});};
    await assert.rejects(fetchPinnedArtifactZip({repository:REPO,artifactId:ID,
      token:'scoped-installation-token',fetcher}),/UNTRUSTED_ARTIFACT_REDIRECT/);
    assert.equal(count,1);
  }
  const double=async(url)=>new Response(null,{status:302,headers:{Location:SIGNED}});
  await assert.rejects(fetchPinnedArtifactZip({repository:REPO,artifactId:ID,
    token:'scoped-installation-token',fetcher:double}),/ARTIFACT_DOWNLOAD_FAILED/);
});

test('artifact stream is actually bounded even when Content-Length is absent or dishonest',async()=>{
  for(const declared of [undefined,'1','999999999']){
    const fetcher=async(url)=>url===API?
      new Response(null,{status:302,headers:{Location:SIGNED}}):
      new Response(new Uint8Array(2*1024*1024+1),{
        status:200,headers:declared?{'content-length':declared}:undefined});
    await assert.rejects(fetchPinnedArtifactZip({repository:REPO,artifactId:ID,
      token:'scoped-installation-token',fetcher}),/ARTIFACT_DOWNLOAD_TOO_LARGE/);
  }
});

test('an oversized artifact stream is cancelled before returning failure',async()=>{
  let cancelled=false;
  const stream=new ReadableStream({
    start(controller){controller.enqueue(new Uint8Array(2*1024*1024+1));},
    cancel(){cancelled=true;},
  });
  const fetcher=async url=>url===API?
    new Response(null,{status:302,headers:{Location:SIGNED}}):
    new Response(stream,{status:200});
  await assert.rejects(fetchPinnedArtifactZip({repository:REPO,artifactId:ID,
    token:'scoped-installation-token',fetcher}),/ARTIFACT_DOWNLOAD_TOO_LARGE/);
  assert.equal(cancelled,true);
});

test('malformed artifact scope and GitHub 403 never cause second-hop download',async()=>{
  for(const bad of [{repository:'other/repo?x=1'},
    {artifactId:0},{token:''}]){
    let calls=0;
    await assert.rejects(fetchPinnedArtifactZip({repository:REPO,artifactId:ID,
      token:'scoped-installation-token',fetcher:async()=>{calls++;throw Error('network');},...bad}),
    /INVALID_ARTIFACT_DOWNLOAD_SCOPE/);
    assert.equal(calls,0);
  }
  let calls=0;
  await assert.rejects(fetchPinnedArtifactZip({repository:REPO,artifactId:ID,
    token:'scoped-installation-token',fetcher:async()=>{calls++;return new Response(null,{status:403});}}),
  /ARTIFACT_DOWNLOAD_FAILED/);
  assert.equal(calls,1);
});

test('upstream snapshot reads exactly the two immutable public commit paths, without bearer',async()=>{
  const paths=[ARTIN_PIN.sourcePath,ARTIN_PIN.jsonlPath];
  const calls=[];
  const fetcher=async(url,init)=>{
    calls.push({url,init});
    if(url.endsWith('/'+paths[0]))return new Response('theorem original');
    if(url.endsWith('/'+paths[1]))return new Response('original jsonl');
    throw Error('unexpected URL');
  };
  const x=await fetchPinnedArtinUpstream({fetcher});
  assert.equal(x.sourceBytes.toString(),'theorem original');
  assert.equal(x.jsonlBytes.toString(),'original jsonl');
  assert.equal(x.observedCommit,ARTIN_PIN.commit);
  assert.deepEqual(calls.map(c=>c.url),paths.map(p=>
    `https://raw.githubusercontent.com/${ARTIN_PIN.repository}/${ARTIN_PIN.commit}/${p}`));
  assert.ok(calls.every(c=>c.init.redirect==='error' &&
    c.init.headers?.Authorization===undefined));
});

test('upstream 404, redirect and oversize body fail closed',async()=>{
  for(const response of [
    new Response(null,{status:404}),
    new Response(null,{status:302,headers:{Location:'https://evil.example/'}}),
    new Response(new Uint8Array(65537),{status:200}),
  ]){
    await assert.rejects(fetchPinnedArtinUpstream({fetcher:async()=>response}),
      /UPSTREAM_SOURCE_FETCH_FAILED|UPSTREAM_SOURCE_TOO_LARGE/);
  }
});
