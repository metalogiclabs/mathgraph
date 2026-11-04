// Metadata-only orchestration: imported code never executes in this process.
import {readFile} from 'node:fs/promises';
import {appJWT} from '../cloudflare/worker.mjs';import {githubClient} from './github.mjs';import {mintScopedToken} from './auth.mjs';import {verifyDispatch,signedDispatch} from './transport.mjs';
import {authorizeImport,snapshotUpstream} from './upstream-intake.mjs';import {publicGitHub} from './imported-check.mjs';import {publishRequestStatus} from './request-status.mjs';import {PILOT_ORIGIN} from './pilot-config.mjs';
const ensure=(b,c)=>{if(!b)throw Error(c);};
const event=JSON.parse(await readFile(process.env.GITHUB_EVENT_PATH,'utf8'));ensure(event.action==='mathgraph-pr-import-v2','WRONG_EVENT');
const signed=verifyDispatch(event.client_payload,process.env.APP_PRIVATE_KEY);ensure(signed.command==='import','WRONG_COMMAND');
const app=githubClient(appJWT(process.env.APP_PRIVATE_KEY),{repository:signed.repository}),installation=await app('/repos/'+signed.repository+'/installation');ensure(installation.id===signed.installation_id,'INSTALLATION_CHANGED');
const token=await mintScopedToken(app,installation.id,signed.repository,{contents:'write',pull_requests:'write',issues:'write'}),api=githubClient(token,{repository:signed.repository});
try{
 let request=await authorizeImport(signed,api,signed.actor_authorization==='PILOT_OPERATOR'?[signed.actor_id]:[]);
 ensure(!request.stop&&['actor_id','actor_login','actor_authorization','upstream_number','upstream_repository','upstream_url','watch','stop'].every(k=>request[k]===signed[k]),'IMPORT_AUTHORITY_CHANGED');
 ensure(signed.watch_generation===undefined||Number.isSafeInteger(signed.watch_generation)&&signed.watch_generation>0,'WATCH_GENERATION_INVALID');request={...request,watch_generation:signed.watch_generation};
 try{
  const result=await snapshotUpstream(request,api,publicGitHub({token:process.env.GITHUB_TOKEN}));ensure(Number.isSafeInteger(result.number)&&result.number>0,'IMPORT_RESULT_INVALID');
  const payload=signedDispatch({...request,schema:'mathgraph.import-complete.v2',command:'import-complete',installation_id:installation.id,snapshot_number:result.number,upstream_head:result.head,upstream_base:result.base},process.env.APP_PRIVATE_KEY);
  const response=await fetch(PILOT_ORIGIN+'/pilot/import-complete',{method:'POST',redirect:'manual',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:AbortSignal.timeout(20000)});ensure(response.status===202,'IMPORTED_CHECK_QUEUE_INCOMPLETE');
  console.log(JSON.stringify({...result,check:'QUEUED_FOR_REAUTHORIZATION'}));
 }catch(e){await publishRequestStatus(request,api,{state:'UNKNOWN',reason:e.message==='UPSTREAM_CHANGED_RETRY_REQUIRED'?'The source changed while the snapshot was prepared. Submit the current link again; an active follow will retry.':'The PR copy or its automatic Check could not be completed. No source-code result is claimed.'});throw e;}
}finally{await api('/installation/token',{method:'DELETE'});}
