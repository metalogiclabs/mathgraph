// A deliberately narrow ORIGINAL native evidence consumer for a single owned PR.
// Does not run Go code, infer semantic correctness or create a new check.
// Original ZIP bytes and both SHA-256 member digests were inspected independently
// before these pins were admitted. At runtime, re-check GitHub run AND artifact
// identity; status is historical, not current future-action authorization.
export const V19 = Object.freeze({
  repository: "metalogiclabs/go-ethereum",
  pr: 19,
  sha: "a04aa77aaebd81d11274560e8d24d90c6f417589",
  run: 38202260024,
  workflow: ".github/workflows/bal-engine-crossfork-v19.yml",
  artifact: 11725753900,
  artifactName: "bal-v19-qualification-evidence",
  zipDigest: "sha256:2f141757925ec5d12932d7d60c8d1105be3dbcd932963470b64d9ff262fca943",
  logSha256: "badc1796a65f26b62d10fdd92bb2947ff6bef9cff9c339b3a829f8bb0d81d0e6",
  boundarySha256: "326f4be0cbf0137803a072686d5dccc73cc76610a1a91ae24c5c623612b35009",
  checkedTests: Object.freeze([
    "TestBALV19CrossForkAdmissionPredicate",
    "TestBALV18CompetingForkFinalityFailsClosed",
    "TestBALInvalidFCUV17MalformedAttributesCannotAdmitPendingAuthority",
    "TestBALEngineV13VolatilePendingWitness"
  ]),
  openResiduals: Object.freeze(["remote_conflicting_fcu", "concurrent_fcu"])
});
function target(s) {
  return s?.repository===V19.repository &&
    s?.pr===V19.pr && s?.sha===V19.sha;
}
function safeCheck(c) {
  return c?.name==="MathGraph Check / evidence scope" &&
    c?.status==="completed" && c?.conclusion==="neutral" &&
    typeof c?.output?.summary==="string";
}
function validRun(r) {
  return r?.id===V19.run && r?.status==="completed" &&
    r?.conclusion==="success" && r?.head_sha===V19.sha &&
    r?.repository?.full_name===V19.repository &&
    r?.path===V19.workflow && r?.event==="push" &&
    r?.run_attempt===1;
}
function validArtifacts(r) {
  return Number.isSafeInteger(r?.total_count) &&
    r.total_count<=r.artifacts?.length &&
    r.artifacts.filter(a=>a.id===V19.artifact &&
      a.name===V19.artifactName && a.expired===false &&
      a.digest===V19.zipDigest &&
      a.workflow_run?.id===V19.run &&
      a.workflow_run?.head_sha===V19.sha).length===1;
}
/**
 * This is an adapter between existing GitHub checks and already qualified
 * archive-level evidence. The original Go tests are NOT executed here.
 * Both GitHub REST readbacks and reviewed, immutable local digest pins are
 * required before adding any bounded historical observation.
 */
export async function appendGethV19NativeEvidence(report, check, githubRead, token) {
  if(!target(report?.source)) return {state:"NOT_APPLICABLE",check};
  if(report?.authority!=="ADVISORY_ONLY" || !safeCheck(check))
    throw Error("FORBIDDEN_NATIVE_CHECK_AUTHORITY");
  if(typeof githubRead!=="function" || typeof token!=="string" || !token)
    return {state:"UNKNOWN_NATIVE_RUN_READBACK_MISSING",check};
  let run, artifacts;
  try {
    run=await githubRead("/repos/"+V19.repository+"/actions/runs/"+V19.run,token);
    artifacts=await githubRead("/repos/"+V19.repository+"/actions/runs/"+
      V19.run+"/artifacts?per_page=100",token);
  }catch{
    return {state:"UNKNOWN_NATIVE_RUN_READBACK_UNAVAILABLE",check};
  }
  if(!validRun(run) || !validArtifacts(artifacts))
    return {state:"UNKNOWN_NATIVE_RUN_IDENTITY_MISMATCH",check};
  const content=[
    "### Independently source-pinned native Go evidence — historical scope only",
    "- **Exact original PR/source:** https://github.com/"+V19.repository+
      "/pull/"+V19.pr+" at "+V19.sha,
    "- **Native workflow:** https://github.com/"+V19.repository+
      "/actions/runs/"+V19.run+" — original GitHub run completed SUCCESS",
    "- **Original archived Go observations:** "+V19.checkedTests.join(", ")+" — PASS in the pinned log",
    "- **Archive identity:** artifact "+V19.artifact+
      ", SHA-256 "+V19.zipDigest.slice(7),
    "- **Native tests.log SHA-256:** "+V19.logSha256,
    "- **Native boundary.txt SHA-256:** "+V19.boundarySha256,
    "- **Original qualified scope:** predicate plus valid authenticated Engine controls.",
    "- **Still UNKNOWN:** "+V19.openResiduals.map(x=>x+"=UNKNOWN").join("; ")+
      ". These were not exercised by the original remote competing-fork/concurrency test.",
    "",
    "**Evidence boundary:** an original source-pinned GitHub run and its archive"+
      " identity were rechecked. The archived native test results were"+
      " independently inspected at their exact revisions, **not rerun in this"+
      " webhook**. This is not a general correctness proof, a new native test,"+
      " current production assurance or permission to merge. A CI status may"+
      " change at the same source SHA without refuting historical observations."
  ].join("\n");
  const updated={...check,output:{...check.output,
    summary:(content+"\n\n---\n### Generic current-head evidence and next action\n"+
      check.output.summary).slice(0,60000)}};
  if(!safeCheck(updated) || updated.output.title!==check.output.title)
    throw Error("NATIVE_RECEIPT_ESCALATED_CHECK");
  return {state:"WARRANTED_BOUNDED_HISTORICAL_NATIVE_ARTIFACT",
    check:updated,source:V19.sha,appAuthority:"ADVISORY_ONLY"};
}
