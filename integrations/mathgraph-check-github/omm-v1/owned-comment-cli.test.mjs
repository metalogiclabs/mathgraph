import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {artinStrongSource} from '../mention-artin-control-v1.mjs';

const repo='metalogiclabs/mathgraph',number=239,commentId=6645637811,owner=32909488;
const head='2f6aaba0d71f1c0b4c0db58618a8981ccd59dc17';
const base='dfd87d1e921953badedcfae21ade76bb38f5c04a';
const source='e45efb73729fc98e45e66d216e792e70f67f8c43d4c12cbb753ac410b950e4d9';
const timestamp='2026-11-05T00:00:20Z';
const qualified=()=>({request:{schema:'mathgraph.omm.request.v1',repository:repo,number,command:'check',
 head_sha:head,base_sha:base,candidate_source_sha256:source},
 source:artinStrongSource,publishedSource:'published verified Artin exercise'});
function api(path){
 if(path===`/repos/${repo}/issues/comments/${commentId}`)
  return {id:commentId,body:'@MathGraph -claim',user:{id:owner,type:'User'},
   created_at:timestamp,updated_at:timestamp,issue_url:`https://api.github.com/repos/${repo}/issues/${number}`};
 if(path===`/repos/${repo}/pulls/${number}`)
  return {number,state:'open',user:{id:owner,type:'User'},
   head:{sha:head,repo:{full_name:repo}},base:{sha:base,repo:{full_name:repo}}};
 throw Error('UNEXPECTED_'+path);
}
const subject=()=>import('./owned-comment-cli.mjs');

test('App Check creation uses a real HTTP POST with JSON rather than GET on the checks collection',async()=>{
 const {makeOwnedGitHubApi}=await subject();
 const requests=[];
 const api=makeOwnedGitHubApi({token:'test-token-with-no-real-access',allowWrite:true,
  fetcher:async(url,opts)=>{requests.push({url,opts});return {ok:true,status:201,
   json:async()=>({id:991})};}});
 const p={name:'MathGraph Check / OMM owner opt-in (advisory)',conclusion:'neutral'};
 assert.deepEqual(await api(`/repos/${repo}/check-runs`,{method:'POST',body:p}),{id:991});
 assert.equal(requests.length,1);
 assert.equal(requests[0].url,`https://api.github.com/repos/${repo}/check-runs`);
 assert.equal(requests[0].opts.method,'POST');
 assert.equal(requests[0].opts.body,JSON.stringify(p));
 assert.equal(requests[0].opts.headers['Content-Type'],'application/json');
 await api(`/repos/${repo}/check-runs/991`,{method:'PATCH',body:{conclusion:'neutral'}});
 assert.equal(requests[1].opts.method,'PATCH');
 await api(`/repos/${repo}/pulls/239`);
 assert.equal(requests[2].opts.method,'GET');
});

test('preflight API cannot write and publisher cannot mutate any path except exact Check endpoints',async()=>{
 const {makeOwnedGitHubApi}=await subject();
 let calls=0;
 const fetcher=async()=>{calls++;return {ok:true,json:async()=>({})};};
 const read=makeOwnedGitHubApi({token:'test-token-with-no-real-access',fetcher});
 await assert.rejects(read(`/repos/${repo}/check-runs`,{method:'POST',body:{}}),/OWNED_API_SURFACE_REFUSED/);
 const write=makeOwnedGitHubApi({token:'test-token-with-no-real-access',fetcher,allowWrite:true});
 await assert.rejects(write(`/repos/${repo}/issues/comments/1`,{method:'POST',body:{}}),/OWNED_API_SURFACE_REFUSED/);
 await assert.rejects(write('/repos/foreign/repo/check-runs',{method:'POST',body:{}}),/OWNED_API_SURFACE_REFUSED/);
 assert.equal(calls,0);
});

test('real source admission writes a run-local admission and actual fixed Lean source',async()=>{
 const {prepareOwnedCommentInputs}=await subject();
 const root=await mkdtemp(join(tmpdir(),'omm-owned-comment-'));
 const dir=join(root,'artin');
 try{
  const admission=await prepareOwnedCommentInputs({directory:dir,number,commentId,
   api:async path=>api(path),qualifyRegistered:async()=>qualified()});
  assert.equal(admission.comment_id,commentId);
  assert.equal(admission.status,'SOURCE_ADMITTED_ONLY');
  assert.deepEqual(JSON.parse(await readFile(join(dir,'admission.json'),'utf8')),admission);
  assert.deepEqual(JSON.parse(await readFile(join(dir,'request.json'),'utf8')),qualified().request);
  assert.equal(await readFile(join(dir,'candidate.lean.txt'),'utf8'),artinStrongSource);
  assert.equal(await readFile(join(dir,'published-exercise.lean.txt'),'utf8'),qualified().publishedSource);
 }finally{await rm(root,{recursive:true,force:true});}
});

test('preflight refuses a qualified manifest that does not match candidate source bytes',async()=>{
 const {prepareOwnedCommentInputs}=await subject();
 const root=await mkdtemp(join(tmpdir(),'omm-owned-comment-'));
 try{await assert.rejects(prepareOwnedCommentInputs({directory:join(root,'artin'),number,commentId,
  api:async path=>api(path),qualifyRegistered:async()=>({...qualified(),source:'wrong source'})}),
  /OWNED_SOURCE_BYTES_MISMATCH/);
 }finally{await rm(root,{recursive:true,force:true});}
});

test('artifact binding requires exact admission, registered PR and native assessment',async()=>{
 const {checkOwnedNativeBinding}=await subject();
 const admission={schema:'mathgraph.omm.owned-comment-admission.v1',status:'SOURCE_ADMITTED_ONLY',
  repository:repo,number,comment_id:commentId,head_sha:head,base_sha:base,source_sha256:source,
  comment_created_at:timestamp,comment_updated_at:timestamp,
  native_receipt:'UNKNOWN',original_target:'UNKNOWN',intent_fidelity:'UNKNOWN',
  evidence_warrant:'UNKNOWN',repair_permission:'DENIED',publication_permission:'DENIED'};
 const assessment={schema:'mathgraph.omm.claim-assessment.v1',status:'NATIVE_RECEIPT_BOUND',
  repository:repo,number,head_sha:head,base_sha:base,candidate_sha256:source,
  candidate_proof:'LEAN_COMPILED',original_target:'NOT_ESTABLISHED_IN_THIS_REPLAY',
  formal_statement_relation:'UNKNOWN',intent_fidelity:'UNKNOWN',evidence_warrant:'UNKNOWN',
  candidate_dependence:'UNKNOWN',native_receipt_sha256:'a'.repeat(64)};
 assert.equal(checkOwnedNativeBinding({admission,request:qualified().request,assessment}),true);
 for(const request of [{...qualified().request,base_sha:'0'.repeat(40)},
  {...qualified().request,candidate_source_sha256:'f'.repeat(64)}])
  assert.throws(()=>checkOwnedNativeBinding({admission,request,assessment}),/OWNED_NATIVE_BOUNDARY_MISMATCH/);
 for(const modified of [{original_target:'CONSUMER_ACCEPTED'},{evidence_warrant:'WARRANTED'}])
  assert.throws(()=>checkOwnedNativeBinding({admission,request:qualified().request,
   assessment:{...assessment,...modified}}),/OWNED_NATIVE_BOUNDARY_MISMATCH/);
});
