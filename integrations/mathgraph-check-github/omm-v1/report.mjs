// Neutral OMM Passport projection. The caller supplies the source-bound
// assessment; this view is not an independent evidence authenticator.
const REPO=/^[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+$/;
const SHA40=/^[a-f0-9]{40}$/;
const SHA256=/^[a-f0-9]{64}$/;
const RUN=/^https:\/\/github\.com\/metalogiclabs\/mathgraph\/actions\/runs\/[1-9][0-9]*$/;

function validateRequest(r){
 if(!REPO.test(r?.repository??'')||!Number.isSafeInteger(r.number)||r.number<1||
   !SHA40.test(r.head_sha??'')||!SHA40.test(r.base_sha??''))throw Error('INVALID_OMM_REPORT_SOURCE');
}
const compiled=s=>s==='LEAN_COMPILED'?'Compiled':'UNKNOWN';
const target=s=>({CONSUMER_ACCEPTED:'Accepted by native Lean replay',
  NOT_ESTABLISHED_IN_THIS_REPLAY:'Not established in this replay',UNKNOWN:'UNKNOWN'}[s]??'UNKNOWN');

export function ommClaimView(assessment,request){
 validateRequest(request);
 const observed=assessment?.status==='NATIVE_RECEIPT_BOUND'&&assessment.head_sha!==undefined&&
   assessment.head_sha===request.head_sha&&assessment.base_sha===request.base_sha;
 // An unrelated or stale artifact cannot be rendered as an observed success.
 const proof=observed?assessment.candidate_proof:'UNKNOWN';
 const original=observed?assessment.original_target:'UNKNOWN';
 const title=original==='CONSUMER_ACCEPTED'?'Original-target consumer accepted':
   original==='NOT_ESTABLISHED_IN_THIS_REPLAY'?'Original target not established in this replay':'Check incomplete';
 return {title,summary:proof==='LEAN_COMPILED'?'Lean candidate compiled; the original target is assessed separately.':
   'The evidence is incomplete or stale. No native proof acceptance is claimed.',
  candidate_proof:proof,original_target:original,formal_statement_relation:'UNKNOWN',
  candidate_axiom_status:observed&&assessment.candidate_axiom_status==='STANDARD_ONLY'?'STANDARD_ONLY':'UNKNOWN',
  candidate_dependence:'UNKNOWN',intent_fidelity:'UNKNOWN',evidence_warrant:'UNKNOWN',
  scope:'One source- and receipt-pinned native consumer replay. Formal statement equivalence: UNKNOWN. Human mathematical intent: UNKNOWN. This is NOT mathematical inequivalence, proof necessity, or acceptance of an author-specified claim.',
  fix:{available:false,reason:'No automatic repair is qualified for OMM Lean claims.'},
  next:original==='NOT_ESTABLISHED_IN_THIS_REPLAY'?'Inspect the original-target consumer and exact source; seek independent claim approval before proposing a repair.':
    original==='CONSUMER_ACCEPTED'?'Have an independent reviewer approve that the formal target represents the intended mathematics.':
    'Recheck the current revision with a separately authorized claim contract and complete native evidence.'};
}

export function formatOmmClaimReport(assessment,request,runUrl){
 const v=ommClaimView(assessment,request);
 if(!RUN.test(runUrl??''))throw Error('INVALID_EVIDENCE_LINK');
 const observed=assessment?.status==='NATIVE_RECEIPT_BOUND'&&assessment.head_sha===request.head_sha&&assessment.base_sha===request.base_sha;
 const pins=observed?[
   ['Trusted original source',assessment.reference_sha256],
   ['Candidate source',assessment.candidate_sha256],
   ['Consumer source',assessment.consumer_sha256],
   ['Claim contract',assessment.contract_sha256],
   ['Native receipt',assessment.native_receipt_sha256]
 ].filter(([,v])=>SHA256.test(v??'')):[];
 return ['### MathGraph Check · Open Math Model',
   `**${v.title}**`,
   `[${request.repository}#${request.number}](https://github.com/${request.repository}/pull/${request.number})`,
   `Head: \`${request.head_sha}\` · Base: \`${request.base_sha}\``,
   '| Assurance axis | Observation |','|---|---|',
   `| Lean candidate | ${compiled(v.candidate_proof)} |`,
   `| Candidate axioms | ${v.candidate_axiom_status==='STANDARD_ONLY'?'Standard only':'UNKNOWN'} |`,
   `| Original-target consumer | ${target(v.original_target)} |`,
   '| Candidate proof necessity | UNKNOWN |',
   '| Formal-statement relation | UNKNOWN |',
   '| Human mathematical intent | UNKNOWN |',
   '| Independent evidence warrant | UNKNOWN |',
   '',v.scope,'',`**Next:** ${v.next}`,
   '',v.fix.reason,
   ...(pins.length?['',...pins.map(([name,value])=>`${name} SHA-256: \`${value}\``)]:[]),
   '',`[Execution and full evidence](${runUrl})`
 ].join('\n');
}
