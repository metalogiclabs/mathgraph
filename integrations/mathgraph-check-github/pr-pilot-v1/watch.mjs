import {WATCH_MAX,WATCH_MS,WATCH_INTERVAL_MS} from './pilot-config.mjs';
import {admitUpstream} from './upstream-intake.mjs';
const ensure=(b,c)=>{if(!b)throw Error(c);};
export function watchKey(r){ensure(['nasa-jpl/L4YAML','metalogiclabs/L4YAML'].includes(r.upstream_repository)&&Number.isSafeInteger(r.upstream_number)&&r.upstream_number>0&&Number.isSafeInteger(r.actor_id)&&r.actor_id>0,'WATCH_ID_INVALID');return `pr-pilot/watch/${r.upstream_repository}/${r.upstream_number}/${r.actor_id}.json`;}
async function all(storage){const list=await storage.list({prefix:'pr-pilot/watch/',limit:100});ensure(list&&Array.isArray(list.objects)&&list.truncated===false,'WATCH_LIST_INCOMPLETE');const records=[];for(const x of list.objects){const value=await storage.get(x.key);if(value)records.push({key:x.key,value:await value.json()});}return records;}
export async function registerWatch(storage,request,result,now=Date.now()){
 const key=watchKey(request),records=await all(storage);
 for(const r of records)if(r.value.expires_at<=now)await storage.delete(r.key);
 const existing=records.find(r=>r.key===key&&r.value.expires_at>now)?.value;
 if(existing&&request.comment_id<existing.request.comment_id)return null;
 const same=existing?.request.comment_id===request.comment_id;
 if(same&&(existing.stopped||(request.watch_generation??0)<Math.max(existing.generation??0,existing.pending_generation??0)))return null;
 if(!request.watch||result.state!=='open'){await storage.delete(key);return null;}
 const expires=same?existing.expires_at:(request.requested_at??now)+WATCH_MS;
 if(expires<=now){await storage.delete(key);return null;}
 const active=records.filter(r=>r.value.expires_at>now&&!r.value.stopped);
 ensure(existing&&!existing.stopped||active.length<WATCH_MAX,'WATCH_CAPACITY_REACHED');
 const value={schema:'mathgraph.pilot.watch.v2',request:{...request},head:result.head,base:result.base,snapshot_number:result.number,snapshot_url:result.url,snapshot_head:result.snapshot_head,installationID:request.installation_id,expires_at:expires,last_checked_at:now,pending_at:null,generation:request.watch_generation??existing?.generation??0,pending_generation:null,pending_head:null,pending_base:null};
 await storage.put(key,JSON.stringify(value));return value;
}
export async function stopWatch(storage,request,now=Date.now()){const key=watchKey(request),old=await storage.get(key),w=old?await old.json():null;if(w&&request.comment_id<w.request.comment_id)return false;await storage.put(key,JSON.stringify({...w,schema:'mathgraph.pilot.watch.v2',request:{...request},stopped:true,pending_at:null,pending_generation:null,expires_at:Math.max(w?.expires_at??0,(request.requested_at??now)+WATCH_MS)}));return !!old;}
export async function pollWatches(storage,hooks,now=Date.now()){
 const results=[];
 for(const {key,value:w}of await all(storage)){
  const stop=async reason=>{await storage.delete(key);await hooks.notify(w.request,{state:'WATCH_STOPPED',reason,last_checked_at:now});results.push({state:'STOPPED',reason});};
  if(w.expires_at<=now){await stop('The seven-day follow period ended.');continue;}
  if(w.stopped)continue;
  if(w.last_checked_at+WATCH_INTERVAL_MS>now)continue;
  try{
   let actor;try{actor=await hooks.authorize(w.request);}catch(e){if(['MAINTAINER_REQUIRED','IMPORT_COMMENT_INVALID','ACTOR_ORIGIN_INVALID','ACTOR_COMMENT_INVALID'].includes(e.message)){await stop('Access or the original request changed.');continue;}throw e;}
   if(actor.actor_id!==w.request.actor_id||!actor.watch||actor.stop){await stop('The original follow request is no longer active.');continue;}
   const source=admitUpstream(await hooks.publicAPI('/repos/'+w.request.upstream_repository+'/pulls/'+w.request.upstream_number),w.request.upstream_number,w.request.upstream_repository);
   const changed=source.head!==w.head||source.base!==w.base;
   if(!changed&&!w.pending_at&&source.state==='closed'){await stop('The source PR is closed; its recorded revision remains available.');continue;}
   const pendingDifferent=!!w.pending_at&&(source.head!==w.pending_head||source.base!==w.pending_base),needs=changed||!!w.pending_at;
   if(needs&&(!w.pending_at||pendingDifferent||now-w.pending_at>=30*60*1000)){
    const generation=w.pending_at&&!pendingDifferent?w.pending_generation:Math.max(w.generation??0,w.pending_generation??0)+1;
    await hooks.withdraw(w);
    await hooks.enqueue({origin:w.request,upstream_head:source.head,upstream_base:source.base,watch_generation:generation});
    w.pending_at=now;w.pending_generation=generation;w.pending_head=source.head;w.pending_base=source.base;results.push({state:'ENQUEUED',upstream_number:w.request.upstream_number});
   }else results.push({state:needs?'PENDING':'UNCHANGED',upstream_number:w.request.upstream_number});
   await hooks.notify(w.request,{state:'WATCHING',snapshot_url:w.snapshot_url,expires_at:w.expires_at,last_checked_at:now,reason:needs?'A newer upstream revision was seen; its new Check is pending. The previous revision is out of date.':undefined});
   w.last_checked_at=now;await storage.put(key,JSON.stringify(w));
  }catch(e){results.push({state:'RETRY_LATER',reason:/^[A-Z0-9_]+$/.test(e.message)?e.message:'METADATA_READ_INCOMPLETE'});}
 }
 return results;
}
