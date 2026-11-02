// Explicitly operator-invoked local runner. Never call on GitHub PR-supplied
// executable sources unless a separately reviewed sandbox has been provided.
import {createHash} from 'node:crypto';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {mkdtemp,readFile,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {bindFormalPair,assessSemantEq} from './generic-claim-audit-v1.mjs';
import {inspectPinnedLeanEnvironment} from './generic-lean-environment-v1.mjs';

const exec=promisify(execFile);
const sha256=s=>createHash('sha256').update(s).digest('hex');
const MAX_WALL_MS=180000;
const base=b=>({...b,formal_statement_relation:'UNKNOWN',execution_status:'ENVIRONMENT_UNAVAILABLE',native_exit_code:null,
 input_sha256:null,output_sha256:null,tool_git:null,raw_output_jsonl:null,raw_input_jsonl:null,
 candidate_source_build:'NOT_RUN',intent_fidelity:'UNKNOWN',evidence_warrant:'UNKNOWN'});

export async function runGenericSemantEq({reference,candidate,expectedReferenceSha,projectDir,timeoutMs=60000}={}){
 const startedAt=new Date().toISOString();
 const startTime=performance.now();
 const binding=bindFormalPair({reference,candidate,expectedReferenceSha});
 const unknown=base(binding);
 if(typeof projectDir!=='string'||!projectDir||!Number.isInteger(timeoutMs)||timeoutMs<1000||timeoutMs>MAX_WALL_MS)
  return {...unknown,reason:'INVALID_PROJECT_OR_TIMEOUT'};
 const env=await inspectPinnedLeanEnvironment(projectDir);
 if(!env.ok)return {...unknown,reason:env.reason,...env};
 const {cwd,tool_git:revision,mathlib_git:mathlibGit,
  lake_manifest_sha256:manifestSha,lean_toolchain_sha256:toolchainSha,
  lean_version:leanVersion,lake_version:lakeVersion,
  semanteq_executable_sha256:binarySha}=env;
 let temporary;
 const input=JSON.stringify({id:binding.case_id,reference:reference.source,candidate:candidate.source})+'\n';
 const inputHash=sha256(input);
 try{
  temporary=await mkdtemp(join(tmpdir(),'mathgraph-generic-semanteq-'));
  const inputFile=join(temporary,'input.jsonl');
  const outputFile=join(temporary,'output.jsonl');
  await writeFile(inputFile,input,{flag:'wx'});
  const args=['env','.lake/build/bin/semanteq','--timeout','12',inputFile,outputFile];
  let stdout='',stderr='',exitCode=0,failed=false;
  try{
   const output=await exec('lake',args,{cwd,timeout:timeoutMs,maxBuffer:1048576,env:process.env});
   stdout=output.stdout;stderr=output.stderr;
  }catch(e){
   failed=true;exitCode=typeof e.code==='number'?e.code:null;
   stdout=String(e.stdout??'');stderr=String(e.stderr??e.message);
  }
  let raw='';
  try{raw=await readFile(outputFile,'utf8');}catch{}
  const result={...unknown,execution_status:failed?'RUN_FAILED':'EXECUTED',
   started_at:startedAt,finished_at:new Date().toISOString(),wall_clock_ms:Math.round(performance.now()-startTime),
   native_exit_code:exitCode,input_sha256:inputHash,output_sha256:raw?sha256(raw):null,
   tool_git:revision,mathlib_git:mathlibGit,lean_version:leanVersion,lake_version:lakeVersion,
   semanteq_executable_sha256:binarySha,
   lake_manifest_sha256:manifestSha,lean_toolchain_sha256:toolchainSha,
   command:['lake',...args],
   stdout,stderr,raw_input_jsonl:input,raw_output_jsonl:raw};
  if(failed)return {...result,reason:'NATIVE_EXECUTION_FAILED'};
  let records;
  try{records=raw.trim().split('\n').map(x=>JSON.parse(x));}catch{return {...result,execution_status:'INVALID_NATIVE_OUTPUT',reason:'JSON_PARSE_FAILED'};}
  if(records.length!==2||!records[0]?._meta||!records[1]||records[1].id!==binding.case_id)
   return {...result,execution_status:'INVALID_NATIVE_OUTPUT',reason:'MISSING_OR_MISMATCHED_CASE'};
  const execution={kind:'LOCAL_NATIVE_SEMANTEQ',exitCode,referenceSha256:binding.reference_sha256,
   candidateSha256:binding.candidate_sha256,toolGit:revision.slice(0,7),
   outputSha256:sha256(raw),command:result.command};
  const audit=assessSemantEq({binding,record:records[1],metadata:records[0]._meta,execution});
  return {...result,...audit,execution_status:'EXECUTED',diagnostic_verdict:audit.diagnostic_verdict,
   raw_result:records[1],tool_metadata:records[0]._meta};
 }catch(e){return {...unknown,execution_status:'RUN_FAILED',reason:String(e.message??e),input_sha256:inputHash,tool_git:revision};}
 finally{if(temporary)await rm(temporary,{recursive:true,force:true});}
}
