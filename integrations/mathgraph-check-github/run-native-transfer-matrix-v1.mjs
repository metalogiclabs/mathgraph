// Zero-API execution: no model client, no credentials, frozen method only.
import {readFile,writeFile,mkdir} from 'node:fs/promises';import {join,resolve} from 'node:path';import {createHash} from 'node:crypto';
import {runNativeMatrix,writeMatrixEvent} from './native-transfer-matrix-v1.mjs';
import {freshNativeRunner} from './fresh-native-runner-v1.mjs';
import {verifyFresh,renderCandidate} from './mention-fresh-proof-v1.mjs';
const bytes=await readFile(new URL('./fixtures/native-transfer-matrix-v1.json',import.meta.url));
const matrix=JSON.parse(bytes),engine=await readFile(new URL('./mention-fresh-proof-v1.mjs',import.meta.url));
const digest=createHash('sha256').update(bytes).digest('hex');
if(digest!=='df3c0f61aa00f36d2ce945c49bedb346ab6da0c2f1a5b05bd4530d6bab09f625'||createHash('sha256').update(engine).digest('hex')!==matrix.engine_sha256)throw Error('MATRIX_FROZEN_INPUT_CHANGED');
const output=resolve(process.env.RUNNER_TEMP??'/tmp','mathgraph-native-matrix');await mkdir(output,{recursive:true});
await writeFile(join(output,'frozen-matrix.json'),JSON.stringify({preregistration:'f664a92c84446a2ac2da46eecef569a282f37c72',matrix_sha256:digest,matrix},null,2));
if(process.argv.includes('--freeze-only')){console.log(JSON.stringify({status:'MATRIX_FROZEN',cases:matrix.cases.length,api_calls:0,matrix_sha256:digest}));process.exit();}
let traceIndex=0,evidenceIndex=0;
const runner=async label=>{
 const directory=join(output,label);await mkdir(directory,{recursive:true});
 const execute=await freshNativeRunner({directory,dependencyDirectory:process.env.MATHGRAPH_NATIVE_DEPS});
 return async(name,text,options)=>{const r=await execute(name,text,options);await writeMatrixEvent(output,'trace',++traceIndex,{label,unit:name,...r});return r;};
};
try{
const control=await runner('controls');const positive=await control('Sanity','import Mathlib\nexample : True := by trivial\n'),negative=await control('Negative','import Mathlib\nexample : False := by trivial\n');
if(positive.code!==0||negative.code!==1)throw Error('MATRIX_NATIVE_CONTROLS_FAILED');
 const result=await runNativeMatrix({matrix,engine,verify:async(frozen,proof,label)=>{
  const r=await verifyFresh({frozen,proof,run:await runner(label)});
  if(r.status==='ORIGINAL_TARGET_VERIFIED')await writeFile(join(output,label+'.lean'),renderCandidate(frozen,proof));
  return r;
 },onEvidence:async item=>{await writeMatrixEvent(output,'evidence',++evidenceIndex,item);if(item.stage==='RESULT')console.log(JSON.stringify({id:item.id,outcome:item.result.outcome,expected:item.result.expected,expectation_met:item.result.expectation_met}));}});
 await writeFile(join(output,'matrix-result.json'),JSON.stringify({run_id:process.env.GITHUB_RUN_ID,source_sha:process.env.GITHUB_SHA,matrix_sha256:digest,...result},null,2));
 console.log(JSON.stringify({status:'MATRIX_EXECUTION_COMPLETED',cases:result.results.length,repaired:result.repaired,expectations_met:result.expectations_met,api_calls:0}));
}catch(e){await writeFile(join(output,'incomplete.json'),JSON.stringify({status:'UNKNOWN',api_calls:0,error:/^[A-Z0-9_]+$/.test(e.message)?e.message:'NATIVE_MATRIX_INCOMPLETE'},null,2));throw e;}
