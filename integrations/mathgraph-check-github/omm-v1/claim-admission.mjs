// Bounded OMM evidence bridge. This module never executes source or authenticates
// GitHub itself: the caller must obtain request identities and both independent
// artifact pins from the trusted Check controller, not PR-controlled material.
import {createHash} from 'node:crypto';

const SHA40=/^[a-f0-9]{40}$/;
const SHA256=/^[a-f0-9]{64}$/;
const LEAN_NAME=/^[A-Za-z_][A-Za-z0-9_'.]{0,150}$/;
const STANDARD_AXIOMS=new Set(['propext','Classical.choice','Quot.sound']);

const digest=s=>createHash('sha256').update(s).digest('hex');
const same=(left,right,keys)=>keys.every(key=>left?.[key]===right?.[key]);
const cleanAxioms=xs=>Array.isArray(xs)&&xs.every(x=>typeof x==='string'&&STANDARD_AXIOMS.has(x))&&new Set(xs).size===xs.length;
const validExit=step=>step&&Number.isInteger(step.exit_code)&&step.execution_failed!==true;

function unknown(reason){return {schema:'mathgraph.omm.claim-assessment.v1',status:'UNKNOWN',reason,
 candidate_proof:'UNKNOWN',original_target:'UNKNOWN',formal_statement_relation:'UNKNOWN',
 intent_fidelity:'UNKNOWN',evidence_warrant:'UNKNOWN',candidate_dependence:'UNKNOWN',
 candidate_axiom_status:'UNKNOWN',repair_permission:'DENIED'};}

function pinnedJson(bytes,pin){
 if(typeof bytes!=='string'||bytes.length>2_000_000||!SHA256.test(pin??'')||digest(bytes)!==pin)return null;
 try{return JSON.parse(bytes);}catch{return null;}
}

/** Only a bounded native-replay observation; never paper-to-Lean intent warrant. */
export function assessOmmClaim({request,contractBytes,expectedContractSha256,receiptBytes,expectedReceiptSha256}={}){
 if(request?.schema!=='mathgraph.omm.request.v1'||request.command!=='check'||
    !Number.isSafeInteger(request.number)||request.number<1||
    !/^[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+$/.test(request.repository??'')||
    !SHA40.test(request.head_sha??'')||!SHA40.test(request.base_sha??'')||
    !SHA256.test(request.candidate_source_sha256??''))return unknown('REQUEST_NOT_AUTHENTICATED_OR_NOT_SUPPORTED');

 const contract=pinnedJson(contractBytes,expectedContractSha256);
 if(!contract||contract.schema!=='mathgraph.omm.claim-contract.v1'||
    !same(contract,request,['repository','number','head_sha','base_sha'])||
    !SHA256.test(contract.reference_sha256??'')||
    !SHA256.test(contract.candidate_sha256??'')||
    !SHA256.test(contract.consumer_sha256??'')||
    !LEAN_NAME.test(contract.consumer_name??'')||!LEAN_NAME.test(contract.candidate_name??'')||
    !SHA40.test(contract.mathlib_git??'')||
    !SHA256.test(contract.lean_toolchain_sha256??'')||
    contract.candidate_sha256!==request.candidate_source_sha256)
  return unknown('TRUSTED_CLAIM_CONTRACT_MISSING_OR_SOURCE_CHANGED');

 const receipt=pinnedJson(receiptBytes,expectedReceiptSha256);
 if(!receipt||receipt.schema!=='mathgraph.omm.native-receipt.v1'||
    !same(receipt,request,['repository','number','head_sha','base_sha']))
  return unknown('NATIVE_RECEIPT_MISSING_OR_CONTEXT_CHANGED');

 const n=receipt.native;
 if(!n||!same(n,contract,['candidate_sha256','consumer_sha256','consumer_name','mathlib_git','lean_toolchain_sha256'])||
    n.candidate_declaration_name!==contract.candidate_name||
    n.source_reference_sha256!==contract.reference_sha256||n.execution_status!=='EXECUTED'||
    !Array.isArray(n.trace)||n.trace.length<2||n.trace.length>3||
    n.trace[0]?.unit!=='Candidate'||n.trace[1]?.unit!=='Consumer'||
    n.trace.some(step=>!step||typeof step.unit!=='string'||step.execution_failed===true))
  return unknown('NATIVE_EXECUTION_OR_ENVIRONMENT_NOT_QUALIFIED');

 if(!validExit(n.trace[0])||n.trace[0].exit_code!==0||n.candidate_source_build!=='LEAN_ACCEPTED')
  return unknown('CANDIDATE_NOT_COMPILED');

 let originalTarget='UNKNOWN';
 if(validExit(n.trace[1])&&n.trace[1].exit_code!==0&&n.original_target_status!=='NATIVE_CONSUMER_ACCEPTED')
  originalTarget='NOT_ESTABLISHED_IN_THIS_REPLAY';
 else if(n.trace.length===3&&n.trace[2]?.unit==='Audit'&&validExit(n.trace[2])&&
    n.trace[1].exit_code===0&&n.trace[2].exit_code===0&&
    n.original_target_status==='NATIVE_CONSUMER_ACCEPTED'&&
    cleanAxioms(n.axioms)&&cleanAxioms(n.candidate_axioms))
  originalTarget='CONSUMER_ACCEPTED';

 return {schema:'mathgraph.omm.claim-assessment.v1',status:'NATIVE_RECEIPT_BOUND',
  candidate_proof:'LEAN_COMPILED',original_target:originalTarget,
  // SemantEq and source-to-paper authority are distinct future admissions.
  formal_statement_relation:'UNKNOWN',intent_fidelity:'UNKNOWN',evidence_warrant:'UNKNOWN',
  candidate_dependence:'UNKNOWN',candidate_axiom_status:cleanAxioms(n.candidate_axioms)?'STANDARD_ONLY':'UNKNOWN',
  repair_permission:'DENIED',repository:request.repository,number:request.number,
  head_sha:request.head_sha,base_sha:request.base_sha,
  reference_sha256:contract.reference_sha256,candidate_sha256:contract.candidate_sha256,
  consumer_sha256:contract.consumer_sha256,contract_sha256:expectedContractSha256,
  native_receipt_sha256:expectedReceiptSha256,
  reason:originalTarget==='NOT_ESTABLISHED_IN_THIS_REPLAY'?'ORIGINAL_TARGET_CONSUMER_REJECTED':
    originalTarget==='CONSUMER_ACCEPTED'?'NATIVE_ORIGINAL_TARGET_REPLAY_ACCEPTED':'ORIGINAL_TARGET_AUDIT_INCOMPLETE'};
}
