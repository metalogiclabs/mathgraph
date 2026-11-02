// Operator-only, first-party native proof-use diagnostic. NEVER invoke on
// untrusted PR-supplied Lean without a separately reviewed execution sandbox.
import {createHash} from 'node:crypto';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {mkdtemp,readFile,rm,writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {basename,join,resolve} from 'node:path';
import {inspectPinnedLeanEnvironment} from './generic-lean-environment-v1.mjs';

const exec=promisify(execFile);
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');

// This parser is not an evidence source; the runner only calls it on the
// freshly captured stdout of its own pinned native process.
export function parseNativeProofVerdict(stdout,stagedPath){
 if(typeof stdout!=='string'||!stdout.trim()||typeof stagedPath!=='string')return null;
 const lines=stdout.trim().split(/\r?\n/);
 if(lines.length!==1)return null;
 let entry;
 try{entry=JSON.parse(lines[0]);}catch{return null;}
 if(!entry||Array.isArray(entry)||typeof entry!=='object'||
  entry.file!==stagedPath||typeof entry.ante!=='string'||!entry.ante||
  typeof entry.goal!=='string'||!entry.goal||
  !['PASS','FAIL'].includes(entry.verdict)||entry.flags!==0||
  !Array.isArray(entry.flagDetails)||!Array.isArray(entry.reasons))return null;
 return entry;
}

export async function runGenericProofRelevance({source,expectedSha,projectDir,timeoutMs=60000}={}){
 const startedAt=new Date().toISOString(),start=performance.now();
 const sourcePath=typeof source==='string'&&source?resolve(source):null;
 const receipt={source_path:sourcePath,source_sha256:null,expected_source_sha256:expectedSha??null,
  proof_binding:'UNBOUND_ADVISORY',verdict:'UNKNOWN',execution_status:'ENVIRONMENT_UNAVAILABLE',
  native_exit_code:null,command:null,stdout:'',stderr:'',native_record:null,
  started_at:startedAt,finished_at:null,wall_clock_ms:null};
 const finish=fields=>({...receipt,...fields,finished_at:new Date().toISOString(),
  wall_clock_ms:Math.round(performance.now()-start)});
 if(!sourcePath||typeof expectedSha!=='string'||!/^[a-f0-9]{64}$/i.test(expectedSha))
  return finish({execution_status:'INVALID_SOURCE_PIN',reason:'EXPECTED_EXACT_SHA256_AND_SOURCE'});
 let bytes;
 try{bytes=await readFile(sourcePath);}catch(e){return finish({execution_status:'SOURCE_UNAVAILABLE',reason:`SOURCE_READ_FAILED:${e.code??e.message}`});}
 const sourceSha=sha(bytes);
 if(sourceSha!==expectedSha.toLowerCase())return finish({source_sha256:sourceSha,
  execution_status:'SOURCE_HASH_MISMATCH',reason:'SOURCE_HASH_MISMATCH'});
 receipt.source_sha256=sourceSha;
 if(typeof projectDir!=='string'||!projectDir||!Number.isInteger(timeoutMs)||timeoutMs<1000||timeoutMs>180000)
  return finish({execution_status:'ENVIRONMENT_UNAVAILABLE',reason:'INVALID_PROJECT_OR_TIMEOUT'});
 const environment=await inspectPinnedLeanEnvironment(projectDir);
 if(!environment.ok)return finish({...environment,execution_status:'ENVIRONMENT_UNAVAILABLE',reason:environment.reason});
 let temporary;
 try{
  // Execute a private immutable-by-convention byte copy so a source-path edit
  // between hashing and execution cannot silently change what was checked.
  temporary=await mkdtemp(join(tmpdir(),'mathgraph-proof-relevance-'));
  const staged=join(temporary,basename(sourcePath).endsWith('.lean')?basename(sourcePath):'Proof.lean');
  await writeFile(staged,bytes,{flag:'wx',mode:0o400});
  const args=['env','.lake/build/bin/semanteq','--raw','--strict','--proof',staged];
  const command=['lake',...args];
  let stdout='',stderr='',exitCode=0,failed=false;
  try{
   const result=await exec('lake',args,{cwd:environment.cwd,env:process.env,timeout:timeoutMs,maxBuffer:1048576});
   stdout=result.stdout;stderr=result.stderr;
  }catch(e){
   failed=true;exitCode=typeof e.code==='number'?e.code:null;
   stdout=String(e.stdout??'');stderr=String(e.stderr??e.message);
  }
  const execution={...environment,command,native_exit_code:exitCode,stdout,stderr,
   stdout_sha256:sha(stdout),stderr_sha256:sha(stderr),staged_source_sha256:sha(await readFile(staged)),
   execution_status:failed?'RUN_FAILED':'EXECUTED'};
  if(failed)return finish({...execution,reason:'NATIVE_EXECUTION_FAILED'});
  const record=parseNativeProofVerdict(stdout,staged);
  if(!record)return finish({...execution,execution_status:'INVALID_NATIVE_OUTPUT',reason:'INVALID_OR_AMBIGUOUS_PROOF_RECORD'});
  return finish({...execution,verdict:record.verdict,native_record:record});
 }catch(e){return finish({...environment,execution_status:'RUN_FAILED',reason:`PROOF_RUN_FAILED:${e.message??e}`});}
 finally{if(temporary)await rm(temporary,{recursive:true,force:true});}
}
