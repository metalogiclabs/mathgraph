import test from 'node:test';
import assert from 'node:assert/strict';
import {parseOwnedOmmOptin,admitOwnedOmmSource} from './optin-admission.mjs';

const repo='metalogiclabs/mathgraph';
const head='2f6aaba0d71f1c0b4c0db58618a8981ccd59dc17';
const base='dfd87d1e921953badedcfae21ade76bb38f5c04a';
const userId=32909488;
const command='@MathGraph -claim';
const event=()=>({action:'created',repository:{full_name:repo},sender:{id:userId,type:'User'},
 comment:{id:555,body:command,user:{id:userId,type:'User'},created_at:'2026-11-05T00:00:00Z',updated_at:'2026-11-05T00:00:00Z'},
 issue:{number:239,pull_request:{url:'https://api.github.com/repos/'+repo+'/pulls/239'}}});
const env=()=>({GITHUB_EVENT_NAME:'issue_comment',GITHUB_REPOSITORY:repo,GITHUB_RUN_ATTEMPT:'1'});
const qualified=()=>({request:{schema:'mathgraph.omm.request.v1',repository:repo,number:239,command:'check',head_sha:head,
  base_sha:base,candidate_source_sha256:'e45efb73729fc98e45e66d216e792e70f67f8c43d4c12cbb753ac410b950e4d9'}});

function client({moved=false,edited=false,foreign=false}={}){
 const calls=[],state={count:0};
 const api=async path=>{
  calls.push(path);
  if(path==='/repos/'+repo+'/issues/comments/555')return {...event().comment,
   body:edited?'@MathGraph -fix':command,issue_url:'https://api.github.com/repos/'+repo+'/issues/239'};
  if(path==='/repos/'+repo+'/pulls/239'){
   state.count++;
   return {number:239,state:'open',head:{sha:moved&&state.count>1?'0'.repeat(40):head,
    repo:{full_name:foreign?'someone/mathgraph':repo}},base:{sha:base,repo:{full_name:repo}}};
  }
  throw Error('UNEXPECTED_'+path);
 };
 return {api,calls};
}

test('exact owner-only comment is a request, not an evidence warrant',async()=>{
 const {api}=client(),e=event();
 const parsed=parseOwnedOmmOptin(e,env());
 assert.deepEqual(parsed,{number:239,commentId:555});
 const accepted=await admitOwnedOmmSource({event:e,env:env(),api,
  qualifyRegistered:async({number})=>{assert.equal(number,239);return qualified();}});
 assert.equal(accepted.status,'SOURCE_ADMITTED_ONLY');
 assert.equal(accepted.original_target,'UNKNOWN');
 assert.equal(accepted.evidence_warrant,'UNKNOWN');
 assert.equal(accepted.intent_fidelity,'UNKNOWN');
 assert.equal(accepted.repair_permission,'DENIED');
 assert.equal(accepted.head_sha,head);
});

test('not an owner, changed command, unsupported event and edited comment are refused',async()=>{
 const e=event();
 assert.equal(parseOwnedOmmOptin({...e,sender:{id:1,type:'User'}},env()),null);
 assert.equal(parseOwnedOmmOptin({...e,comment:{...e.comment,body:'@MathGraph -check'}},env()),null);
 assert.equal(parseOwnedOmmOptin({...e,comment:{...e.comment,body:command+' plus instructions'}},env()),null);
 assert.equal(parseOwnedOmmOptin(e,{...env(),GITHUB_RUN_ATTEMPT:'2'}),null);
 const {api}=client({edited:true});
 let calls=0;
 await assert.rejects(admitOwnedOmmSource({event:e,env:env(),api,
  qualifyRegistered:async()=>{calls++;return qualified();}}),/COMMENT_IDENTITY_CHANGED/);
 assert.equal(calls,0);
});

test('changed source between admission steps is refused even for registered cohort',async()=>{
 const {api}=client({moved:true});
 await assert.rejects(admitOwnedOmmSource({event:event(),env:env(),api,
  qualifyRegistered:async()=>qualified()}),/SOURCE_HEAD_MOVED/);
});

test('foreign-owned PR or unregistered claim fails closed',async()=>{
 const {api}=client({foreign:true});
 await assert.rejects(admitOwnedOmmSource({event:event(),env:env(),api,
  qualifyRegistered:async()=>qualified()}),/FIRST_PARTY_SOURCE_REQUIRED/);
 const normal=client();
 await assert.rejects(admitOwnedOmmSource({event:event(),env:env(),api:normal.api,
  qualifyRegistered:async()=>{throw Error('UNREGISTERED_ARTIN_PR');}}),/UNREGISTERED_ARTIN_PR/);
});

test('a forged qualification response cannot bind a different claim or base',async()=>{
 const {api}=client();
 await assert.rejects(admitOwnedOmmSource({event:event(),env:env(),api,
  qualifyRegistered:async()=>({request:{...qualified().request,number:240}})}),/QUALIFIED_SOURCE_IDENTITY_MISMATCH/);
});
