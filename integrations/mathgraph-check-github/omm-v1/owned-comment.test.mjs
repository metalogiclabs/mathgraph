import test from 'node:test';
import assert from 'node:assert/strict';

const repo='metalogiclabs/mathgraph',owner=32909488,number=239,commentId=6650111234;
const head='2f6aaba0d71f1c0b4c0db58618a8981ccd59dc17';
const base='dfd87d1e921953badedcfae21ade76bb38f5c04a';
const source='e45efb73729fc98e45e66d216e792e70f67f8c43d4c12cbb753ac410b950e4d9';
const timestamp='2026-11-05T00:35:12Z';
const qualified=()=>({request:{schema:'mathgraph.omm.request.v1',repository:repo,number,
 command:'check',head_sha:head,base_sha:base,candidate_source_sha256:source}});

function client({foreignComment=false,edited=false,wrongPr=false,headMoved=false,
 baseMoved=false,ownerChanged=false,deleted=false}={}){
 const calls=[];let c=0,p=0;
 const api=async path=>{
  calls.push(path);
  if(path===`/repos/${repo}/issues/comments/${commentId}`){
   c++;if(deleted&&c>1)throw Error('HTTP_404');
   return {id:commentId,body:edited&&c>1?'@MathGraph -fix':'@MathGraph -claim',
    user:{id:foreignComment?9:owner,type:'User'},
    created_at:timestamp,updated_at:edited&&c>1?'2026-11-05T00:36:00Z':timestamp,
    issue_url:`https://api.github.com/repos/${repo}/issues/${wrongPr?240:number}`};
  }
  if(path===`/repos/${repo}/pulls/${number}`){
   p++;return {number,state:'open',user:{id:ownerChanged?10:owner,type:'User'},
    head:{sha:headMoved&&p>1?'0'.repeat(40):head,repo:{full_name:repo}},
    base:{sha:baseMoved&&p>1?'0'.repeat(40):base,repo:{full_name:repo}}};
  }
  throw Error(`UNEXPECTED_${path}`);
 };
 return {api,calls};
}

async function subject(){return import('./owned-comment.mjs');}

test('real owned comment gates only the registered frozen Artin source and never warrants intent',async()=>{
 const {admitOwnedComment}=await subject();
 const {api,calls}=client();
 const admission=await admitOwnedComment({number,commentId,api,
  qualifyRegistered:async({number:n})=>{assert.equal(n,239);return qualified();}});
 assert.equal(admission.schema,'mathgraph.omm.owned-comment-admission.v1');
 assert.equal(admission.status,'SOURCE_ADMITTED_ONLY');
 assert.equal(admission.comment_id,commentId);
 assert.equal(admission.head_sha,head);
 assert.equal(admission.base_sha,base);
 assert.equal(admission.source_sha256,source);
 for(const field of ['native_receipt','original_target','intent_fidelity','evidence_warrant'])
  assert.equal(admission[field],'UNKNOWN');
 assert.equal(admission.publication_permission,'DENIED');
 assert.equal(admission.repair_permission,'DENIED');
 assert.deepEqual(calls,[`/repos/${repo}/issues/comments/${commentId}`,
  `/repos/${repo}/pulls/${number}`,`/repos/${repo}/issues/comments/${commentId}`,
  `/repos/${repo}/pulls/${number}`]);
});

test('cannot admit unsupported PR or arbitrary invalid IDs',async()=>{
 const {admitOwnedComment}=await subject();
 const {api}=client();
 await assert.rejects(admitOwnedComment({number:240,commentId,api}),/UNREGISTERED_OWNED_REQUEST/);
 await assert.rejects(admitOwnedComment({number,commentId:0,api}),/UNREGISTERED_OWNED_REQUEST/);
 await assert.rejects(admitOwnedComment({number,commentId:'123',api}),/UNREGISTERED_OWNED_REQUEST/);
});

test('foreign author, wrong issue, wrong PR owner or changed source are rejected',async()=>{
 const {admitOwnedComment}=await subject();
 for(const config of [{foreignComment:true},{wrongPr:true},{ownerChanged:true}]){
  const {api}=client(config);
  await assert.rejects(admitOwnedComment({number,commentId,api,
   qualifyRegistered:async()=>qualified()}),/OWNED_COMMENT_IDENTITY_UNQUALIFIED|FIRST_PARTY_PR_REQUIRED/);
 }
 const {api}=client();
 await assert.rejects(admitOwnedComment({number,commentId,api,
  qualifyRegistered:async()=>({request:{...qualified().request,head_sha:'0'.repeat(40)}})}),
  /QUALIFIED_SOURCE_IDENTITY_MISMATCH/);
});

test('recheck refuses edited/deleted owner comment and head/base movement',async()=>{
 const {admitOwnedComment}=await subject();
 for(const config of [{edited:true},{deleted:true},{headMoved:true},{baseMoved:true}]){
  const {api}=client(config);
  await assert.rejects(admitOwnedComment({number,commentId,api,
   qualifyRegistered:async()=>qualified()}),
   /COMMENT_CHANGED|SOURCE_HEAD_MOVED|HTTP_404/);
 }
});

test('saved admission is independently rederived; tampering is rejected',async()=>{
 const {admitOwnedComment,verifyOwnedAdmission}=await subject();
 const admission=await admitOwnedComment({number,commentId,api:client().api,
  qualifyRegistered:async()=>qualified()});
 assert.deepEqual(await verifyOwnedAdmission(admission,{api:client().api,
  qualifyRegistered:async()=>qualified()}),admission);
 for(const change of [{head_sha:'1'.repeat(40)},{comment_id:commentId+1},
  {publication_permission:'ALLOWED'},{evidence_warrant:'WARRANTED'}]){
  await assert.rejects(verifyOwnedAdmission({...admission,...change},{api:client().api,
   qualifyRegistered:async()=>qualified()}),/OWNED_ADMISSION_RECHECK_MISMATCH|UNREGISTERED_OWNED_REQUEST/);
 }
});
