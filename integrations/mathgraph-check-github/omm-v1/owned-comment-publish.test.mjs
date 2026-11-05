import test from 'node:test';
import assert from 'node:assert/strict';

const repo='metalogiclabs/mathgraph',owner=32909488,number=239,commentId=6650111234;
const head='2f6aaba0d71f1c0b4c0db58618a8981ccd59dc17';
const base='dfd87d1e921953badedcfae21ade76bb38f5c04a';
const admission={schema:'mathgraph.omm.owned-comment-admission.v1',status:'SOURCE_ADMITTED_ONLY',
 repository:repo,number,comment_id:commentId,comment_created_at:'2026-11-05T00:35:12Z',
 comment_updated_at:'2026-11-05T00:35:12Z',head_sha:head,base_sha:base,
 source_sha256:'e45efb73729fc98e45e66d216e792e70f67f8c43d4c12cbb753ac410b950e4d9',
 native_receipt:'UNKNOWN',original_target:'UNKNOWN',intent_fidelity:'UNKNOWN',
 evidence_warrant:'UNKNOWN',repair_permission:'DENIED',publication_permission:'DENIED'};
const assessment={schema:'mathgraph.omm.claim-assessment.v1',status:'NATIVE_RECEIPT_BOUND',
 number,repository:repo,head_sha:head,base_sha:base,candidate_proof:'LEAN_COMPILED',
 original_target:'NOT_ESTABLISHED_IN_THIS_REPLAY',formal_statement_relation:'UNKNOWN',
 intent_fidelity:'UNKNOWN',evidence_warrant:'UNKNOWN',candidate_dependence:'UNKNOWN',
 native_receipt_sha256:'a'.repeat(64),candidate_sha256:admission.source_sha256};
const runUrl=`https://github.com/${repo}/actions/runs/41930000111`;
const subject=()=>import('./owned-comment-publish.mjs');

function client({foreignApp=false,duplicate=false,moved=false}={}){
 const calls=[];let numberOfPrGets=0,check=null,created=0;
 const appCheck=()=>({id:900123,app:{id:foreignApp?1234:5308912},
  name:check.name,head_sha:check.head_sha,external_id:check.external_id,
  status:check.status,conclusion:check.conclusion,output:check.output});
 const api=async(path,{method='GET',body}={})=>{
  calls.push({path,method});
  if(path===`/repos/${repo}/pulls/${number}`){numberOfPrGets++;
   return {number,state:'open',user:{id:owner,type:'User'},
    head:{sha:moved&&numberOfPrGets>1?'0'.repeat(40):head,repo:{full_name:repo}},
    base:{sha:base,repo:{full_name:repo}}};}
  if(path.startsWith(`/repos/${repo}/commits/${head}/check-runs?`))
   return {total_count:check?(duplicate?2:1):0,
    check_runs:check?(duplicate?[appCheck(),{...appCheck(),id:900124}]:[appCheck()]):[]};
  if(path===`/repos/${repo}/check-runs`&&method==='POST'){
   check=body;created++;return appCheck();}
  if(path===`/repos/${repo}/check-runs/900123`&&method==='PATCH'){
   check={...check,...body};return appCheck();}
  if(path===`/repos/${repo}/check-runs/900123`&&method==='GET')return appCheck();
  throw Error('UNEXPECTED_'+path+'_'+method);
 };
 return {api,calls,getCreated:()=>created,seed:payload=>{check=payload;}};
}

test('owner command + pinned native negative consumer projects only a neutral advisory',async()=>{
 const {buildOwnedCommentCheck}=await subject();
 const p=buildOwnedCommentCheck({admission,assessment,runUrl});
 assert.equal(p.name,'MathGraph Check / OMM owner opt-in (advisory)');
 assert.equal(p.head_sha,head);
 assert.equal(p.status,'completed');
 assert.equal(p.conclusion,'neutral');
 assert.match(p.external_id,/^mathgraph-omm-owner-optin-v1:/);
 assert.match(p.output.summary,/issuecomment-6650111234/);
 assert.match(p.output.summary,/NOT_ESTABLISHED_IN_THIS_REPLAY/);
 assert.match(p.output.summary,/Mathematical intent \| UNKNOWN/);
 assert.match(p.output.summary,/Independent evidence warrant \| UNKNOWN/);
 assert.match(p.output.summary,/not an active issue_comment listener/);
});

test('unqualified or promoted claims never form an App payload',async()=>{
 const {buildOwnedCommentCheck}=await subject();
 for(const change of [{head_sha:'0'.repeat(40)},{status:'WARRANTED'},
  {publication_permission:'ALLOWED'}, {comment_id:0}])
  assert.throws(()=>buildOwnedCommentCheck({admission:{...admission,...change},assessment,runUrl}),
   /OWNED_OPTIN_NOT_QUALIFIED/);
 for(const change of [{intent_fidelity:'WARRANTED'},{evidence_warrant:'WARRANTED'},
  {original_target:'CONSUMER_ACCEPTED'},{candidate_sha256:'0'.repeat(64)}])
  assert.throws(()=>buildOwnedCommentCheck({admission,assessment:{...assessment,...change},runUrl}),
   /OWNED_OPTIN_NOT_QUALIFIED/);
});

test('App write is neutral, exact-head, independently reread, idempotent',async()=>{
 const {reconcileOwnedCommentCheck}=await subject();
 const c=client();let rechecks=0;
 const args={admission,assessment,runUrl,api:c.api,verifyAdmission:async()=>{rechecks++;return admission;}};
 const a=await reconcileOwnedCommentCheck({...args,write:true});
 assert.equal(a.mode,'CREATED');assert.equal(a.app_id,5308912);
 assert.equal(a.check_run_id,900123);assert.equal(c.getCreated(),1);
 assert.equal(rechecks>=2,true);
 const b=await reconcileOwnedCommentCheck({...args,write:true});
 assert.equal(b.mode,'UNCHANGED');assert.equal(c.getCreated(),1);
});

test('non-owning App collision, duplicate Check and stale source fail closed before write',async()=>{
 const {buildOwnedCommentCheck,reconcileOwnedCommentCheck}=await subject();
 const payload=buildOwnedCommentCheck({admission,assessment,runUrl});
 for(const config of [{foreignApp:true},{duplicate:true},{moved:true}]){
  const c=client(config);if(!config.moved)c.seed(payload);
  await assert.rejects(reconcileOwnedCommentCheck({admission,assessment,runUrl,api:c.api,
   verifyAdmission:async()=>admission,write:true}),
   /FOREIGN_APP_CHECK_NAME_COLLISION|DUPLICATE_OWNED_OMM_CHECK|STALE_PR_HEAD/);
  assert.equal(c.getCreated(),0);
 }
});

test('comment/source withdrawing during the publisher gate prevents App creation',async()=>{
 const {reconcileOwnedCommentCheck}=await subject();
 const c=client();let i=0;
 await assert.rejects(reconcileOwnedCommentCheck({admission,assessment,runUrl,api:c.api,
  verifyAdmission:async()=>{if(++i>1)throw Error('COMMENT_CHANGED');return admission;},write:true}),
  /COMMENT_CHANGED/);
 assert.equal(c.getCreated(),0);
});
