// Native proof evidence is acquired through the existing authenticated bytes
// collector. No receipt, trust manifest or proof status is read from PR text.
import {collectMathSourceEvidenceWithEnvironment} from './math-source-environment-correlation-v1.mjs';
import {ARTIN_PIN} from './proofnet-artin-replay-v1.mjs';
const unknown=()=>({status:'UNKNOWN',meaning:'UNVERIFIED'});
export function proofObserver({manifests=[],token,fetcher=fetch,collect=collectMathSourceEvidenceWithEnvironment}={}){
 const trusted=structuredClone(manifests);
 return async snapshot=>{
  if(!Array.isArray(trusted))return unknown();
  const selected=trusted.filter(m=>m?.repository===snapshot.repository&&m.pr===snapshot.number&&m.trusted?.headSha===snapshot.sha);
  if(!selected.length)return {status:'NOT_CONFIGURED_FOR_SOURCE',meaning:'UNVERIFIED'};
  if(selected.length!==1)return unknown();
  const manifest=selected[0];let r;
  try{r=await collect({...manifest,token,fetcher});}catch{return unknown();}
  if(r?.schema!=='mathgraph.artin-environment-correlation.v1'||r.status!=='ENVIRONMENT_AND_REPLAY_CORRELATED'||r.permission!=='ADVISORY_ONLY'||r.intent_verification!=='NOT_ESTABLISHED'||r.conclusion!=='neutral'||r.subject?.repository!==snapshot.repository||r.subject?.pr!==snapshot.number||r.subject?.head_sha!==snapshot.sha||r.replay?.status!=='PINNED_REPLAY_OBSERVED'||r.replay.run_id!==manifest.runId||!Number.isSafeInteger(r.replay.run_id)||r.replay.run_id<1||!Number.isSafeInteger(r.replay.run_attempt)||r.replay.run_attempt<1)return unknown();
  return {status:'NATIVE_REPLAY_OBSERVED',theorem:ARTIN_PIN.theorem,meaning:'UNVERIFIED',boundary:'PINNED_ARTIN_THEOREM_ONLY',run_id:r.replay.run_id,run_attempt:r.replay.run_attempt,run_url:'https://github.com/'+snapshot.repository+'/actions/runs/'+r.replay.run_id};
 };
}
