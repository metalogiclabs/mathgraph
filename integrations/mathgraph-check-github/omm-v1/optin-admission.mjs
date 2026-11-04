// An operator-only, non-publishing OMM opt-in source gate. It authenticates
// the human request and source boundary before any native work. A command
// cannot supply its own theorem, native evidence, model prompt or proof.
// No live issue_comment workflow is activated by this module alone.
import {checkPublishedArtinInput} from './artin-preflight.mjs';

const REPO='metalogiclabs/mathgraph',USER_ID=32909488;
const SHA40=/^[a-f0-9]{40}$/;
const root='/repos/'+REPO;
const assert=(ok,error)=>{if(!ok)throw Error(error);};

export function parseOwnedOmmOptin(event,env={}){
 if(env.GITHUB_EVENT_NAME!=='issue_comment'||env.GITHUB_REPOSITORY!==REPO||
  env.GITHUB_RUN_ATTEMPT!=='1'||event?.action!=='created'||
  event.repository?.full_name!==REPO||event.sender?.id!==USER_ID||
  event.sender?.type!=='User'||event.comment?.user?.id!==USER_ID||
  event.comment.user?.type!=='User'||event.comment?.body!=='@MathGraph -claim'||
  !Number.isSafeInteger(event.comment?.id)||event.comment.id<1||
  !event.issue?.pull_request||!Number.isSafeInteger(event.issue?.number)||event.issue.number<1)return null;
 return {number:event.issue.number,commentId:event.comment.id};
}

/** Admit identity only. A full native claim receipt and independent intent remain UNKNOWN. */
export async function admitOwnedOmmSource({event,env,api,qualifyRegistered=checkPublishedArtinInput}={}){
 const input=parseOwnedOmmOptin(event,env);
 assert(input&&typeof api==='function'&&typeof qualifyRegistered==='function','UNQUALIFIED_OMM_OPTIN');
 const comment=await api(root+'/issues/comments/'+input.commentId);
 assert(comment?.id===input.commentId&&comment.body===event.comment.body&&
  comment.user?.id===USER_ID&&comment.issue_url==='https://api.github.com'+root+'/issues/'+input.number&&
  typeof comment.created_at==='string'&&comment.created_at===event.comment.created_at&&
  comment.updated_at===event.comment.updated_at,'COMMENT_IDENTITY_CHANGED');
 const original=await api(root+'/pulls/'+input.number);
 const sourceOkay=p=>p?.number===input.number&&p.state==='open'&&
  SHA40.test(p.head?.sha??'')&&SHA40.test(p.base?.sha??'')&&
  p.head.repo?.full_name===REPO&&p.base.repo?.full_name===REPO;
 assert(sourceOkay(original),'FIRST_PARTY_SOURCE_REQUIRED');
 const registration=await qualifyRegistered({number:input.number});
 const contract=registration?.request;
 assert(contract?.schema==='mathgraph.omm.request.v1'&&contract.repository===REPO&&
  contract.number===input.number&&contract.command==='check'&&
  contract.head_sha===original.head.sha&&contract.base_sha===original.base.sha&&
  /^[a-f0-9]{64}$/.test(contract.candidate_source_sha256??''),
  'QUALIFIED_SOURCE_IDENTITY_MISMATCH');
 const current=await api(root+'/pulls/'+input.number);
 assert(sourceOkay(current)&&current.head.sha===original.head.sha&&
  current.base.sha===original.base.sha,'SOURCE_HEAD_MOVED');
 return {schema:'mathgraph.omm.optin-admission.v1',status:'SOURCE_ADMITTED_ONLY',
  repository:REPO,number:input.number,comment_id:input.commentId,
  head_sha:contract.head_sha,base_sha:contract.base_sha,
  source_sha256:contract.candidate_source_sha256,
  native_receipt:'UNKNOWN',original_target:'UNKNOWN',
  intent_fidelity:'UNKNOWN',evidence_warrant:'UNKNOWN',
  repair_permission:'DENIED',publication_permission:'DENIED'};
}
