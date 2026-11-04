import {signedDispatch} from './transport.mjs';import {PILOT_ORIGIN} from './pilot-config.mjs';
export async function queuePilotStatus(request,result,key,fetcher=fetch){
 const origin=request.origin?Object.fromEntries(['number','comment_id','upstream_repository','upstream_number','upstream_url','watch','requested_at','watch_generation'].filter(k=>request.origin[k]!==undefined).map(k=>[k,request.origin[k]])):undefined;
 const subject={repository:request.repository,number:request.number,comment_id:request.comment_id,actor_id:request.actor_id,head_sha:request.head_sha,origin};
 const payload=signedDispatch({schema:'mathgraph.pilot.status.v2',command:'status-complete',repository:request.repository,subject,result},key);
 const response=await fetcher(PILOT_ORIGIN+'/pilot/import-complete',{method:'POST',redirect:'manual',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:AbortSignal.timeout(20000)});
 if(response.status!==202)throw Error('STATUS_QUEUE_INCOMPLETE');return {state:'QUEUED'};
}
