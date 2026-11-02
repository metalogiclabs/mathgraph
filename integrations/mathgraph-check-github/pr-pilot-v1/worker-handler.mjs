import {profileFor} from './policy.mjs';import {authenticate,withdrawChecks} from './lifecycle.mjs';import {signedDispatch,reservationKey} from './transport.mjs';import {githubClient} from './github.mjs';
const ensure=(b,c)=>{if(!b)throw Error(c);};
export async function processPilotDelivery(item,env,{jwt,fetcher=fetch}={}){
 if(env.PR_PILOT_ENABLED!=='true')return {state:'DISABLED'};
 profileFor(item.repository);ensure(item.schema==='mathgraph.pr-pilot.delivery.v1'&&Number.isSafeInteger(item.installationID)&&item.installationID>0&&Number.isSafeInteger(item.number)&&item.number>0&&['command','synchronize','closed'].includes(item.action),'INVALID_PILOT_DELIVERY');
 ensure(env.PR_PILOT_BUDGET&&env.WARRANT_EVENTS,'PILOT_STORAGE_UNAVAILABLE');
 const app=githubClient(jwt,{repository:item.repository,fetcher}),installation=await app('/repos/'+item.repository+'/installation');
 ensure(installation.id===item.installationID,'INSTALLATION_MISMATCH');
 const source=await app(`/app/installations/${installation.id}/access_tokens`,{method:'POST',body:{repository_names:[item.repository.split('/')[1]],permissions:{contents:'read',pull_requests:'read',issues:'write',checks:'write'}}});
 const api=githubClient(source.token,{repository:item.repository,fetcher}),root='/repos/'+item.repository;
 const subscriptionKey=`pr-pilot/subscription/${item.repository}/${item.number}.json`;
 try{
  let previous;const stored=await env.WARRANT_EVENTS.get(subscriptionKey);if(stored)previous=await stored.json();
  if(item.action!=='command'){
   if(!previous)return {state:'NOT_OPTED_IN'};
   const pr=await api(root+'/pulls/'+item.number);
   for(const sha of new Set([previous.head_sha,item.previous_sha].filter(x=>/^[a-f0-9]{40}$/.test(x??'')))){
    const response=await api(root+'/commits/'+sha+'/check-runs?per_page=100');ensure(response.total_count===response.check_runs?.length,'INCOMPLETE_CHECK_HISTORY');
    await withdrawChecks({repository:item.repository,number:item.number,head_sha:item.action==='closed'?'':pr.head?.sha},response.check_runs,api);
   }
   if(item.action==='closed'){await env.WARRANT_EVENTS.delete(subscriptionKey);return {state:'CLOSED_WITHDRAWN'};}
   item={...item,comment_id:previous.comment_id,command:'check'};
  }
  const request=await authenticate(item,api);
  let reserved={status:'NOT_NEEDED',reserved_cents:0};
  if(request.support.supported){const stub=env.PR_PILOT_BUDGET.get(env.PR_PILOT_BUDGET.idFromName(String(item.installationID)));const response=await stub.fetch('https://internal/reserve',{method:'POST',body:JSON.stringify({key:reservationKey(request),cents:request.command==='check'?49:98,day:new Date().toISOString().slice(0,10)})});reserved=await response.json();}
  if(reserved.status==='BUDGET_EXHAUSTED')return {state:'BUDGET_EXHAUSTED'};
  ensure(['RESERVED','DUPLICATE','NOT_NEEDED'].includes(reserved.status),'BUDGET_RESERVATION_FAILED');
  if(request.command==='check')await env.WARRANT_EVENTS.put(subscriptionKey,JSON.stringify({comment_id:request.comment_id,head_sha:request.head_sha}));
  const central=await app('/repos/metalogiclabs/mathgraph/installation');
  const dispatchToken=await app(`/app/installations/${central.id}/access_tokens`,{method:'POST',body:{repository_names:['mathgraph'],permissions:{contents:'write'}}});
  const dispatch=githubClient(dispatchToken.token,{repository:item.repository,fetcher});
  try{await dispatch('/repos/metalogiclabs/mathgraph/dispatches',{method:'POST',body:{event_type:'mathgraph-pr-pilot-v1',client_payload:signedDispatch({...request,installation_id:item.installationID,reserved_cents:reserved.reserved_cents},env.GITHUB_APP_PRIVATE_KEY)}});}finally{await dispatch('/installation/token',{method:'DELETE'});}
  return {state:'DISPATCHED',repository:request.repository,number:request.number,head_sha:request.head_sha,command:request.command};
 }finally{await api('/installation/token',{method:'DELETE'});}
}
