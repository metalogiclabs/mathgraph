import {createHash} from 'node:crypto';
import {writeFile} from 'node:fs/promises';import {join} from 'node:path';
import {freezeTheorem,repairWithNativePortfolio} from './mention-fresh-proof-v1.mjs';
export async function writeMatrixEvent(directory,prefix,index,value){
 if(!['evidence','trace'].includes(prefix)||!Number.isSafeInteger(index)||index<1)throw Error('MATRIX_EVENT_REFUSED');
 await writeFile(join(directory,prefix+'-'+index+'.json'),JSON.stringify(value,null,2),{flag:'wx'});
}
export async function runNativeMatrix({matrix,engine,verify,onEvidence=async()=>{}}){
 if(matrix.engine_sha256!=='9bf7a144d0a85bbacd154fcd7cc5c49f072feb251dbe58e654f4fb86cd2d4b92'||createHash('sha256').update(engine).digest('hex')!==matrix.engine_sha256)throw Error('FROZEN_ENGINE_CHANGED');
 if(matrix.api_calls!==0||matrix.max_variants_per_case!==2||!Array.isArray(matrix.cases)||matrix.cases.length>20||new Set(matrix.cases.map(x=>x.id)).size!==matrix.cases.length)throw Error('MATRIX_PROTOCOL_REFUSED');
 const results=[];
 for(const item of matrix.cases){
  const frozen=freezeTheorem(item.source,{kind:'CONSTRUCTED_NATIVE_CONTROL',id:item.id});
  const checkedVerify=async(proof,label)=>{const r=await verify(frozen,proof,label);if(r.diagnostic==='NATIVE_RESOURCE_LIMIT_OR_EXECUTION_INCOMPLETE'){await onEvidence({id:item.id,stage:'INCOMPLETE',label,result:r});throw Error('MATRIX_NATIVE_INCOMPLETE');}return r;};
  const baseline=await checkedVerify(item.proof_body,item.id+'-baseline');
  await onEvidence({id:item.id,stage:'BASELINE',frozen,baseline});
  let repair=null,outcome='BASELINE_ACCEPTED';
  if(baseline.status!=='ORIGINAL_TARGET_VERIFIED'){
   let n=0;
   repair=await repairWithNativePortfolio({frozen,proposals:[{proof_body:item.proof_body}],diagnostic:baseline.diagnostic??'',maxAttempts:2,verify:proof=>checkedVerify(proof,item.id+'-variant-'+(++n)),onAttempt:attempt=>onEvidence({id:item.id,stage:'VARIANT',attempt})});
   repair={...repair,post_hoc:false,method_predeclared:true};
   outcome=repair.status==='ORIGINAL_TARGET_VERIFIED'?'REPAIRED':repair.native_attempts?'NOT_ACCEPTED_VARIANTS':'NOT_ACCEPTED_NO_VARIANTS';
  }
  const result={id:item.id,frozen,baseline,repair,outcome,expected:item.expected,expectation_met:outcome===item.expected};results.push(result);
  await onEvidence({id:item.id,stage:'RESULT',result});
 }
 return {schema:'mathgraph.native-transfer-matrix-result.v1',api_calls:0,scope:'FINITE_CONSTRUCTED_NATIVE_CONTROLS_NOT_PROSPECTIVE_THEOREM_ADVANTAGE',results,expectations_met:results.every(x=>x.expectation_met),repaired:results.filter(x=>x.outcome==='REPAIRED').length};
}
