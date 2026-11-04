import {verifyDispatch} from './transport.mjs';
const ensure=(b,c)=>{if(!b)throw Error(c);};
export async function acceptImportComplete(request,env){
 if(env.PR_PILOT_ENABLED!=='true')return new Response('Pilot disabled',{status:503});
 try{
  ensure(request.method==='POST','METHOD_INVALID');ensure(Number(request.headers.get('content-length')??0)<=64000,'CALLBACK_TOO_LARGE');const reader=request.body?.getReader(),parts=[];let size=0;if(reader)while(true){const chunk=await reader.read();if(chunk.done)break;size+=chunk.value.byteLength;if(size>64000){await reader.cancel();throw Error('CALLBACK_TOO_LARGE');}parts.push(chunk.value);}const raw=new TextDecoder().decode(Buffer.concat(parts));const r=verifyDispatch(JSON.parse(raw),env.GITHUB_APP_PRIVATE_KEY);
  if(r.schema==='mathgraph.pilot.status.v2'&&r.command==='status-complete'){
   ensure(r.subject?.repository===r.repository&&r.repository==='metalogiclabs/L4YAML','STATUS_REPOSITORY_INVALID');for(const k of ['number','comment_id','actor_id'])ensure(Number.isSafeInteger(r.subject[k])&&r.subject[k]>0,'STATUS_ID_INVALID');ensure(['PUBLISHED','UNKNOWN'].includes(r.result?.state),'STATUS_STATE_INVALID');await env.PR_EVENTS.send({schema:'mathgraph.pilot.status.v2',subject:r.subject,result:r.result,issued_at:r.issued_at});return new Response('Status queued',{status:202});
  }
  ensure(r.schema==='mathgraph.import-complete.v2'&&r.command==='import-complete'&&r.repository==='metalogiclabs/L4YAML','CALLBACK_PURPOSE_INVALID');
  for(const k of ['number','comment_id','actor_id','installation_id','snapshot_number','upstream_number'])ensure(Number.isSafeInteger(r[k])&&r[k]>0,'CALLBACK_ID_INVALID');
  ensure(['nasa-jpl/L4YAML','metalogiclabs/L4YAML'].includes(r.upstream_repository)&&['upstream_head','upstream_base'].every(k=>/^[a-f0-9]{40}$/.test(r[k])),'CALLBACK_SOURCE_INVALID');
  await env.PR_EVENTS.send({schema:'mathgraph.pr-pilot.delivery.v1',repository:r.repository,number:r.snapshot_number,comment_id:r.comment_id,actor_id:r.actor_id,installationID:r.installation_id,command:'import-check',action:'command',upstream_head:r.upstream_head,upstream_base:r.upstream_base,origin:{number:r.number,comment_id:r.comment_id,upstream_number:r.upstream_number,upstream_repository:r.upstream_repository,upstream_url:r.upstream_url,watch:r.watch===true},watch_generation:r.watch_generation??0});
  return new Response('Check queued',{status:202});
 }catch(e){return new Response('Import completion could not be verified',{status:e.message==='CALLBACK_TOO_LARGE'?413:403});}
}
