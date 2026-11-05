// Qualification-only: authenticate a REAL first-party GitHub comment by ID.
// This is not an issue_comment event handler; it never grants execution,
// publication, semantic warrant or repair permission on its own.
import {checkPublishedArtinInput} from './artin-preflight.mjs';

const REPO='metalogiclabs/mathgraph',NUMBER=239,OWNER=32909488;
const SHA40=/^[a-f0-9]{40}$/,SHA256=/^[a-f0-9]{64}$/;
const root='/repos/'+REPO;
const requireQualified=(ok,reason)=>{if(!ok)throw Error(reason);};

const sourceValid=p=>p?.number===NUMBER&&p.state==='open'&&
 p.user?.id===OWNER&&p.user.type==='User'&&
 SHA40.test(p.head?.sha??'')&&SHA40.test(p.base?.sha??'')&&
 p.head?.repo?.full_name===REPO&&p.base?.repo?.full_name===REPO;
const commentValid=(c,id)=>c?.id===id&&c.body==='@MathGraph -claim'&&
 c.user?.id===OWNER&&c.user?.type==='User'&&
 c.issue_url===`https://api.github.com${root}/issues/${NUMBER}`&&
 /^20\d\d-\d\d-\d\dT\d\d:\d\d:\d\dZ$/.test(c.created_at??'')&&
 c.updated_at===c.created_at;

/** Treat one exact owner-authored GitHub comment as a source request only. */
export async function admitOwnedComment({number,commentId,api,
 qualifyRegistered=checkPublishedArtinInput}={}){
 requireQualified(number===NUMBER&&Number.isSafeInteger(commentId)&&commentId>0&&
  typeof api==='function'&&typeof qualifyRegistered==='function','UNREGISTERED_OWNED_REQUEST');
 const path=root+'/issues/comments/'+commentId;
 const initialComment=await api(path);
 requireQualified(commentValid(initialComment,commentId),'OWNED_COMMENT_IDENTITY_UNQUALIFIED');
 const initialPr=await api(root+'/pulls/'+NUMBER);
 requireQualified(sourceValid(initialPr),'FIRST_PARTY_PR_REQUIRED');
 const registration=await qualifyRegistered({number:NUMBER});
 const request=registration?.request;
 requireQualified(request?.schema==='mathgraph.omm.request.v1'&&
  request.repository===REPO&&request.number===NUMBER&&request.command==='check'&&
  request.head_sha===initialPr.head.sha&&request.base_sha===initialPr.base.sha&&
  SHA256.test(request.candidate_source_sha256??''),'QUALIFIED_SOURCE_IDENTITY_MISMATCH');
 const lastComment=await api(path);
 requireQualified(commentValid(lastComment,commentId)&&
  lastComment.created_at===initialComment.created_at&&
  lastComment.updated_at===initialComment.updated_at,'COMMENT_CHANGED');
 const lastPr=await api(root+'/pulls/'+NUMBER);
 requireQualified(sourceValid(lastPr)&&lastPr.head.sha===initialPr.head.sha&&
  lastPr.base.sha===initialPr.base.sha,'SOURCE_HEAD_MOVED');
 return {schema:'mathgraph.omm.owned-comment-admission.v1',status:'SOURCE_ADMITTED_ONLY',
  repository:REPO,number:NUMBER,comment_id:commentId,
  comment_created_at:initialComment.created_at,comment_updated_at:initialComment.updated_at,
  head_sha:request.head_sha,base_sha:request.base_sha,
  source_sha256:request.candidate_source_sha256,
  native_receipt:'UNKNOWN',original_target:'UNKNOWN',intent_fidelity:'UNKNOWN',
  evidence_warrant:'UNKNOWN',repair_permission:'DENIED',publication_permission:'DENIED'};
}

/** Re-read live source/comment and compare *every* admitted field before use. */
export async function verifyOwnedAdmission(admission,options={}){
 requireQualified(admission?.schema==='mathgraph.omm.owned-comment-admission.v1'&&
  admission.number===NUMBER&&Number.isSafeInteger(admission.comment_id),
  'OWNED_ADMISSION_RECHECK_MISMATCH');
 let fresh;
 try{fresh=await admitOwnedComment({...options,number:NUMBER,commentId:admission.comment_id});}
 catch{throw Error('OWNED_ADMISSION_RECHECK_MISMATCH');}
 requireQualified(JSON.stringify(admission)===JSON.stringify(fresh),
  'OWNED_ADMISSION_RECHECK_MISMATCH');
 return fresh;
}
