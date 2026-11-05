// Exact first-party /check issue_comment bridge; frozen PR239 source only.
// No community intake, model invocation or repair. App credentials are only
// present in the final publisher job, never the Lean process.
import {readFile,writeFile} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {checkPublishedArtinInput} from './artin-preflight.mjs';
import {verifyOwnedAdmission} from './owned-comment.mjs';
import {makeOwnedGitHubApi,prepareOwnedCommentInputs,checkOwnedNativeBinding} from './owned-comment-cli.mjs';
import {loadFrozenArtinPreview} from './app-owned-publish.mjs';
import {reconcileOwnedCommentCheck} from './owned-comment-publish.mjs';

const REPO='metalogiclabs/mathgraph',NUMBER=239,OWNER=32909488;
const BODY='@MathGraph /check';
const assert=(valid,reason)=>{if(!valid)throw Error(reason);};
const isTime=t=>/^20\d\d-\d\d-\d\dT\d\d:\d\d:\d\dZ$/.test(t??'');

/** Validate the runner's event; the API source and comment are re-read later. */
export function validateOwnedSlashEvent({event,actorId,runAttempt}={}){
 const comment=event?.comment;
 assert(event?.action==='created'&&event.repository?.full_name===REPO&&
  event.sender?.id===OWNER&&event.sender?.type==='User'&&
  event.issue?.number===NUMBER&&
  event.issue?.pull_request?.url===`https://api.github.com/repos/${REPO}/pulls/${NUMBER}`&&
  Number.isSafeInteger(comment?.id)&&comment.id>0&&comment.body===BODY&&
  comment.user?.id===OWNER&&comment.user.type==='User'&&
  comment.issue_url===`https://api.github.com/repos/${REPO}/issues/${NUMBER}`&&
  isTime(comment.created_at)&&comment.updated_at===comment.created_at&&
  actorId===String(OWNER)&&runAttempt==='1','OWNED_SLASH_EVENT_REFUSED');
 return comment.id;
}

export async function prepareOwnedSlash({directory,event,actorId,runAttempt,api,
 qualifyRegistered}={}){
 const commentId=validateOwnedSlashEvent({event,actorId,runAttempt});
 const admission=await prepareOwnedCommentInputs({directory,number:NUMBER,commentId,
  api,qualifyRegistered,commandBody:BODY});
 assert(admission.comment_created_at===event.comment.created_at,'OWNED_EVENT_API_MISMATCH');
 return admission;
}

export async function publishOwnedSlash({directory,event,actorId,runAttempt,api,
 qualifyRegistered,runId}={}){
 const commentId=validateOwnedSlashEvent({event,actorId,runAttempt});
 assert(typeof directory==='string'&&directory.startsWith('/')&&
  /^[1-9][0-9]*$/.test(String(runId??'')),'OWNED_SLASH_PUBLISH_CONTEXT');
 const admission=JSON.parse(await readFile(join(resolve(directory),'admission.json'),'utf8'));
 assert(admission.comment_id===commentId&&
  admission.comment_created_at===event.comment.created_at,'OWNED_EVENT_API_MISMATCH');
 const verifyAdmission=async()=>verifyOwnedAdmission(admission,{number:NUMBER,api,
  qualifyRegistered,commandBody:BODY});
 await verifyAdmission();
 const {request,assessment}=await loadFrozenArtinPreview({directory,number:NUMBER,runId});
 checkOwnedNativeBinding({admission,request,assessment,expectedCommentId:commentId});
 const runUrl=`https://github.com/${REPO}/actions/runs/${runId}`;
 const result=await reconcileOwnedCommentCheck({admission,assessment,runUrl,
  api,verifyAdmission,write:true,channel:'slash-v1'});
 await writeFile(join(resolve(directory),'output','owned-slash-app-receipt.json'),
  JSON.stringify(result,null,2)+'\n',{flag:'wx'});
 return result;
}

if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
 try{
  const mode=process.argv[2],directory=process.argv[3];
  assert(process.argv.length===4&&['preflight','publish'].includes(mode)&&
   directory?.startsWith('/')&&process.env.GITHUB_REPOSITORY===REPO&&
   process.env.GITHUB_EVENT_NAME==='issue_comment'&&
   typeof process.env.GITHUB_EVENT_PATH==='string'&&
   /^[1-9][0-9]*$/.test(process.env.GITHUB_RUN_ID??''),
   'OWNED_SLASH_WORKFLOW_CONTEXT_REQUIRED');
  const event=JSON.parse(await readFile(process.env.GITHUB_EVENT_PATH,'utf8'));
  const commentId=validateOwnedSlashEvent({event,actorId:process.env.GITHUB_ACTOR_ID,
   runAttempt:process.env.GITHUB_RUN_ATTEMPT});
  const token=mode==='preflight'?process.env.GITHUB_TOKEN:
   process.env.MATHGRAPH_APP_INSTALLATION_TOKEN;
  const api=makeOwnedGitHubApi({token,commentId,allowWrite:mode==='publish'});
  const authorizedFetch=(url,opts)=>fetch(url,{...opts,redirect:'error',
   headers:{...opts?.headers,
    ...(url.startsWith(`https://api.github.com/repos/${REPO}/`)?
     {Authorization:'Bearer '+token}:{})},signal:AbortSignal.timeout(20000)});
  const qualifyRegistered=({number})=>checkPublishedArtinInput({number,fetch:authorizedFetch});
  const result=mode==='preflight'?
   await prepareOwnedSlash({directory,event,actorId:process.env.GITHUB_ACTOR_ID,
    runAttempt:process.env.GITHUB_RUN_ATTEMPT,api,qualifyRegistered}):
   await publishOwnedSlash({directory,event,actorId:process.env.GITHUB_ACTOR_ID,
    runAttempt:process.env.GITHUB_RUN_ATTEMPT,api,qualifyRegistered,
    runId:process.env.GITHUB_RUN_ID});
  console.log('OMM_OWNED_SLASH_'+mode.toUpperCase()+' '+JSON.stringify(result));
 }catch(e){console.error('OMM_OWNED_SLASH_UNKNOWN:'+String(e.message));process.exitCode=1;}
}
