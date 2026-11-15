import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {artinStrongSource} from '../mention-artin-control-v1.mjs';

const owner=32909488,commentId=6657771222,repo='metalogiclabs/mathgraph';
const event={action:'created',repository:{full_name:repo},sender:{id:owner,type:'User'},
 issue:{number:239,pull_request:{url:`https://api.github.com/repos/${repo}/pulls/239`}},
 comment:{id:commentId,body:'@MathGraph /check',user:{id:owner,type:'User'},
  created_at:'2026-11-05T01:15:20Z',updated_at:'2026-11-05T01:15:20Z',
  issue_url:`https://api.github.com/repos/${repo}/issues/239`}};

test('only a newly created exact slash command by the registered first-party owner enters the listener',async()=>{
 const {validateOwnedSlashEvent}=await import('./slash-owned-cli.mjs');
 assert.equal(validateOwnedSlashEvent({event,actorId:String(owner),runAttempt:'1'}),commentId);
 for(const modified of [
  {...event,action:'edited'},
  {...event,repository:{full_name:'other/repo'}},
  {...event,issue:{...event.issue,number:240}},
  {...event,issue:{number:239}},
  {...event,sender:{id:42,type:'User'}},
  {...event,comment:{...event.comment,body:'@MathGraph -claim'}},
  {...event,comment:{...event.comment,body:'@MathGraph /check extra'}},
  {...event,comment:{...event.comment,user:{id:12,type:'User'}}},
  {...event,comment:{...event.comment,updated_at:'2026-11-05T01:16:20Z'}},
  {...event,comment:{...event.comment,id:'6657771222'}}
 ])assert.throws(()=>validateOwnedSlashEvent({event:modified,actorId:String(owner),runAttempt:'1'}),
  /OWNED_SLASH_EVENT_REFUSED/);
 assert.throws(()=>validateOwnedSlashEvent({event,actorId:String(owner),runAttempt:'2'}),/OWNED_SLASH_EVENT_REFUSED/);
 assert.throws(()=>validateOwnedSlashEvent({event,actorId:'9',runAttempt:'1'}),/OWNED_SLASH_EVENT_REFUSED/);
});

test('slash event binds dynamically selected comment without expanding the GitHub API read surface',async()=>{
 const {makeOwnedGitHubApi}=await import('./owned-comment-cli.mjs');
 const requested=[];
 const api=makeOwnedGitHubApi({token:'test-token-with-no-real-access',commentId,fetcher:async(url)=>{
  requested.push(url);return {ok:true,json:async()=>({id:commentId})};}});
 await api(`/repos/${repo}/issues/comments/${commentId}`);
 await assert.rejects(api(`/repos/${repo}/issues/comments/6645637811`),/OWNED_API_SURFACE_REFUSED/);
 await assert.rejects(api(`/repos/${repo}/issues/comments/${commentId+1}`),/OWNED_API_SURFACE_REFUSED/);
 assert.equal(requested.length,1);
});

test('preflight reauthenticates actual slash bytes and freezes exact source without arbitrary execution',async()=>{
 const {prepareOwnedSlash}=await import('./slash-owned-cli.mjs');
 const root=await mkdtemp(join(tmpdir(),'omm-owned-slash-'));
 const head='2f6aaba0d71f1c0b4c0db58618a8981ccd59dc17';
 const base='dfd87d1e921953badedcfae21ade76bb38f5c04a';
 const qualified=()=>({request:{schema:'mathgraph.omm.request.v1',repository:repo,number:239,
  command:'check',head_sha:head,base_sha:base,
  candidate_source_sha256:'e45efb73729fc98e45e66d216e792e70f67f8c43d4c12cbb753ac410b950e4d9'},
  source:artinStrongSource,publishedSource:'published verified Artin exercise'});
 const api=async path=>{
  if(path===`/repos/${repo}/issues/comments/${commentId}`)return event.comment;
  if(path===`/repos/${repo}/pulls/239`)return {number:239,state:'open',user:{id:owner,type:'User'},
   head:{sha:head,repo:{full_name:repo}},base:{sha:base,repo:{full_name:repo}}};
  throw Error('UNEXPECTED_API_PATH');
 };
 try{
  const admission=await prepareOwnedSlash({directory:join(root,'accepted'),event,
   actorId:String(owner),runAttempt:'1',api,qualifyRegistered:async()=>qualified()});
  assert.equal(admission.comment_id,commentId);
  assert.equal(admission.intent_fidelity,'UNKNOWN');
  assert.equal(await readFile(join(root,'accepted','candidate.lean.txt'),'utf8'),artinStrongSource);
  await assert.rejects(prepareOwnedSlash({directory:join(root,'mismatch'),event,
   actorId:String(owner),runAttempt:'1',api:async path=>path.includes('/issues/comments/')?
    {...event.comment,created_at:'2026-11-05T01:15:30Z',updated_at:'2026-11-05T01:15:30Z'}:api(path),
   qualifyRegistered:async()=>qualified()}),/OWNED_EVENT_API_MISMATCH/);
  await assert.rejects(prepareOwnedSlash({directory:join(root,'legacy'),event,
   actorId:String(owner),runAttempt:'1',api:async path=>path.includes('/issues/comments/')?
    {...event.comment,body:'@MathGraph -claim'}:api(path),qualifyRegistered:async()=>qualified()}),
   /OWNED_COMMENT_IDENTITY_UNQUALIFIED/);
 }finally{await rm(root,{recursive:true,force:true});}
});

test('slash Check has distinct identity, binds the comment, and remains neutral/UNKNOWN',async()=>{
 const {buildOwnedCommentCheck}=await import('./owned-comment-publish.mjs');
 const admission={schema:'mathgraph.omm.owned-comment-admission.v1',status:'SOURCE_ADMITTED_ONLY',
  repository:repo,number:239,comment_id:commentId,comment_created_at:'2026-11-05T01:15:20Z',
  comment_updated_at:'2026-11-05T01:15:20Z',
  head_sha:'2f6aaba0d71f1c0b4c0db58618a8981ccd59dc17',
  base_sha:'dfd87d1e921953badedcfae21ade76bb38f5c04a',
  source_sha256:'e45efb73729fc98e45e66d216e792e70f67f8c43d4c12cbb753ac410b950e4d9',
  native_receipt:'UNKNOWN',original_target:'UNKNOWN',intent_fidelity:'UNKNOWN',
  evidence_warrant:'UNKNOWN',repair_permission:'DENIED',publication_permission:'DENIED'};
 const assessment={schema:'mathgraph.omm.claim-assessment.v1',status:'NATIVE_RECEIPT_BOUND',
  repository:repo,number:239,head_sha:admission.head_sha,base_sha:admission.base_sha,
  candidate_sha256:admission.source_sha256,candidate_proof:'LEAN_COMPILED',
  original_target:'NOT_ESTABLISHED_IN_THIS_REPLAY',formal_statement_relation:'UNKNOWN',
  intent_fidelity:'UNKNOWN',evidence_warrant:'UNKNOWN',candidate_dependence:'UNKNOWN',
  native_receipt_sha256:'a'.repeat(64)};
 const url=`https://github.com/${repo}/actions/runs/41999990001`;
 const previous=buildOwnedCommentCheck({admission,assessment,runUrl:url});
 const next=buildOwnedCommentCheck({admission,assessment,runUrl:url,channel:'slash-v1'});
 assert.equal(previous.name,'MathGraph Check / OMM owner opt-in (advisory)');
 assert.match(previous.output.summary,/not an active issue_comment listener/);
 assert.equal(next.name,'MathGraph Check / OMM \/check (advisory)');
 assert.notEqual(next.external_id,previous.external_id);
 assert.equal(next.status,'completed');assert.equal(next.conclusion,'neutral');
 assert.match(next.output.summary,/issuecomment-6657771222/);
 assert.match(next.output.summary,/issue_comment listener/);
 assert.match(next.output.summary,/intent \| UNKNOWN/);
 assert.match(next.output.summary,/repair permission \| DENIED/i);
 assert.doesNotMatch(next.output.summary,/not an active issue_comment listener/);
 assert.throws(()=>buildOwnedCommentCheck({admission,assessment,runUrl:url,channel:'arbitrary'}),
  /OWNED_OPTIN_NOT_QUALIFIED/);
});

