// Controlled Actions bridge: a real owned comment is re-read before native
// execution and again before/after Check publication. No public event listener.
import {createHash} from 'node:crypto';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {checkPublishedArtinInput} from './artin-preflight.mjs';
import {admitOwnedComment,verifyOwnedAdmission} from './owned-comment.mjs';
import {loadFrozenArtinPreview} from './app-owned-publish.mjs';
import {buildOwnedCommentCheck,reconcileOwnedCommentCheck} from './owned-comment-publish.mjs';

const REPO='metalogiclabs/mathgraph',NUMBER=239,OWNER_ID=32909488,COMMENT_ID=6645637811;
const BRANCH='refs/heads/feature/check-omm-claim-bridge-v1-20261105';
const SOURCE_SHA='e45efb73729fc98e45e66d216e792e70f67f8c43d4c12cbb753ac410b950e4d9';
const sha=s=>createHash('sha256').update(s).digest('hex');
const assert=(ok,reason)=>{if(!ok)throw Error(reason);};

/** Explicit HTTP method + least-privilege path boundary for our App publisher. */
export function makeOwnedGitHubApi({token,allowWrite=false,fetcher=globalThis.fetch}={}){
 assert(typeof token==='string'&&token.length>10&&typeof fetcher==='function',
  'OWNED_AUTHENTICATED_READ_CONTEXT_REQUIRED');
 const root=`/repos/${REPO}`;
 const read=path=>path===root+'/issues/comments/'+COMMENT_ID||
  path===root+'/pulls/'+NUMBER||
  path.startsWith(root+`/commits/2f6aaba0d71f1c0b4c0db58618a8981ccd59dc17/check-runs?check_name=`)||
  new RegExp('^'+root+'/check-runs/[1-9][0-9]*$').test(path);
 const writable=(method,path)=>allowWrite&&
  (method==='POST'&&path===root+'/check-runs'||
   method==='PATCH'&&new RegExp('^'+root+'/check-runs/[1-9][0-9]*$').test(path));
 return async(path,{method='GET',body}={})=>{
  assert(typeof path==='string'&&path.startsWith(root+'/')&&
   (method==='GET'&&body===undefined&&read(path)||writable(method,path)),
   'OWNED_API_SURFACE_REFUSED');
  const response=await fetcher('https://api.github.com'+path,{method,redirect:'error',
   headers:{Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28',
    Authorization:'Bearer '+token,'User-Agent':'MathGraph-OMM-Owned-Claim',
    'Content-Type':'application/json'},
   body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(20000)});
  assert(response.ok,'OWNED_GITHUB_'+method+'_'+response.status);
  return response.json();
 };
}

export async function prepareOwnedCommentInputs({directory,number,commentId,api,
 qualifyRegistered}={}){
 assert(typeof directory==='string'&&directory.startsWith('/')&&
  number===NUMBER&&commentId===COMMENT_ID&&typeof qualifyRegistered==='function',
  'OWNED_SOURCE_ADMISSION_CONTEXT');
 const bundle=await qualifyRegistered({number});
 const admission=await admitOwnedComment({number,commentId,api,
  qualifyRegistered:async()=>bundle});
 assert(bundle.request.candidate_source_sha256===SOURCE_SHA&&
  typeof bundle.source==='string'&&sha(bundle.source)===SOURCE_SHA&&
  typeof bundle.publishedSource==='string'&&bundle.publishedSource.length>10,
  'OWNED_SOURCE_BYTES_MISMATCH');
 const dir=resolve(directory);
 await mkdir(dir,{recursive:false});
 await Promise.all([
  writeFile(join(dir,'admission.json'),JSON.stringify(admission,null,2)+'\n',{flag:'wx'}),
  writeFile(join(dir,'request.json'),JSON.stringify(bundle.request,null,2)+'\n',{flag:'wx'}),
  writeFile(join(dir,'candidate.lean.txt'),bundle.source,{flag:'wx'}),
  writeFile(join(dir,'published-exercise.lean.txt'),bundle.publishedSource,{flag:'wx'})
 ]);
 return admission;
}

/** Bind a separately requalified native receipt to the authenticated request. */
export function checkOwnedNativeBinding({admission,request,assessment}={}){
 const valid=admission?.schema==='mathgraph.omm.owned-comment-admission.v1'&&
  admission.status==='SOURCE_ADMITTED_ONLY'&&admission.repository===REPO&&
  admission.number===NUMBER&&admission.comment_id===COMMENT_ID&&
  admission.head_sha===request?.head_sha&&admission.base_sha===request?.base_sha&&
  admission.source_sha256===request?.candidate_source_sha256&&
  admission.native_receipt==='UNKNOWN'&&admission.original_target==='UNKNOWN'&&
  admission.intent_fidelity==='UNKNOWN'&&admission.evidence_warrant==='UNKNOWN'&&
  admission.repair_permission==='DENIED'&&admission.publication_permission==='DENIED'&&
  assessment?.schema==='mathgraph.omm.claim-assessment.v1'&&
  assessment.status==='NATIVE_RECEIPT_BOUND'&&
  assessment.repository===admission.repository&&assessment.number===NUMBER&&
  assessment.head_sha===request.head_sha&&assessment.base_sha===request.base_sha&&
  assessment.candidate_sha256===request.candidate_source_sha256&&
  assessment.candidate_proof==='LEAN_COMPILED'&&
  assessment.original_target==='NOT_ESTABLISHED_IN_THIS_REPLAY'&&
  assessment.formal_statement_relation==='UNKNOWN'&&
  assessment.intent_fidelity==='UNKNOWN'&&assessment.evidence_warrant==='UNKNOWN'&&
  assessment.candidate_dependence==='UNKNOWN';
 assert(valid,'OWNED_NATIVE_BOUNDARY_MISMATCH');
 return true;
}

export async function publishOwnedComment({directory,runId,api,qualifyRegistered}={}){
 assert(typeof directory==='string'&&directory.startsWith('/')&&
  /^[1-9][0-9]*$/.test(String(runId??'')),'OWNED_PUBLISH_CONTEXT_REQUIRED');
 const admission=JSON.parse(await readFile(join(resolve(directory),'admission.json'),'utf8'));
 const verifyAdmission=async()=>verifyOwnedAdmission(admission,{api,qualifyRegistered});
 await verifyAdmission();
 const {request,assessment}=await loadFrozenArtinPreview({directory,number:NUMBER,runId});
 checkOwnedNativeBinding({admission,request,assessment});
 const runUrl=`https://github.com/${REPO}/actions/runs/${runId}`;
 buildOwnedCommentCheck({admission,assessment,runUrl});
 const result=await reconcileOwnedCommentCheck({admission,assessment,runUrl,api,verifyAdmission,write:true});
 await writeFile(join(resolve(directory),'output','owned-optin-app-receipt.json'),
  JSON.stringify(result,null,2)+'\n',{flag:'wx'});
 return result;
}

if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
 try{
  const mode=process.argv[2],directory=process.argv[3];
  assert(process.argv.length===4&&['preflight','publish'].includes(mode)&&
   directory?.startsWith('/')&&process.env.GITHUB_REPOSITORY===REPO&&
   process.env.GITHUB_EVENT_NAME==='push'&&process.env.GITHUB_REF===BRANCH&&
   process.env.GITHUB_ACTOR_ID===String(OWNER_ID)&&
   /^[1-9][0-9]*$/.test(process.env.GITHUB_RUN_ID??''),
   'OWNED_QUALIFICATION_WORKFLOW_CONTEXT_REQUIRED');
  const token=mode==='preflight'?process.env.GITHUB_TOKEN:
   process.env.MATHGRAPH_APP_INSTALLATION_TOKEN;
  assert(typeof token==='string'&&token.length>10,'OWNED_AUTHENTICATED_READ_CONTEXT_REQUIRED');
  const api=makeOwnedGitHubApi({token,allowWrite:mode==='publish'});
  const authorizedFetch=(url,opts)=>fetch(url,{...opts,redirect:'error',
   headers:{...opts?.headers,
    ...(url.startsWith(`https://api.github.com/repos/${REPO}/`)?{Authorization:'Bearer '+token}:{})},
   signal:AbortSignal.timeout(20000)});
  const qualifyRegistered=({number})=>checkPublishedArtinInput({number,fetch:authorizedFetch});
  const result=mode==='preflight'?
   await prepareOwnedCommentInputs({directory,number:NUMBER,commentId:COMMENT_ID,api,qualifyRegistered}):
   await publishOwnedComment({directory,runId:process.env.GITHUB_RUN_ID,api,qualifyRegistered});
  console.log('OMM_OWNED_OPTIN_'+mode.toUpperCase()+' '+JSON.stringify(result));
 }catch(e){console.error('OMM_OWNED_OPTIN_UNKNOWN:'+String(e.message));process.exitCode=1;}
}
