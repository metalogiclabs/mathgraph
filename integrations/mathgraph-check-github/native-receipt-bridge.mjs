// MathGraph Check: source-bound native evidence adaptor, NOT a verifier by itself.
// Caller must obtain the pinned policy from reviewed source, verify both GitHub
// workflow readbacks independently, and supply original receipt bytes.
// Does not read credentials, execute source or POST a Check.
import {createHash} from "node:crypto";
const SHA=/^[a-f0-9]{40}$/i, HASH=/^[a-f0-9]{64}$/i;
const sha256=b=>createHash("sha256").update(b).digest("hex");
function need(x,code){if(!x)throw Error(code);}
function validRun(run,p){
  return run?.id===p.id && run?.status==="completed" &&
    run?.conclusion==="success" && run?.head_sha===p.commit &&
    run?.path===p.workflow && run?.repository?.full_name===p.repository;
}
function same(a,b){return a?.repository===b?.repository &&
  a?.pr===b?.pr && a?.sha===b?.sha;}
// Policy and GitHub API readbacks are trust inputs, NEVER receipt-supplied claims.
export function bindQualifiedNativeReceipt({
  assessment, check, receiptBytes, reviewedPolicy, originalRun,
  independentReplayRun, currentPRHead
}={}){
  need(assessment?.authority==="ADVISORY_ONLY" &&
    SHA.test(assessment.source?.sha||""),"APP_ASSESSMENT_NOT_ADVISORY");
  need(check?.name==="MathGraph Check / evidence scope" &&
    check.status==="completed" && check.conclusion==="neutral" &&
    typeof check.output?.summary==="string","CHECK_AUTHORITY_ESCALATION");
  const p=reviewedPolicy;
  need(p?.schema==="metalogic.mathgraph-check.native-bridge-policy.v1" &&
    HASH.test(p.receiptSha256||"") && HASH.test(p.protocolSha256||"") &&
    SHA.test(p.baseSha||"") && SHA.test(p.subject?.sha||"") &&
    p.subject?.pr>0 && p.actionAuthorization==="NONE" &&
    Number.isSafeInteger(p.selectedTests) && p.selectedTests>0 &&
    Number.isSafeInteger(p.baseSuite) && Number.isSafeInteger(p.headSuite),
    "REVIEWED_POLICY_REQUIRED");
  if(!same(assessment.source,p.subject))
    return {state:"UNKNOWN_SOURCE_SCOPE_MISMATCH",check,actionAuthorization:"NONE"};
  if(p.withdrawn===true)
    return {state:"STALE_WITHDRAWN_EVIDENCE",check,actionAuthorization:"NONE"};
  if(currentPRHead!==p.subject.sha)
    return {state:"STALE_OR_UNOBSERVED_SOURCE_HEAD",check,actionAuthorization:"NONE"};
  need(receiptBytes instanceof Uint8Array,"ORIGINAL_RECEIPT_BYTES_REQUIRED");
  need(sha256(receiptBytes)===p.receiptSha256,"RECEIPT_DIGEST_CHANGED");
  need(validRun(originalRun,p.producer),"PRODUCER_RUN_NOT_QUALIFIED");
  need(validRun(independentReplayRun,p.replay),"REPLAY_RUN_NOT_QUALIFIED");
  let r;
  try{r=JSON.parse(Buffer.from(receiptBytes).toString("utf8"))}
  catch{throw Error("RECEIPT_PARSE_FAILED")}
  need(r.schema==="metalogic.real-external-pr-native-evidence.v1" &&
    r.original_external_repo===p.subject.repository &&
    r.protocol_sha256===p.protocolSha256 &&
    r.qualified_count===r.cases?.length &&
    r.advisory_conclusion==="NEUTRAL_REVIEW_EVIDENCE_ONLY" &&
    r.code_repair_generated==="NO" &&
    r.method_generator_software_authorship==="HUMAN_WRITTEN" &&
    r.scientific_L7==="UNKNOWN" && r.action_authorization==="NONE",
    "RECEIPT_AUTHORITY_INVALID");
  const matches=r.cases.filter(c=>c.pr===p.subject.pr);
  need(matches.length===1,"CASE_IDENTITY_NOT_UNIQUE");
  const c=matches[0], n=p.selectedTests;
  need(c.head_sha===p.subject.sha && c.base_sha===p.baseSha &&
    c.result==="WARRANTED_BOUNDED_REAL_PR_NATIVE_REGRESSION" &&
    c.source_behavioral_proof==="RED_BASE_GREEN_HEAD_NATIVE_TESTS" &&
    c.application_to_external_owner==="READ_ONLY_NOT_INSTALLED" &&
    c.AST_derived_new_test_methods?.length===n &&
    c.before_source_with_head_tests?.test_count===n &&
    c.before_source_with_head_tests.exit_code!==0 &&
    c.after_source_with_head_tests?.test_count===n &&
    c.after_source_with_head_tests.exit_code===0 &&
    c.old_full_suite_on_base?.exit_code===0 &&
    c.old_full_suite_on_base.test_count===p.baseSuite &&
    c.full_suite_on_head?.exit_code===0 &&
    c.full_suite_on_head.test_count===p.headSuite,
    "NATIVE_BEHAVIOR_NOT_QUALIFIED");
  const notes=[
    "### Bounded, independently replayed ORIGINAL native regression",
    "- Original PR: https://github.com/"+p.subject.repository+"/pull/"+p.subject.pr,
    "- Source: "+p.subject.sha+" (current head matched at readback; future freshness UNKNOWN)",
    "- Same "+n+" contributor-authored tests: baseline RED / contributor head GREEN",
    "- Complete suites: "+p.baseSuite+" old; "+p.headSuite+" revised (at pinned revisions)",
    "- Original verifier: https://github.com/"+p.producer.repository+"/actions/runs/"+p.producer.id,
    "- Independent replay: https://github.com/"+p.replay.repository+"/actions/runs/"+p.replay.id,
    "- Pinned receipt SHA-256: "+p.receiptSha256,
    "",
    "**Boundary:** scoped historic observation, NOT a general source-correctness "+
    "theorem, generated fix, production approval or merge authority. "+
    "CI/freshness can change without refuting the original checked observation."
  ].join("\n");
  const result={...check,output:{...check.output,
    summary:(notes+"\n\n---\n### Original generic App report\n"+
      check.output.summary).slice(0,60000)}};
  need(result.conclusion==="neutral","FORBIDDEN_CHECK_PROMOTION");
  return {state:"WARRANTED_BOUNDED_HISTORICAL_NATIVE_RECEIPT",check:result,
    actionAuthorization:"NONE",currentApplicability:"OBSERVED_HEAD_ONLY"};
}
