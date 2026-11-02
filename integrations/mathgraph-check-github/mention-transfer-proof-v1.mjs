// Prospective orchestration only: the existing proof engine is byte-frozen.
import {createHash} from 'node:crypto';
import {freezeTheorem,runFreshComparison,repairWithNativePortfolio} from './mention-fresh-proof-v1.mjs';
const hash=x=>createHash('sha256').update(x).digest('hex');
const ensure=(ok,code)=>{if(!ok)throw Error(code);};
export function bindTransferInputs({protocolBytes,binding,engine,source}){
 ensure(binding?.preregistration_commit==='4d0405ef933626e791df488bd07afb5fe7015d94'&&/^[a-f0-9]{64}$/.test(binding.source_sha256)&&/^[a-f0-9]{64}$/.test(binding.target_sha256),'TRANSFER_PREREGISTRATION_REFUSED');
 ensure(protocolBytes&&hash(protocolBytes)==='0b144f9d3bfed1390da3dc4f88c6e4bf6ef8a6f77d1aceaf647091b79106fe33','FROZEN_PROTOCOL_CHANGED');
 const protocol=JSON.parse(protocolBytes.toString('utf8'));
 ensure(hash(engine)===protocol.engine_sha256,'FROZEN_ENGINE_CHANGED');
 ensure(hash(source)===binding.source_sha256,'TRANSFER_SOURCE_CHANGED');
 const frozen=freezeTheorem(source.toString('utf8'),{...protocol.source,sha256:binding.source_sha256});
 ensure(frozen.target_sha256===binding.target_sha256,'TRANSFER_TARGET_CHANGED');
 return frozen;
}
export function authorizeTransferRun(current,history){
 ensure(current?.event==='push'&&current.run_attempt===1&&current.actor?.id===32909488&&current.head_branch==='research/mathgraph-proof-transfer-v1-20261102'&&current.path==='.github/workflows/mathgraph-fresh-transfer-v1.yml'&&Array.isArray(history?.workflow_runs)&&history.total_count===history.workflow_runs.length&&history.workflow_runs.some(r=>r.id===current.id)&&history.workflow_runs.filter(r=>r.id<=current.id).length===1,'TRANSFER_EPOCH_REFUSED');return true;
}
export async function runTransferComparison({frozen,generate,verify,onProposal,onRaw=async()=>{},onNativeAttempt=async()=>{}}){
 const raw=await runFreshComparison({frozen,generate,verify,onProposal});
 await onRaw(raw);
 const base={schema:'mathgraph.frozen-transfer-comparison.v1',raw,unique_api_calls:raw.unique_api_calls,llm_alone:raw.llm_alone,mathgraph:raw.mathgraph,native_attempts:0,prospective:true};
 if(raw.unique_api_calls===1)return {...base,transfer:'SHARED_FIRST_PASSED_NO_TRANSFER_EVIDENCE'};
 if(raw.mathgraph.status==='ORIGINAL_TARGET_VERIFIED')return {...base,transfer:'MODEL_FEEDBACK_SUCCESS_NATIVE_REPAIR_UNTESTED'};
 const proposal=raw.proposals.find(p=>p.arm==='native-feedback-revision');
 const repaired=await repairWithNativePortfolio({frozen,proposals:[proposal],diagnostic:raw.mathgraph.diagnostic??'',verify,maxAttempts:2,onAttempt:onNativeAttempt});
 return {...base,transfer:repaired.status==='ORIGINAL_TARGET_VERIFIED'?'FROZEN_NATIVE_REPAIR_TRANSFERRED_ON_ONE_CASE':'NO_FROZEN_NATIVE_REPAIR_TRANSFER_SHOWN',native_attempts:repaired.native_attempts,mathgraph:{...repaired,post_hoc:false,method_predeclared:true}};
}
