/**
 * A deliberately narrow L4YAML case for the existing finite quotient gate.
 *
 * Observation: the frozen public TokenParser.parseYaml accepts both inputs.
 * Protected question: does the source contain a forbidden raw U+0001?
 * The second answer differs; no downstream decision based ONLY on parser
 * success can recover the answer for both inputs.
 *
 * Historical Lean qualification is referenced, not rerun here. Only a host
 * which has independently authenticated that proof receipt and this finite
 * universe may authorize an admitted NAMED_OBSTRUCTION response.
 */
import {checkFiniteWarrantQuotient} from
  '../../integrations/mathgraph-check-github/finite-warrant-quotient-v1.mjs';
import {buildAdvisoryCheck} from
  '../../integrations/mathgraph-check-github/advisory-publisher-v1.mjs';

export const L4_PRODUCTION_SHA='64795a8db28ccfdae85082c93b6453001ae9d3e4';
const PROOF_COMMIT='b882e5b298b30b094f4154da7108a45e196cfcd3';
const PROOF_RUN=42420433923;
const PROOF_JOB=128547467405;
const PROOF_THEOREM='MathGraph.WholeSource.CapstoneCommentBoundary.no_normative_iff_on_frozen_runtime';
// GitHub Actions artifact metadata independently checked for run 42420433923.
export const L4_PROOF_ARTIFACT_SHA256='f60e48bc7a9df0e618c9ce6398644a9bbc5da4d4022010528f662f0566a536f3';
export const L4_PROOF_RECEIPT_ID=`metalogiclabs/L4YAML@${PROOF_COMMIT}:run-${PROOF_RUN}:job-${PROOF_JOB}:${PROOF_THEOREM}`;
const SCHEMA='mathgraph.finite-warrant-quotient.v1';
const admittedReports=new WeakSet();

/** Returned as new objects to prevent mutable state leaking between calls. */
export function l4CommentObservationCase(){
 return {
   case_id:'L4-NORMATIVE-RUNTIME',
   observation:'TokenParser.parseYaml success',
   protected_requirement:'NoRawSOH (necessary normative character restriction)',
   semantics:'Raw U+0001 is forbidden; an escaped scalar value is a different source',
   frozen_source_sha:L4_PRODUCTION_SHA,
   proof:{repository:'metalogiclabs/L4YAML',commit:PROOF_COMMIT,run:PROOF_RUN,
     job:PROOF_JOB,theorem:PROOF_THEOREM,artifact_sha256:L4_PROOF_ARTIFACT_SHA256,
     qualification:'HISTORICAL_RECEIPT_NOT_REPLAYED_HERE'},
   witnesses:[
     {id:'legal-comment',input:'#a',parseYaml_success:true,no_raw_soh:true},
     {id:'raw-soh-comment',input:'#\u0001',parseYaml_success:true,no_raw_soh:false},
   ],
   universe:{schema:SCHEMA,scope:'l4yaml-frozen-parser-no-raw-soh',rows:[
     {id:'legal-comment',source_sha:L4_PRODUCTION_SHA,
       alpha_key:'TokenParser.parseYaml:ok',protected_status:'OBSERVED'},
     {id:'raw-soh-comment',source_sha:L4_PRODUCTION_SHA,
       alpha_key:'TokenParser.parseYaml:ok',protected_status:'BLOCKED'},
   ]},
 };
}

const unresolved=reason=>({schema:SCHEMA,status:'UNKNOWN',reason,
  terminal_form:null,universal_preservation:'NOT_ESTABLISHED',
  target_decidability:'UNKNOWN',source_traceability:'UNKNOWN',
  permission:'ADVISORY_ONLY',frozen_parser_normative_iff:'UNKNOWN',
  complete_yaml_grammar:'UNKNOWN',
  required_change:'INDEPENDENTLY_QUALIFY_PROOF_AND_SOURCE'});

/**
 * `authority` MUST be selected by a trusted host, never taken from the
 * affected repository, an AI-produced receipt, or the case manifest.
 * Its digest and proof admission are independent of the case's own bytes.
 */
export function auditL4CommentObservation(authority={}){
 if(!authority||!Array.isArray(authority.qualifiedLeanProofReceiptIds)||
   !authority.qualifiedLeanProofReceiptIds.includes(L4_PROOF_RECEIPT_ID)||
   !Array.isArray(authority.qualifiedArtifactDigests)||
   !authority.qualifiedArtifactDigests.includes(L4_PROOF_ARTIFACT_SHA256))
   return unresolved('INDEPENDENT_LEAN_PROOF_ADMISSION_REQUIRED');
 const report=checkFiniteWarrantQuotient(l4CommentObservationCase().universe,authority);
 if(report.status!=='FINITE_COUNTEREXAMPLE'||
   report.target_decidability!=='TARGET_NOT_DECIDABLE_FROM_PROJECTION')
   return unresolved('INDEPENDENT_FINITE_UNIVERSE_ADMISSION_REQUIRED');
 const accepted=Object.freeze({...report,terminal_form:'NAMED_OBSTRUCTION',
   frozen_parser_normative_iff:'REJECTED',complete_yaml_grammar:'UNKNOWN',
   proof_receipt_id:L4_PROOF_RECEIPT_ID,
   proof_replay_in_this_run:false,
   claim_boundary:'This is the necessary NoRawSOH requirement on the frozen source; it is not the complete YAML syntax or output contract.'});
 admittedReports.add(accepted);
 return accepted;
}

/** Construct a neutral Check Run *preview*; this function never publishes. */
export function previewL4AdvisoryCheck(report,expectedHeadSha){
 if(expectedHeadSha!==L4_PRODUCTION_SHA)throw Error('UNBOUND_SOURCE');
 if(!report||!admittedReports.has(report)||
   report.status!=='FINITE_COUNTEREXAMPLE'||
   report.target_decidability!=='TARGET_NOT_DECIDABLE_FROM_PROJECTION'||
   report.terminal_form!=='NAMED_OBSTRUCTION'||
   report.proof_receipt_id!==L4_PROOF_RECEIPT_ID||
   report.frozen_parser_normative_iff!=='REJECTED'||
   report.complete_yaml_grammar!=='UNKNOWN'||
   report.witness?.left?.id!=='legal-comment'||
   report.witness?.right?.id!=='raw-soh-comment')
   throw Error('UNQUALIFIED_L4_REPORT');
 const generic={source:{repository:'metalogiclabs/L4YAML',head_sha:L4_PRODUCTION_SHA},
   scope:'GITHUB_CHECK_RUN_OBSERVATION_ONLY',permission:'ADVISORY_ONLY',
   status:'BLOCKED',
   results:[{id:'NoRawSOH-comment-source-necessity',status:'BLOCKED'}],
   evidence:[{id:'L4-NORMATIVE-RUNTIME',status:'BLOCKED'}]};
 const built=buildAdvisoryCheck(generic,{
   repository:'metalogiclabs/L4YAML',sha:L4_PRODUCTION_SHA});
 return {...built,name:'MathGraph Check / observation ceiling (advisory)',
   external_id:`mathgraph-l4-observation-ceiling:${L4_PRODUCTION_SHA}`,
   output:{title:'L4YAML frozen-parser observation gap (advisory)',
     summary:built.output.summary+'\n\n'+
       'The same parser-success observation covers both #a and a comment containing raw U+0001. '+
       'No downstream procedure using only that success bit can decide the necessary NoRawSOH condition for both.\n\n'+
       'REJECTED: normative iff at this frozen parser revision. '+
       'UNKNOWN: complete YAML grammar, repaired implementation, and full-source iff.\n\n'+
       'Historical qualified Lean proof: '+L4_PROOF_RECEIPT_ID+'. '+
       'The original native proof was not replayed in this preview. '+
       'No merge permission or universal positive proof certificate.'}};
}
