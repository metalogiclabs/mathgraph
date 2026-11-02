// Trusted target registry; candidate proof bodies remain untrusted.
import {readFileSync} from 'node:fs';import {createHash} from 'node:crypto';
import {freezeTheorem,renderCandidate,verifyFresh,repairWithNativePortfolio} from './mention-fresh-proof-v1.mjs';
const engine=readFileSync(new URL('./mention-fresh-proof-v1.mjs',import.meta.url));
if(createHash('sha256').update(engine).digest('hex')!=='9bf7a144d0a85bbacd154fcd7cc5c49f072feb251dbe58e654f4fb86cd2d4b92')throw Error('FROZEN_ENGINE_CHANGED');
const bytes=readFileSync(new URL('./fixtures/native-transfer-matrix-v1.json',import.meta.url));
if(createHash('sha256').update(bytes).digest('hex')!=='df3c0f61aa00f36d2ce945c49bedb346ab6da0c2f1a5b05bd4530d6bab09f625')throw Error('FROZEN_GROUP_TARGETS_CHANGED');
const targets=JSON.parse(bytes).cases.filter(x=>['conjugate_power_2','conjugate_power_3','conjugate_power_4','nested_conjugate_cube'].includes(x.id)).map(x=>freezeTheorem(x.source,{kind:'QUALIFIED_CONSTRUCTED_CONTROL',run:41410152881}));
export const groupPath='mathgraph-demo/GroupIdentity.lean';
export const groupBrokenSource=renderCandidate(targets[0],'by group');
export function bindGroupSource(source){
 try{
  if(typeof source!=='string'||Buffer.byteLength(source)>4000)throw Error();
  for(const frozen of targets){const prefix=frozen.prelude+frozen.header+' := ';if(!source.startsWith(prefix))continue;const proof=source.slice(prefix.length).trim();if(!/^by\s+(?:group|rfl|simp\s+only\s+\[pow_succ,\s*pow_zero,\s*mul_one\];\s*group|simp\s+\[pow_two,\s*mul_assoc\])$/.test(proof)||renderCandidate(frozen,proof)!==source)throw Error();return {frozen,proof};}
 }catch{}
 throw Error('UNSUPPORTED_GROUP_SOURCE');
}
export async function nativeGroup({source,run}){
 const {frozen,proof}=bindGroupSource(source);let candidateCode=null;
 const r=await verifyFresh({frozen,proof,run:async(name,text)=>{const result=await run(name,text);if(name==='Candidate')candidateCode=result.code;return result;}});
 const knownFailure=candidateCode===1&&/error: (?:unsolved goals|tactic .rfl. failed)/i.test(r.diagnostic??'');
 return {...r,status:r.status==='UNKNOWN'&&knownFailure?'CLAIM_NOT_ESTABLISHED':r.status,source_compiles:candidateCode===0?true:knownFailure?false:null,original_claim_satisfied:r.status==='ORIGINAL_TARGET_VERIFIED',target_sha256:frozen.target_sha256,target_name:frozen.name};
}
export async function repairGroup({source,run,initial,onAttempt=async()=>{}}){
 const {frozen,proof}=bindGroupSource(source);
 const attempts=[];
 const r=await repairWithNativePortfolio({frozen,proposals:[{proof_body:proof}],diagnostic:initial.diagnostic??'',maxAttempts:2,onAttempt:async item=>{attempts.push(item);await onAttempt(item);},verify:async p=>{const result=await nativeGroup({source:renderCandidate(frozen,p),run});if(result.status==='UNKNOWN')throw Error('GROUP_NATIVE_EXECUTION_INCOMPLETE');return result;}});
 return {source:r.status==='ORIGINAL_TARGET_VERIFIED'?renderCandidate(frozen,r.proof_body):null,receipt:{...r,attempts,post_hoc:false,method_prequalified:true,target_name:frozen.name}};
}
