import test from 'node:test';
import assert from 'node:assert/strict';
import {githubSnapshot} from './authenticated-cycle-v1.mjs';

const repo = 'metalogiclabs/mathgraph';
const a = 'a'.repeat(40);
const b = 'b'.repeat(40);
const c = 'c'.repeat(40);
const options = {repository: repo, pr: 195, token: 'local-test-token-only'};

function githubFixture({initialHead=b, nextHead=b, initialBase=a, nextBase=a}={}) {
  let reads=0;
  const fetcher=async url=>{
    let json;
    if(url.endsWith('/pulls/195')){
      reads++;
      json={base:{sha:reads===1?initialBase:nextBase,repo:{full_name:repo}},
        head:{sha:reads===1?initialHead:nextHead,repo:{full_name:repo}}};
    }else if(url.includes('/commits/'+initialHead+'/check-runs?')){
      json={total_count:1,check_runs:[{id:44,name:'Independent build',
        head_sha:initialHead,status:'completed',conclusion:'success',
        started_at:'2026-10-29T00:00:00Z',app:{slug:'github-actions'}}]};
    }else throw Error('Unexpected source query: '+url);
    return {ok:true,json:async()=>json};
  };
  return {fetcher,readCount:()=>reads};
}

test('a moving PR head cannot be reported as stable after verification readback',async()=>{
  const fixture=githubFixture({initialHead:b,nextHead:c});
  await assert.rejects(githubSnapshot({...options,fetcher:fixture.fetcher}),
    /PR_SOURCE_MOVED_DURING_CHECKS/);
  assert.equal(fixture.readCount(),2);
});

test('a moving PR base invalidates a source-bound readback as well',async()=>{
  const fixture=githubFixture({initialHead:b,nextHead:b,initialBase:a,nextBase:c});
  await assert.rejects(githubSnapshot({...options,fetcher:fixture.fetcher}),
    /PR_SOURCE_MOVED_DURING_CHECKS/);
  assert.equal(fixture.readCount(),2);
});

test('stable source after two reads still yields bounded observation',async()=>{
  const fixture=githubFixture();
  const result=await githubSnapshot({...options,fetcher:fixture.fetcher});
  assert.equal(fixture.readCount(),2);
  assert.equal(result.result.status,'OBSERVED');
  assert.equal(result.result.permission,'ADVISORY_ONLY');
  assert.equal(result.result.subject.head_sha,b);
});
