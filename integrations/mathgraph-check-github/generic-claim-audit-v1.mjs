// Operator-side contract for formal-statement comparison. This is NOT an
// authenticated mathematical review or a production PR source executor.
import {createHash} from 'node:crypto';

const SHA256=/^[a-f0-9]{64}$/;
const ALLOWED_AXIOMS=new Set(['propext','Classical.choice','Quot.sound']);
const NATIVE_EQUIVALENCE=new Set(['ExactMatch','DefEq','EquivalentRestricted']);
const sha256=value=>createHash('sha256').update(value).digest('hex');

export function bindFormalPair({reference,candidate,expectedReferenceSha}={}){
 if(typeof expectedReferenceSha!=='string'||!SHA256.test(expectedReferenceSha))throw Error('EXPECTED_REFERENCE_SHA_REQUIRED');
 for(const item of [reference,candidate]){
  if(!item||typeof item.source!=='string'||!item.source.trim())throw Error('SOURCE_REQUIRED');
  if(typeof item.path!=='string'||!item.path||item.path.length>512)throw Error('SOURCE_PATH_REQUIRED');
 }
 const referenceSha=sha256(reference.source);
 if(referenceSha!==expectedReferenceSha)throw Error('REFERENCE_SHA_MISMATCH');
 const candidateSha=sha256(candidate.source);
 return Object.freeze({
  case_id:`formal:${referenceSha.slice(0,16)}:${candidateSha.slice(0,16)}`,
  reference_sha256:referenceSha,candidate_sha256:candidateSha,
  reference_path:reference.path,candidate_path:candidate.path,
  formal_statement_relation:'NOT_RUN',candidate_source_build:'NOT_RUN',
  intent_fidelity:'UNKNOWN',evidence_warrant:'UNKNOWN'
 });
}

function cleanExecution(binding,metadata,execution){
 return execution?.kind==='LOCAL_NATIVE_SEMANTEQ'&&execution?.exitCode===0&&
  execution.referenceSha256===binding.reference_sha256&&
  execution.candidateSha256===binding.candidate_sha256&&
  typeof execution.outputSha256==='string'&&SHA256.test(execution.outputSha256)&&
  Array.isArray(execution.command)&&execution.command.length>0&&
  metadata?.tool==='semanteq'&&metadata?.version==='v1.4.0'&&
  metadata?.git==='f927670'&&metadata?.dirty===false&&
  execution.toolGit===metadata.git;
}

export function assessSemantEq({binding,record,metadata,execution}={}){
 if(!binding||typeof binding.case_id!=='string')throw Error('BOUND_PAIR_REQUIRED');
 const trustworthy=cleanExecution(binding,metadata,execution)&&
  record?.id===binding.case_id&&record?.reference?.ok===true&&record?.candidate?.ok===true;
 return {
  ...binding,
  formal_statement_relation:trustworthy&&NATIVE_EQUIVALENCE.has(record.verdict)
   ?'NATIVE_CERTIFIED_EQUIVALENT':'UNKNOWN',
  diagnostic_verdict:trustworthy?record.verdict:'UNTRUSTED_OR_INCOMPLETE_EXECUTION',
  tool_provenance:trustworthy?{name:metadata.tool,version:metadata.version,git:metadata.git,
   output_sha256:execution.outputSha256,command:execution.command}:null,
  // SemantEq ignores candidate proof bodies and does not authenticate source intent.
  candidate_source_build:'NOT_RUN',intent_fidelity:'UNKNOWN',evidence_warrant:'UNKNOWN'
 };
}

export function qualifyOriginalRepair({binding,sourceReplay,consumerReplay}={}){
 if(!binding||typeof binding.case_id!=='string')throw Error('BOUND_PAIR_REQUIRED');
 const cleanAxioms=Array.isArray(consumerReplay?.axioms)&&
  new Set(consumerReplay.axioms).size===consumerReplay.axioms.length&&
  consumerReplay.axioms.every(x=>ALLOWED_AXIOMS.has(x));
 const clean=sourceReplay?.kind==='NATIVE_LEAN'&&sourceReplay?.exitCode===0&&
  sourceReplay?.candidateSha256===binding.candidate_sha256&&
  consumerReplay?.kind==='NATIVE_LEAN'&&consumerReplay?.exitCode===0&&
  consumerReplay?.referenceSha256===binding.reference_sha256&&cleanAxioms;
 return {
  ...binding,
  original_target_status:clean?'NATIVE_CONSUMER_ACCEPTED':'UNKNOWN',
  axioms:clean?consumerReplay.axioms:null,
  // Still no source-to-paper approval, independent review, or authenticated receipt.
  intent_fidelity:'UNKNOWN',evidence_warrant:'UNKNOWN'
 };
}
