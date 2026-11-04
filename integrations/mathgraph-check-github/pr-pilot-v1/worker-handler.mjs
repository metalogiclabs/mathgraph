import {readPilotActor} from './pilot-actor.mjs';
import {PILOT_INBOX} from './pilot-config.mjs';
import {publishRequestStatus,checkURL,reuseDetails} from './request-status.mjs';
import {authenticateImported,publicGitHub} from './imported-check.mjs';
import {registerWatch,stopWatch,watchKey,pollWatches} from './watch.mjs';
import {authorizeImport} from './upstream-intake.mjs';
import {REPORT_METHOD} from './report-integrity.mjs';
import {isFiniteMethod} from './finite-methods.mjs';
import {mintScopedToken} from './auth.mjs';
import {profileFor,modelReservationCents} from './policy.mjs';import {authenticate,withdrawChecks,queueCheck,finishCheck,listChecks} from './lifecycle.mjs';import {signedDispatch,reservationKey} from './transport.mjs';import {githubClient} from './github.mjs';
const ensure=(b,c)=>{if(!b)throw Error(c);};
export function pilotOperatorIDs(value){if(typeof value!=='string'||!/^\d+(,\d+){0,15}$/.test(value))return [];const ids=value.split(',').map(Number);return ids.every(x=>Number.isSafeInteger(x)&&x>0)?[...new Set(ids)]:[];}
export async function processPilotDelivery(item,env,{jwt,fetcher=fetch}={}){
 if(env.PR_PILOT_ENABLED!=='true')return {state:'DISABLED'};
 profileFor(item.repository);ensure(item.schema==='mathgraph.pr-pilot.delivery.v1'&&Number.isSafeInteger(item.installationID)&&item.installationID>0&&Number.isSafeInteger(item.number)&&item.number>0&&['command','synchronize','closed'].includes(item.action),'INVALID_PILOT_DELIVERY');
 ensure(env.PR_PILOT_BUDGET&&env.PILOT_SUBSCRIPTIONS,'PILOT_STORAGE_UNAVAILABLE');
 const app=githubClient(jwt,{repository:item.repository,fetcher}),installation=await app('/repos/'+item.repository+'/installation');
 ensure(installation.id===item.installationID,'INSTALLATION_MISMATCH');
 const token=await mintScopedToken(app,installation.id,item.repository,{contents:'read',pull_requests:'read',issues:'write',checks:'write'},{fetcher});
 const api=githubClient(token,{repository:item.repository,fetcher}),root='/repos/'+item.repository;
 let publication,request;
 const subscriptionKey=`pr-pilot/subscription/${item.repository}/${item.number}.json`;
 try{
  if(item.action==='command'&&!item.origin){
   const actor=await readPilotActor(item,api,pilotOperatorIDs(env.PR_PILOT_OPERATOR_IDS));
   if(!actor.allowed){await publishRequestStatus(item,api,{state:'INVITE_REQUIRED'});return {state:'INVITATION_REQUIRED'};}
   if(item.command==='status'){ensure(/^(?:\/|@MathGraph -?)(status|help)$/i.test(actor.comment.body.trim()),'COMMAND_CHANGED');await publishRequestStatus(item,api,{state:'ACCESS_READY'});return {state:'ACCESS_READY'};}
   if(item.number===PILOT_INBOX&&item.command!=='import'){await publishRequestStatus(item,api,{state:'INPUT_NEEDED'});return {state:'INPUT_NEEDED'};}
  }
  if(item.action==='command'&&item.command==='import'){
   let authorized=await authorizeImport(item,api,pilotOperatorIDs(env.PR_PILOT_OPERATOR_IDS));
   if(item.from_watch){const record=await env.PILOT_SUBSCRIPTIONS.get(watchKey(authorized)),w=record?await record.json():null;if(!w||w.stopped||w.expires_at<=Date.now()||w.pending_generation!==item.watch_generation)return {state:'WATCH_REQUEST_SUPERSEDED'};authorized={...authorized,watch_generation:item.watch_generation};}
   if(authorized.stop){const old=await env.PILOT_SUBSCRIPTIONS.get(watchKey(authorized));await stopWatch(env.PILOT_SUBSCRIPTIONS,authorized);if(old)await publishRequestStatus((await old.json()).request,api,{state:'WATCH_STOPPED'});await publishRequestStatus(authorized,api,{state:'WATCH_STOPPED'});return {state:'WATCH_STOPPED'};}
   await publishRequestStatus(authorized,api,{state:'QUEUED',reason:authorized.watch?'Preparing a checked copy and seven-day follow request.':'Preparing a checked copy of this one revision.'});
   const central=await app('/repos/metalogiclabs/mathgraph/installation'),dt=await mintScopedToken(app,central.id,'metalogiclabs/mathgraph',{contents:'write'},{fetcher}),dispatch=githubClient(dt,{repository:item.repository,fetcher});
   try{await dispatch('/repos/metalogiclabs/mathgraph/dispatches',{method:'POST',body:{event_type:'mathgraph-pr-import-v2',client_payload:signedDispatch({...authorized,installation_id:item.installationID},env.GITHUB_APP_PRIVATE_KEY)}});}finally{await dispatch('/installation/token',{method:'DELETE'});}
   return {state:'IMPORT_DISPATCHED',upstream_number:authorized.upstream_number};
  }
  let previous;const stored=await env.PILOT_SUBSCRIPTIONS.get(subscriptionKey);if(stored)previous=await stored.json();
  if(item.action!=='command'){
   if(!previous)return {state:'NOT_OPTED_IN'};
   const pr=await api(root+'/pulls/'+item.number);
   if(item.action==='synchronize'&&previous.head_sha===pr.head?.sha&&previous.base_sha===pr.base?.sha)return {state:'SOURCE_UNCHANGED'};
   for(const sha of new Set([previous.head_sha,item.previous_sha].filter(x=>/^[a-f0-9]{40}$/.test(x??'')))){
    const checks=await listChecks({repository:item.repository,head_sha:sha},api);
    await withdrawChecks({repository:item.repository,number:item.number,head_sha:item.action==='closed'?'':pr.head?.sha,base_sha:pr.base?.sha},checks,api);
   }
   if(item.action==='closed'){await env.PILOT_SUBSCRIPTIONS.delete(subscriptionKey);return {state:'CLOSED_WITHDRAWN'};}
   item=previous.import_item?{...previous.import_item,action:'command'}:{...item,comment_id:previous.comment_id,command:'check'};
  }
  request=item.origin?await authenticateImported(item,api,{pilotOperators:pilotOperatorIDs(env.PR_PILOT_OPERATOR_IDS),publicAPI:publicGitHub({fetcher,token})}):await authenticate(item,api,{pilotOperators:pilotOperatorIDs(env.PR_PILOT_OPERATOR_IDS)});
  if(request.origin?.watch){
   const origin={...request.origin,repository:request.repository,actor_id:request.actor_id,actor_login:request.actor_login,actor_authorization:request.actor_authorization,installation_id:item.installationID};
   try{const w=await registerWatch(env.PILOT_SUBSCRIPTIONS,origin,{state:request.upstream_state,head:request.upstream_head,base:request.upstream_base,number:request.number,url:`https://github.com/${request.repository}/pull/${request.number}`,snapshot_head:request.head_sha});if(!w&&request.upstream_state==='open'){await publishRequestStatus(origin,api,{state:'WATCH_STOPPED',reason:'The request stopped or expired before this update completed.'});return {state:'WATCH_STOPPED'};}if(w)request.watch_expires_at=w.expires_at;}
   catch(e){if(e.message!=='WATCH_CAPACITY_REACHED')throw e;request.follow_note='The shared limit of three followed PRs is full. This one-time Check still runs.';}
  }
  publication=await queueCheck(request,api);if(publication.state==='DUPLICATE'){const c=await api(root+'/check-runs/'+publication.check_id);await publishRequestStatus(request,api,{state:c.status==='completed'?'REUSED':'RUNNING',title:c.output?.title,check_url:checkURL(request.repository,request.number,publication.check_id),snapshot_url:request.origin?`https://github.com/${request.repository}/pull/${request.number}`:undefined,...reuseDetails(c)});return {state:'DUPLICATE',check_id:publication.check_id};}
  await publishRequestStatus(request,api,{state:'QUEUED',check_url:checkURL(request.repository,request.number,publication.check_id),snapshot_url:request.origin?`https://github.com/${request.repository}/pull/${request.number}`:undefined,expires_at:request.watch_expires_at,reason:request.follow_note});
  request.queued_check_id=publication.check_id;
  if(!request.support.supported){await finishCheck(request,publication,{status:'UNKNOWN',reason:request.support.reason},api);await publishRequestStatus(request,api,{state:'UNKNOWN',reason:'This change is outside the available reviewed checks. No whole-PR correctness result is claimed.',check_url:checkURL(request.repository,request.number,publication.check_id)});return {state:'UNKNOWN',reason:request.support.reason};}
  let reserved={status:'NOT_NEEDED',reserved_cents:0};
  const cents=modelReservationCents(request);if(cents>0){const stub=env.PR_PILOT_BUDGET.get(env.PR_PILOT_BUDGET.idFromName(String(item.installationID)));const response=await stub.fetch('https://internal/reserve',{method:'POST',body:JSON.stringify({key:reservationKey(request),cents,day:new Date().toISOString().slice(0,10)})});reserved=await response.json();}
  if(['BUDGET_EXHAUSTED','DUPLICATE'].includes(reserved.status)){await finishCheck(request,publication,{status:'UNKNOWN',reason:reserved.status},api);await publishRequestStatus(request,api,{state:'UNKNOWN',reason:'The shared model-assisted pilot budget is unavailable for this request. It is capped at USD10 per installation per UTC day; fixed no-model checks remain available.',check_url:checkURL(request.repository,request.number,publication.check_id)});return {state:reserved.status};}
  ensure(['RESERVED','DUPLICATE','NOT_NEEDED'].includes(reserved.status),'BUDGET_RESERVATION_FAILED');
  if(request.command==='check')await env.PILOT_SUBSCRIPTIONS.put(subscriptionKey,JSON.stringify({comment_id:request.comment_id,head_sha:request.head_sha,base_sha:request.base_sha,import_item:item.origin?item:undefined}));
  const central=await app('/repos/metalogiclabs/mathgraph/installation');
  const dispatchToken=await mintScopedToken(app,central.id,'metalogiclabs/mathgraph',{contents:'write'},{fetcher});
  const dispatch=githubClient(dispatchToken,{repository:item.repository,fetcher});
  try{await dispatch('/repos/metalogiclabs/mathgraph/dispatches',{method:'POST',body:{event_type:'mathgraph-pr-selfserve-v2',client_payload:signedDispatch({...request,installation_id:item.installationID,reserved_cents:reserved.reserved_cents},env.GITHUB_APP_PRIVATE_KEY)}});}finally{await dispatch('/installation/token',{method:'DELETE'});}
  return {state:'DISPATCHED',repository:request.repository,number:request.number,head_sha:request.head_sha,command:request.command};
 }catch(e){if(item.origin&&!publication){try{await publishRequestStatus({repository:item.repository,origin:item.origin},api,{state:'UNKNOWN',reason:e.message==='UPSTREAM_CHANGED_RETRY_REQUIRED'?'The source changed while this copy was being prepared. A followed PR will be checked again on a new copy.':'The original request or copied source could not be verified. No code-check result is claimed.'});}catch{}}if(publication?.state==='QUEUED'&&request){try{await finishCheck(request,publication,{status:'UNKNOWN',reason:'REQUEST_DISPATCH_INCOMPLETE'},api);}catch{}}throw e;}finally{await api('/installation/token',{method:'DELETE'});}
}

// Scheduled work is serialized through the existing queue (max_concurrency=1).
export async function processPilotWatchTick(env,{jwt,fetcher=fetch,now=Date.now()}={}){
 if(env.PR_PILOT_ENABLED!=='true')return {state:'DISABLED'};
 const repository='metalogiclabs/L4YAML',app=githubClient(jwt,{repository,fetcher}),installation=await app('/repos/'+repository+'/installation'),token=await mintScopedToken(app,installation.id,repository,{contents:'read',pull_requests:'read',issues:'write',checks:'write'},{fetcher}),api=githubClient(token,{repository,fetcher});
 try{const results=await pollWatches(env.PILOT_SUBSCRIPTIONS,{publicAPI:publicGitHub({fetcher,token}),authorize:r=>authorizeImport(r,api,pilotOperatorIDs(env.PR_PILOT_OPERATOR_IDS)),enqueue:async x=>env.PR_EVENTS.send({schema:'mathgraph.pr-pilot.delivery.v1',repository,number:x.origin.number,comment_id:x.origin.comment_id,installationID:installation.id,action:'command',command:'import',from_watch:true,watch_generation:x.watch_generation}),withdraw:async w=>{if(w.snapshot_head&&w.snapshot_number){const checks=await listChecks({repository,head_sha:w.snapshot_head},api);await withdrawChecks({repository,number:w.snapshot_number,head_sha:''},checks,api,{force:true});}},notify:(r,v)=>publishRequestStatus(r,api,v)},now);return {state:'WATCH_TICK',results};}finally{await api('/installation/token',{method:'DELETE'});}
}

export async function processPilotStatusDelivery(item,env,{jwt,fetcher=fetch}={}){
 if(env.PR_PILOT_ENABLED!=='true')return {state:'DISABLED'};
 if(!Number.isSafeInteger(item.issued_at)||Date.now()-item.issued_at>7200000)return {state:'STATUS_EXPIRED'};
 const request=item.subject;profileFor(request.repository);const app=githubClient(jwt,{repository:request.repository,fetcher}),installation=await app('/repos/'+request.repository+'/installation'),token=await mintScopedToken(app,installation.id,request.repository,{contents:'read',pull_requests:'read',issues:'write'},{fetcher}),api=githubClient(token,{repository:request.repository,fetcher});
 try{let actor;try{actor=await readPilotActor({...request,...(request.origin??{}),repository:request.repository},api,pilotOperatorIDs(env.PR_PILOT_OPERATOR_IDS));}catch(e){if(['ACTOR_ORIGIN_INVALID','ACTOR_COMMENT_INVALID','GITHUB_HTTP_404'].includes(e.message))return {state:'STATUS_ORIGIN_GONE'};throw e;}ensure(actor.actor_id===request.actor_id,'STATUS_ACTOR_CHANGED');const result=actor.allowed?item.result:{state:'INVITE_REQUIRED'};return await publishRequestStatus(request,api,result);}finally{await api('/installation/token',{method:'DELETE'});}
}
