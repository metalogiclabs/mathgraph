import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildOmmIntakeCheck, reconcileOwnedOmmLifecycle, admitOmmLifecyclePush
} from './lifecycle-check.mjs';

const repo='metalogiclabs/mathgraph';
const branch='feature/check-omm-claim-bridge-v1-20261105';
const a='a'.repeat(40),b='b'.repeat(40),c='c'.repeat(40);
const name='MathGraph Check / OMM intake (advisory)';

function stateApi({live=a,foreign=false,moveAt=Infinity,full=true}={}){
  const state={live,checks:new Map(),calls:[],next:701,prReads:0};
  const root='/repos/'+repo;
  const api=async(path,{method='GET',body}={})=>{
    state.calls.push({path,method,body});
    if(path===root+'/pulls/270'){
      state.prReads++;
      if(state.prReads>=moveAt)state.live=c;
      return {number:270,state:'open',head:{sha:state.live,ref:branch,repo:{full_name:repo}},base:{repo:{full_name:repo}}};
    }
    const found=path.match(/\/commits\/([a-f0-9]{40})\/check-runs\?/);
    if(found){
      const list=state.checks.get(found[1])??[];
      if(foreign&&found[1]===state.live)return {total_count:1,check_runs:[{...list[0],id:800,app:{id:111},name,external_id:`mathgraph-omm-intake-v1:${repo}:270:${state.live}`}]};
      return {total_count:full?list.length:list.length+1,check_runs:list};
    }
    if(path===root+'/check-runs'&&method==='POST'){
      const r={...body,id:state.next++,app:{id:5308912}};
      state.checks.set(body.head_sha,[...(state.checks.get(body.head_sha)??[]),r]);return r;
    }
    const checkId=path.match(/\/check-runs\/(\d+)$/);
    if(checkId){
      const entries=[...state.checks.values()].flat();const check=entries.find(x=>x.id===Number(checkId[1]));
      if(!check)throw Error('CHECK_NOT_FOUND');
      if(method==='PATCH'){Object.assign(check,body);return check;}
      return check;
    }
    throw Error('UNEXPECTED_API_'+method+':'+path);
  };
  return {state,api};
}

const runUrl='https://github.com/metalogiclabs/mathgraph/actions/runs/41916425178';

test('owned exact-head UNKNOWN check is created; head change explicitly supersedes old check',async()=>{
  const {state,api}=stateApi();
  const first=await reconcileOwnedOmmLifecycle({number:270,head:a,before:c,runUrl,api,write:true});
  assert.equal(first.current.mode,'CREATED');
  assert.equal(first.previous.mode,'ABSENT');
  assert.equal(state.checks.get(a)[0].app.id,5308912);
  assert.equal(state.checks.get(a)[0].conclusion,'neutral');
  assert.match(state.checks.get(a)[0].output.summary,/Mathematical intent \| UNKNOWN/);
  state.live=b;
  const second=await reconcileOwnedOmmLifecycle({number:270,head:b,before:a,runUrl,api,write:true});
  assert.equal(second.previous.mode,'WITHDRAWN');
  assert.equal(second.current.mode,'CREATED');
  assert.match(state.checks.get(a)[0].output.summary,/SUPERSEDED/);
  assert.match(state.checks.get(a)[0].output.summary,new RegExp(b));
  assert.equal(state.checks.get(b)[0].conclusion,'neutral');
  const rerun=await reconcileOwnedOmmLifecycle({number:270,head:b,before:a,runUrl,api,write:true});
  assert.equal(rerun.previous.mode,'ALREADY_WITHDRAWN');
  assert.equal(rerun.current.mode,'UNCHANGED');
  assert.equal(state.checks.get(b).length,1);
});

test('changed live PR refuses to publish a Check for an obsolete SHA',async()=>{
  const {state,api}=stateApi({live:b});
  await assert.rejects(reconcileOwnedOmmLifecycle({number:270,head:a,before:c,runUrl,api,write:true}),/STALE_PR_HEAD/);
  assert.equal(state.calls.some(x=>x.method!=='GET'),false);
});

test('a foreign App with the same Check name cannot be overwritten',async()=>{
  const {state,api}=stateApi({foreign:true});
  await assert.rejects(reconcileOwnedOmmLifecycle({number:270,head:a,before:c,runUrl,api,write:true}),/FOREIGN_APP_CHECK_NAME_COLLISION/);
  assert.equal(state.calls.some(x=>x.method!=='GET'),false);
});

test('incomplete check-list visibility refuses publication',async()=>{
  const {state,api}=stateApi({full:false});
  await assert.rejects(reconcileOwnedOmmLifecycle({number:270,head:a,before:c,runUrl,api,write:true}),/CHECK_VISIBILITY_INCOMPLETE/);
  assert.equal(state.calls.some(x=>x.method!=='GET'),false);
});

test('head moving after preflight cannot receive a new Check',async()=>{
  const {state,api}=stateApi({moveAt:2});
  await assert.rejects(reconcileOwnedOmmLifecycle({number:270,head:a,before:c,runUrl,api,write:true}),/STALE_PR_HEAD/);
  assert.equal(state.calls.some(x=>x.method==='POST'),false);
});

test('wrong owned PR and attempts to encode a passing claim are rejected',async()=>{
  const {api}=stateApi();
  await assert.rejects(reconcileOwnedOmmLifecycle({number:239,head:a,before:c,runUrl,api,write:true}),/OWNED_LIFECYCLE_ONLY/);
  const p=buildOmmIntakeCheck({head:a,runUrl});
  assert.equal(p.status,'completed');assert.equal(p.conclusion,'neutral');
  assert.equal(p.external_id,`mathgraph-omm-intake-v1:${repo}:270:${a}`);
  assert.doesNotMatch(p.output.summary,/WARRANTED/);
});

test('CLI event admission requires exact owned push source and actor',()=>{
  const event={ref:'refs/heads/'+branch,before:a,after:b,repository:{full_name:repo},sender:{id:32909488}};
  const env={GITHUB_EVENT_NAME:'push',GITHUB_REPOSITORY:repo,GITHUB_REF:event.ref,GITHUB_SHA:b,GITHUB_ACTOR_ID:'32909488',GITHUB_RUN_ID:'41916425178'};
  assert.deepEqual(admitOmmLifecyclePush(event,env),{head:b,before:a,runId:'41916425178'});
  assert.throws(()=>admitOmmLifecyclePush({...event,sender:{id:999}},env),/OWNED_EVENT_REQUIRED/);
  assert.throws(()=>admitOmmLifecyclePush(event,{...env,GITHUB_ACTOR_ID:'999'}),/OWNED_EVENT_REQUIRED/);
  assert.throws(()=>admitOmmLifecyclePush(event,{...env,GITHUB_SHA:c}),/OWNED_EVENT_REQUIRED/);
});
