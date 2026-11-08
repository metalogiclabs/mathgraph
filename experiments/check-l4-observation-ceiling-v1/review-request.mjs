/**
 * Source-qualified review *request*, not reviewer approval or a production
 * trust root. This deliberately preserves two different L4YAML revisions:
 * the frozen production source and the later historical proof source.
 */
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {l4CommentObservationCase} from './case.mjs';

export const REVIEW_REQUEST_SCHEMA='mathgraph.independent-l4-review-request.v1';

export function makeIndependentL4ReviewRequest(){
 const prior=l4CommentObservationCase();
 return {
  schema:REVIEW_REQUEST_SCHEMA,status:'CANDIDATE',terminal_form:null,
  reviewer_decision:'NOT_OBTAINED',reviewer_signature:'NOT_ISSUED',
  permission:'ADVISORY_ONLY',
  claim:'On the frozen L4YAML source, parser-success alone cannot decide whether a YAML source comment contains forbidden raw U+0001.',
  observation:'TokenParser.parseYaml success',
  normative_requirement:{
   id:'YAML-1.2.2-CHARACTER-SET-U0001',
   source:'https://yaml.org/spec/1.2.2/',section:'5.1 Character Set / production [1] c-printable',
   interpretation:'YAML streams exclude literal U+0001, including a raw U+0001 in a comment; an escaped code point is a different source representation.',
   review_status:'PENDING_INDEPENDENT_REVIEW',
  },
  source:{repository:'metalogiclabs/L4YAML',
   frozen_production_sha:prior.frozen_source_sha,
   source_reference:`https://github.com/metalogiclabs/L4YAML/tree/${prior.frozen_source_sha}`},
  separating_witness:prior.witnesses.map(w=>({
   id:w.id,input_utf8_hex:Buffer.from(w.input,'utf8').toString('hex'),
   parser_success:w.parseYaml_success,no_raw_soh:w.no_raw_soh,
  })),
  finite_universe:prior.universe,
  proof:{...prior.proof,
   run_url:`https://github.com/metalogiclabs/L4YAML/actions/runs/${prior.proof.run}`,
   artifact_id:13593491176,
   proof_replay:'NOT_PERFORMED',
   byte_corroboration:'HISTORICALLY_VERIFIED_SEPARATELY',
   theorem_claim_scope:'No total iff of frozen parser acceptance with any language satisfying NoRawSOH; does not define the complete YAML 1.2.2 grammar.',
  },
  review_tasks:[
   {id:'NORMATIVE_REQUIREMENT',status:'PENDING',
    question:'Does YAML 1.2.2 section 5.1 exclude literal U+0001 in this source position, and is NoRawSOH a necessary constraint on accepted YAML streams?',
    method:'Independently inspect the authoritative normative production c-printable and the applicability of the character-set rule to comment text.'},
   {id:'FROZEN_RUNTIME_BEHAVIOR',status:'PENDING',
    question:'At precisely the frozen production commit, does TokenParser.parseYaml report success for both input byte strings 23 61 and 23 01?',
    method:'Checkout the pinned L4YAML production commit, replay the real parser on both byte inputs and preserve their exact outputs and toolchain identification.'},
   {id:'LEAN_THEOREM_AND_CONTROLS',status:'PENDING',
    question:'Does the actual named theorem, at the separate proof commit, establish the limited no-iff claim under the recorded axioms and does the negative control fail?',
    method:'Retrieve artifact 13593491176 from run 42420433923; independently hash the original ZIP, read proof logs and source, and if possible rerun Lean with pinned build.'},
   {id:'CLAIM_TO_EVIDENCE_FIDELITY',status:'PENDING',
    question:'Do the normative requirement, the actual frozen parser behavior, the theorem statement and the observation-only impossibility claim refer to the same meaning and valid scope?',
    method:'Inspect the two-byte witness and proof statement together; reject any promotion to complete YAML grammar, all parser behavior, or a different repository or source revision.'},
  ],
  live_admission:{status:'NOT_AUTHORIZED',
   reason:'REVIEWED_SOURCE_NOT_CURRENT_MATHGRAPH_PR_HEAD',
   boundary:'The current MathGraph PR-head-only signed projection consumer cannot treat historical L4YAML witness rows as if they came from a MathGraph source head. External review and separately authenticated cross-repository source binding are both still required.'},
  complete_yaml_grammar:'UNKNOWN',
  next_action:'OBTAIN_INDEPENDENT_REVIEW_DECISIONS_AND_NATIVE_REPLAY_BEFORE_SIGNING_OR_ACTIVATION',
 };
}

if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 process.stdout.write(JSON.stringify(makeIndependentL4ReviewRequest(),null,2)+'\n');
}
