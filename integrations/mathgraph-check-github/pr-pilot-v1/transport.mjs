import {createHash,sign,verify,createPublicKey} from 'node:crypto';
import {profileFor,commandOf} from './policy.mjs';
const ensure=(b,c)=>{if(!b)throw Error(c);};
export function canonical(value){if(value===null||typeof value!=='object')return JSON.stringify(value);if(Array.isArray(value))return '['+value.map(canonical).join(',')+']';return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+canonical(value[k])).join(',')+'}';}
export function signedDispatch(request,key,now=Date.now()){
 const value={...request,issued_at:now};return {request:value,signature:sign('RSA-SHA256',Buffer.from(canonical(value)),key).toString('base64')};
}
export function verifyDispatch(payload,key,now=Date.now()){
 ensure(payload&&typeof payload.signature==='string'&&payload.signature.length<1000,'DISPATCH_UNSIGNED');
 const r=payload.request;ensure(r&&Number.isSafeInteger(r.issued_at)&&now-r.issued_at>=-60000&&now-r.issued_at<=7200000,'DISPATCH_EXPIRED');
 ensure(verify('RSA-SHA256',Buffer.from(canonical(r)),createPublicKey(key),Buffer.from(payload.signature,'base64')),'DISPATCH_SIGNATURE_INVALID');profileFor(r.repository);return r;
}
export function pilotEvent(e,event,delivery){
 try{profileFor(e?.repository?.full_name);}catch{return null;}
 if(!/^[a-f0-9-]{16,80}$/i.test(delivery??'')||!Number.isSafeInteger(e.installation?.id)||e.installation.id<1)return null;
 const common={schema:'mathgraph.pr-pilot.delivery.v1',repository:e.repository.full_name,installationID:e.installation.id,delivery};
 if(event==='issue_comment'&&e.action==='created'&&e.issue?.pull_request&&e.sender?.type==='User'&&e.comment?.user?.type==='User'&&e.sender.id===e.comment.user.id&&commandOf(e.comment.body)&&Number.isSafeInteger(e.comment.id)&&Number.isSafeInteger(e.issue.number))return {...common,number:e.issue.number,comment_id:e.comment.id,command:commandOf(e.comment.body),action:'command'};
 const pr=e.pull_request;if(event==='pull_request'&&['synchronize','edited','closed'].includes(e.action)&&pr?.base?.repo?.full_name===common.repository&&pr.head?.repo?.full_name===common.repository&&Number.isSafeInteger(pr.number)&&/^[a-f0-9]{40}$/.test(pr.head.sha??''))return {...common,number:pr.number,head_sha:pr.head.sha,action:e.action==='edited'?'synchronize':e.action,previous_sha:e.before};
 return null;
}
export class PilotBudget{
 constructor(ctx){this.ctx=ctx;}
 async fetch(request){
  if(request.method!=='POST')return Response.json({status:'INVALID'},{status:400});let r;try{r=await request.json();}catch{return Response.json({status:'INVALID'},{status:400});}
  if(!/^[a-f0-9]{64}$/.test(r.key??'')||![49,98].includes(r.cents)||!/^20[0-9]{2}-[01][0-9]-[0-3][0-9]$/.test(r.day??''))return Response.json({status:'INVALID'},{status:400});
  const result=await this.ctx.storage.transaction(async t=>{
   const id='day:'+r.day,ledger=await t.get(id)??{used:0,keys:{}};
   if(Object.hasOwn(ledger.keys,r.key))return {status:'DUPLICATE',reserved_cents:ledger.keys[r.key],used_cents:ledger.used};
   if(ledger.used+r.cents>1000)return {status:'BUDGET_EXHAUSTED',used_cents:ledger.used};
   ledger.keys[r.key]=r.cents;ledger.used+=r.cents;await t.put(id,ledger);return {status:'RESERVED',reserved_cents:r.cents,used_cents:ledger.used};
  });return Response.json(result);
 }
}
export const reservationKey=r=>createHash('sha256').update(`${r.repository}#${r.number}@${r.head_sha}~${r.base_sha}:${r.command}:${r.comment_id}`).digest('hex');
