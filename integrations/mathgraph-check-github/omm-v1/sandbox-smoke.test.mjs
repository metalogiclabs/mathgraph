import test from 'node:test';
import assert from 'node:assert/strict';
import {qualifySandboxSmoke,probeSandboxBoundary} from './sandbox-smoke.mjs';

const ok={status:'LEAN_ACCEPTED',exit_code:0,source_sha256:'a'.repeat(64)};
const bad={status:'LEAN_REJECTED_THIS_REPLAY',exit_code:1,source_sha256:'b'.repeat(64)};

test('two immutable native controls plus actual isolation probe form bounded smoke evidence',async()=>{
 const sources=[];
 const result=await qualifySandboxSmoke({native:async({source})=>{sources.push(source);return sources.length===1?ok:bad;},
  probe:async()=>({read_only:true,no_default_route:true,uid:65534})});
 assert.equal(result.status,'SANDBOX_SMOKE_OBSERVED');
 assert.equal(result.candidate_compilation,'OBSERVED');
 assert.equal(result.negative_control,'REJECTED_THIS_REPLAY');
 assert.equal(result.intent_fidelity,'UNKNOWN');
 assert.equal(result.community_execution_permission,'DENIED');
 assert.equal(sources.length,2);
 assert.match(sources[1],/False/);
});

test('missing runtime, wrong native outcomes and isolation guard failures refuse promotion',async()=>{
 for(const [positive,negative,probe] of [
   [bad,bad,{read_only:true,no_default_route:true,uid:65534}],
   [ok,ok,{read_only:true,no_default_route:true,uid:65534}],
   [ok,bad,{read_only:false,no_default_route:true,uid:65534}],
   [ok,bad,{read_only:true,no_default_route:false,uid:65534}],
   [ok,bad,{read_only:true,no_default_route:true,uid:0}]
 ]){
  let count=0;
  await assert.rejects(qualifySandboxSmoke({native:async()=>count++===0?positive:negative,
    probe:async()=>probe}),/SANDBOX_SMOKE_FAILED/);
 }
});

test('filesystem/network guard reaps its exact container after its shell probe',async()=>{
 const calls=[];
 const observed=await probeSandboxBoundary({run:async(cmd,args)=>{
  calls.push({cmd,args});
  if(args[0]==='run')return {stdout:'OMM_BOUNDARY_OBSERVED\n',stderr:''};
  return {stdout:'',stderr:''};
 }});
 assert.deepEqual(observed,{read_only:true,no_default_route:true,uid:65534});
 assert.equal(calls.length,2);
 assert.deepEqual(calls[1].args,['rm','-f',calls[0].args[calls[0].args.indexOf('--name')+1]]);
});
