import {spawnSync} from 'node:child_process';import {readFileSync} from 'node:fs';import {createHash} from 'node:crypto';import {fileURLToPath} from 'node:url';
import {claimProfileFor} from './claim-profile.mjs';
const hash=x=>createHash('sha256').update(x).digest('hex');
const source=JSON.parse(readFileSync(new URL('../../../experiments/check-l4-claim-consumer-v1/claim-source.json',import.meta.url)));
export async function captureClaimSnapshot(request,snapshot,api){
 const p=claimProfileFor(request);if(!p)throw Error('CLAIM_PROFILE_UNSUPPORTED');
 const declaration=await api(`/repos/${p.upstream}/pulls/${p.upstream_pr}`);
 if(typeof declaration.body!=='string'||hash(declaration.body)!==source.body_sha256)throw Error('DECLARED_CLAIM_CHANGED');
 return {...snapshot,upstream_claim:declaration};
}
export function admitClaimResult(receipt,request,context){
 const unknown=reason=>({status:'UNKNOWN',reason,scope:'empty-tail constructor consumer',whole_generator_correctness:'UNKNOWN'});
 if(!claimProfileFor(request)||request.profile.claim_profile!=='empty-tail-v1')return unknown('CLAIM_PROFILE_UNSUPPORTED');
 if(!receipt||receipt.pr!==request.number||JSON.stringify(receipt.context)!==JSON.stringify(context))return unknown('CLAIM_CONTEXT_MISMATCH');
 const r=spawnSync('python3',[fileURLToPath(new URL('./claim-admit.py',import.meta.url))],{input:JSON.stringify({receipt,controller:context.verifier_sha}),encoding:'utf8',timeout:10000,maxBuffer:4000000});
 if(r.error||r.status!==0)return unknown('CLAIM_ADMISSION_INCOMPLETE');
 try{const a=JSON.parse(r.stdout);return a.state==='WARRANTED_BOUNDED'?{...a,status:'SUPPORTED',scope:'two empty-tail constructor APIs; retrospective exact-source contract'}:unknown(a.reason??'CLAIM_NATIVE_INCOMPLETE');}catch{return unknown('CLAIM_ADMISSION_INVALID');}
}
