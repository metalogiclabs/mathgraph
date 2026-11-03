import {mintScopedToken} from './auth.mjs';
import {profileFor,modelReservationCents} from './policy.mjs';import {authenticate,withdrawChecks,queueCheck,finishCheck,listChecks} from './lifecycle.mjs';import {signedDispatch,reservationKey} from './transport.mjs';import {githubClient} from './github.mjs';
const ensure=(b,c)=>{if(!b)throw Error(c);};
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
   item={...item,comment_id:previous.comment_id,command:'check'};
  }
  request=await authenticate(item,api);
  publication=await queueCheck(request,api);if(publication.state==='DUPLICATE')return {state:'DUPLICATE',check_id:publication.check_id};
  request.queued_check_id=publication.check_id;
  let reserved={status:'NOT_NEEDED',reserved_cents:0};
  const cents=modelReservationCents(request);if(cents>0){const stub=env.PR_PILOT_BUDGET.get(env.PR_PILOT_BUDGET.idFromName(String(item.installationID)));const response=await stub.fetch('https://internal/reserve',{method:'POST',body:JSON.stringify({key:reservationKey(request),cents,day:new Date().toISOString().slice(0,10)})});reserved=await response.json();}
  if(['BUDGET_EXHAUSTED','DUPLICATE'].includes(reserved.status)){await finishCheck(request,publication,{status:'UNKNOWN',reason:reserved.status},api);return {state:reserved.status};}
  ensure(['RESERVED','DUPLICATE','NOT_NEEDED'].includes(reserved.status),'BUDGET_RESERVATION_FAILED');
  if(request.command==='check')await env.PILOT_SUBSCRIPTIONS.put(subscriptionKey,JSON.stringify({comment_id:request.comment_id,head_sha:request.head_sha,base_sha:request.base_sha}));
  const central=await app('/repos/metalogiclabs/mathgraph/installation');
  const dispatchToken=await mintScopedToken(app,central.id,'metalogiclabs/mathgraph',{contents:'write'},{fetcher});
  const dispatch=githubClient(dispatchToken,{repository:item.repository,fetcher});
  try{await dispatch('/repos/metalogiclabs/mathgraph/dispatches',{method:'POST',body:{event_type:'mathgraph-pr-pilot-v1',client_payload:signedDispatch({...request,installation_id:item.installationID,reserved_cents:reserved.reserved_cents},env.GITHUB_APP_PRIVATE_KEY)}});}finally{await dispatch('/installation/token',{method:'DELETE'});}
  return {state:'DISPATCHED',repository:request.repository,number:request.number,head_sha:request.head_sha,command:request.command};
 }catch(e){if(publication?.state==='QUEUED'&&request){try{await finishCheck(request,publication,{status:'UNKNOWN',reason:'REQUEST_DISPATCH_INCOMPLETE'},api);}catch{}}throw e;}finally{await api('/installation/token',{method:'DELETE'});}
}
