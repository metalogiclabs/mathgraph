// Separate native proof/consumer replay for OPERATOR-REVIEWED local files.
// The operator, not a candidate or this runner, must authorize the consumer's
// correspondence to the original mathematical research claim.
import {createHash,randomBytes} from 'node:crypto';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {mkdtemp,writeFile,rm} from 'node:fs/promises';
import {join,relative} from 'node:path';
import {bindFormalPair,qualifyOriginalRepair} from './generic-claim-audit-v1.mjs';
import {inspectPinnedLeanEnvironment} from './generic-lean-environment-v1.mjs';
import {buildCandidateProofReferenceAudit,parseCandidateProofReferenceMarker,
 classifyCandidateProofReference} from './generic-candidate-proof-reference-v1.mjs';

const exec=promisify(execFile);
const sha=s=>createHash('sha256').update(s).digest('hex');
const SHA256=/^[0-9a-f]{64}$/;
const MAX_WALL_MS=180000;

function parseAxioms(output,name){
 const quoted=name.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
 const zero=new RegExp(`^'${quoted}' does not depend on any axioms\\s*$`,'m');
 if(zero.test(output))return [];
 const nonzero=new RegExp(`^'${quoted}' depends on axioms: \\[([^\\]]*)\\]\\s*$`,'m');
 const match=output.match(nonzero);
 return match?match[1].split(',').map(a=>a.trim()):null;
}

export async function runGenericLeanConsumer({reference,candidate,expectedReferenceSha,
 consumerSource,expectedConsumerSha,consumerName,candidateName,projectDir,timeoutMs=60000}={}){
 const startedAt=new Date().toISOString(),started=performance.now();
 const binding=bindFormalPair({reference,candidate,expectedReferenceSha});
 if(typeof consumerSource!=='string'||!consumerSource.trim()||
  typeof expectedConsumerSha!=='string'||!SHA256.test(expectedConsumerSha))throw Error('TRUSTED_CONSUMER_REQUIRED');
 if(sha(consumerSource)!==expectedConsumerSha)throw Error('CONSUMER_SHA_MISMATCH');
 if(typeof consumerName!=='string'||!/^[A-Za-z_][\w.']{0,150}$/.test(consumerName))throw Error('CONSUMER_NAME_INVALID');
 if(candidateName!==undefined&&
  (typeof candidateName!=='string'||!/^[A-Za-z_][A-Za-z0-9_'.]{0,150}$/.test(candidateName)))
  throw Error('CANDIDATE_NAME_INVALID');
 const dependencyRequested=typeof candidateName==='string';
 const dependencyUnavailable=dependencyRequested?{
  candidate_declaration_name:candidateName,actual_candidate_proof_term_reference:'UNKNOWN',
  normalized_direct_reference:null,candidate_axioms:null,candidate_dependence:'UNKNOWN'}:{};
 const unavailable={...binding,original_target_status:'UNKNOWN',execution_status:'ENVIRONMENT_UNAVAILABLE',
  candidate_source_build:'NOT_RUN',intent_fidelity:'UNKNOWN',evidence_warrant:'UNKNOWN',
  consumer_sha256:expectedConsumerSha,consumer_name:consumerName,axioms:null,...dependencyUnavailable};
 if(!Number.isInteger(timeoutMs)||timeoutMs<1000||timeoutMs>MAX_WALL_MS)
  return {...unavailable,reason:'INVALID_TIMEOUT'};
 const environment=await inspectPinnedLeanEnvironment(projectDir);
 if(!environment.ok)return {...unavailable,reason:environment.reason,...environment};
 const {cwd}=environment;
 let temporary;
 const trace=[];
 const dependencyMarker=dependencyRequested?`MATHGRAPH_CANDIDATE_REFERENCE_${randomBytes(12).toString('hex')}`:null;
 const auditSource=dependencyRequested?buildCandidateProofReferenceAudit({candidateName,consumerName,
  marker:dependencyMarker}):`import Consumer\n#print axioms ${consumerName}\n`;
 const runUnit=async(name,withOlean,env)=>{
  const file=join(temporary,`${name}.lean`);
  const args=['env','lean',...(withOlean?['-o',join(temporary,`${name}.olean`)]:[]),file];
  const started=performance.now();
  try{
   const res=await exec('lake',args,{cwd,timeout:timeoutMs,maxBuffer:1048576,env});
   return {unit:name,command:['lake',...args],exit_code:0,stdout:res.stdout,stderr:res.stderr,
    wall_clock_ms:Math.round(performance.now()-started)};
  }catch(e){return {unit:name,command:['lake',...args],exit_code:typeof e.code==='number'?e.code:null,
   stdout:String(e.stdout??''),stderr:String(e.stderr??e.message),
   execution_failed:typeof e.code!=='number',wall_clock_ms:Math.round(performance.now()-started)};}
 };
 try{
  // Use the repo-ignored build tree: parallel SemantEq jobs inspect Git's
  // dirty flag, so an untracked root-level temp folder would invalidate them.
  temporary=await mkdtemp(join(cwd,'.lake/build/mathgraph-native-consumer-'));
  const localEnv={...process.env,LEAN_PATH:temporary+(process.env.LEAN_PATH?`:${process.env.LEAN_PATH}`:'')};
  await Promise.all([
   writeFile(join(temporary,'Candidate.lean'),candidate.source,{flag:'wx'}),
   writeFile(join(temporary,'Consumer.lean'),consumerSource,{flag:'wx'}),
   writeFile(join(temporary,'Audit.lean'),auditSource,{flag:'wx'})
  ]);
  for(const [name,olean] of [['Candidate',true],['Consumer',true],['Audit',false]]){
   const entry=await runUnit(name,olean,localEnv);trace.push(entry);
   if(entry.exit_code!==0||entry.execution_failed)break;
  }
  const sourceReplay={kind:'NATIVE_LEAN',exitCode:trace[0]?.exit_code,
   candidateSha256:binding.candidate_sha256};
  const allCompiled=trace.length===3&&trace.every(x=>x.exit_code===0&&!x.execution_failed);
  const axioms=allCompiled?parseAxioms(trace[2].stdout+trace[2].stderr,consumerName):null;
  const candidateAxioms=dependencyRequested&&allCompiled?
   parseAxioms(trace[2].stdout+trace[2].stderr,candidateName):null;
  const direct=dependencyRequested&&allCompiled?
   parseCandidateProofReferenceMarker(trace[2].stdout,dependencyMarker):null;
  const dependency=dependencyRequested?{
   candidate_declaration_name:candidateName,actual_candidate_proof_term_reference:
    classifyCandidateProofReference({compiled:allCompiled,record:direct,candidateAxioms,consumerAxioms:axioms}),
   normalized_direct_reference:direct,candidate_axioms:candidateAxioms,candidate_dependence:'UNKNOWN',
   generated_audit_sha256:sha(auditSource),native_reference_marker:dependencyMarker
  }:{};
  const consumerReplay={kind:'NATIVE_LEAN',exitCode:allCompiled?0:1,
   referenceSha256:binding.reference_sha256,axioms};
  const claim=qualifyOriginalRepair({binding,sourceReplay,consumerReplay});
  return {...claim,...environment,execution_status:trace.some(x=>x.execution_failed)?'RUN_FAILED':'EXECUTED',
   candidate_source_build:trace[0]?.exit_code===0?'LEAN_ACCEPTED':trace[0]?.execution_failed?'NOT_RUN':'LEAN_REJECTED',
   source_reference_sha256:binding.reference_sha256,consumer_sha256:expectedConsumerSha,
   consumer_name:consumerName,started_at:startedAt,finished_at:new Date().toISOString(),
   wall_clock_ms:Math.round(performance.now()-started),trace,
   source_declares_formal_original:'OPERATOR_ATTESTATION_REQUIRED',
   intent_fidelity:'UNKNOWN',evidence_warrant:'UNKNOWN',...dependency};
 }catch(e){return {...unavailable,...environment,execution_status:'RUN_FAILED',reason:String(e.message??e),trace};}
 finally{if(temporary)await rm(temporary,{recursive:true,force:true});}
}
