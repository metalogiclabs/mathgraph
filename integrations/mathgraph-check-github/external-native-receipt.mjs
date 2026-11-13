// Exact-subject consumer for one external research receipt on an owned PR.
// The carrier is NOT the researched repository. No native tests are rerun
// in this webhook. Only strict GitHub source/blob/artifact readbacks qualify.
import { createHash } from "node:crypto";
import { Buffer } from "node:buffer";
export const EVIDENCE = Object.freeze({
  carrier:"metalogiclabs/go-ethereum",
  manifest:".mathgraph-check/external-native-evidence.v1.json",
  manifestBlob:"78d8374b3882fa29e84bfacc41e464caf2d444b1",
  carrierFiles:Object.freeze([
    ".mathgraph-check/external-native-evidence.v1.json",
    ".mathgraph-check/EXTERNAL-RECEIPT-ACCEPTANCE.md"
  ]),
  subjectRepo:"goccy/go-yaml",
  subjectPR:958,
  subjectBase:"edee2f91616c6d73112a13e7c0dbde72ce938877",
  subjectHead:"a34b94ecb553bb5a693296c30232a89026db79ca",
  subjectIssue:"https://github.com/goccy/go-yaml/issues/872",
  reporter:"heathsanchez/test",
  reportCommit:"20864090c084efc0511cffcf47aae556b4003fea",
  reportPath:"research/mathgraph_pr958_one_finding_20261015/ONE_FINDING_REPORT.json",
  reportBlob:"1aa1a916df72fbcf6a62abea5c4160c257e205f3",
  runs:Object.freeze([
    Object.freeze({id:38559572638,head:"0edf9eed9cdd9fd076e5f0e4395a97f04898580c",
      path:".github/workflows/mathgraph-one-consequential-pr958.yml",
      artifact:11891727361,name:"mathgraph-pr958-one-finding-native-v1",
      digest:"sha256:f36a2f6fb0027ead5885354f18cdf019c7bd9bf590ac4e26ce3d810e6dcbc35a"}),
    Object.freeze({id:38560167831,head:"332e3119498bd080b195ac33d200707569313b7d",
      path:".github/workflows/mathgraph-issue872-native-repair.yml",
      artifact:11891373353,name:"mathgraph-issue872-native-followup-repair",
      digest:"sha256:bc150693a314107764c59d7f395deb2c2ce4d4107f83324fdfe425d58b353d04"}),
    Object.freeze({id:38560825707,head:"20864090c084efc0511cffcf47aae556b4003fea",
      path:".github/workflows/mathgraph-issue872-apply-diff.yml"})
  ])
});
const PREFIX="/repos/"+EVIDENCE.reporter;
function requireFact(v,reason){if(!v)throw Error(reason);}
function gitBlob(raw) {
  const b=Buffer.from(raw,"utf8");
  return createHash("sha1").update("blob "+b.length+"\0").update(b).digest("hex");
}
export function pinnedJSON(file, expectedBlob){
  requireFact(file?.sha===expectedBlob && file?.encoding==="base64" &&
    typeof file?.content==="string" && file.content.length<40000,
    "SOURCE_BLOB_IDENTITY_UNKNOWN");
  const raw=Buffer.from(file.content.replace(/\s/g,""),"base64").toString("utf8");
  requireFact(Buffer.byteLength(raw,"utf8")<24000 && gitBlob(raw)===expectedBlob,
    "SOURCE_BYTES_NOT_PINNED");
  let parsed;
  try{parsed=JSON.parse(raw);}catch{throw Error("SOURCE_JSON_INVALID");}
  requireFact(parsed && typeof parsed==="object" && !Array.isArray(parsed),
    "SOURCE_JSON_INVALID");
  return parsed;
}
function validManifest(m){
  return m?.schema==="mathgraph.external-native-evidence.v1" &&
    m?.authority==="RESEARCH_EVIDENCE_CARRIER_ONLY" &&
    m?.carrier?.repository===EVIDENCE.carrier &&
    m?.carrier?.subject_matches_carrier_code===false &&
    m?.subject?.repository===EVIDENCE.subjectRepo &&
    m?.subject?.pr===EVIDENCE.subjectPR &&
    m?.subject?.base_sha===EVIDENCE.subjectBase &&
    m?.subject?.head_sha===EVIDENCE.subjectHead &&
    m?.subject?.inherited_issue===EVIDENCE.subjectIssue &&
    m?.one_finding?.code==="INHERITED_KEEP_CHOMPING_BEHAVIOR_WITH_SEPARATE_NATIVE_REPAIR" &&
    m?.one_finding?.priority==="SEPARATE_FOLLOWUP_NOT_PR_INTRODUCED" &&
    m?.one_finding?.introduced_pr_regressions===0 &&
    m?.one_finding?.author_pr_repairs===69 &&
    m?.one_finding?.inherited_failing_nested_cases===20 &&
    m?.one_finding?.independent_one_file_patch_repairs_nested_cases===20 &&
    m?.one_finding?.native_cases===130 &&
    m?.one_finding?.evidence_authority==="HUMAN_ORCHESTRATED_SOURCE_PINNED_GO_TESTS" &&
    m?.receipt?.repository===EVIDENCE.reporter &&
    m?.receipt?.commit===EVIDENCE.reportCommit &&
    m?.receipt?.report_path===EVIDENCE.reportPath &&
    m?.receipt?.report_blob===EVIDENCE.reportBlob &&
    m?.receipt?.native_pr_run?.id===EVIDENCE.runs[0].id &&
    m?.receipt?.native_pr_run?.head_sha===EVIDENCE.runs[0].head &&
    m?.receipt?.native_pr_run?.artifact_id===EVIDENCE.runs[0].artifact &&
    m?.receipt?.native_pr_run?.artifact_digest===EVIDENCE.runs[0].digest &&
    m?.receipt?.native_repair_run?.id===EVIDENCE.runs[1].id &&
    m?.receipt?.native_repair_run?.head_sha===EVIDENCE.runs[1].head &&
    m?.receipt?.native_repair_run?.artifact_id===EVIDENCE.runs[1].artifact &&
    m?.receipt?.native_repair_run?.artifact_digest===EVIDENCE.runs[1].digest &&
    m?.receipt?.independent_patch_run?.id===EVIDENCE.runs[2].id &&
    m?.receipt?.independent_patch_run?.head_sha===EVIDENCE.runs[2].head;
}
function validResearchReport(r){
  return r?.schema==="mathgraph.one-consequential-maintainer-decision.v1" &&
    r?.subject?.repo===EVIDENCE.subjectRepo &&
    r?.subject?.pr===EVIDENCE.subjectPR &&
    r?.subject?.base_sha===EVIDENCE.subjectBase &&
    r?.subject?.head_sha===EVIDENCE.subjectHead &&
    r?.decision?.introduced_case_count===0 &&
    r?.decision?.fixed_by_author_case_count===69 &&
    r?.decision?.unresolved_inherited_count===20 &&
    r?.decision?.passed_unchanged_native_original_suites===true &&
    r?.decision?.independent_preexisting_issue===EVIDENCE.subjectIssue &&
    r?.decision?.report_authority==="WARRANTED_BOUNDED_NATIVE_SEMANTICS_NOT_GLOBAL_MERGE_ASSURANCE" &&
    r?.repair?.source_file==="ast/ast.go" &&
    r?.repair?.original_nesting_failures===20 &&
    r?.repair?.patched_nesting_failures===0 &&
    r?.repair?.ablation_failures===20 &&
    r?.repair?.protected_original_suite==="PASS" &&
    r?.repair?.unchanged_inherited_nan_inf_negative_controls===5 &&
    r?.evidence?.pr_trial?.run===EVIDENCE.runs[0].id &&
    r?.evidence?.pr_trial?.artifact===EVIDENCE.runs[0].artifact &&
    r?.evidence?.repair_trial?.run===EVIDENCE.runs[1].id &&
    r?.evidence?.repair_trial?.artifact===EVIDENCE.runs[1].artifact;
}
const READ_PATHS=new Set(EVIDENCE.runs.flatMap(r=>
  [PREFIX+"/actions/runs/"+r.id,
    ...(r.artifact?[PREFIX+"/actions/runs/"+r.id+"/artifacts?per_page=100"]:[])]
).concat([PREFIX+"/contents/"+EVIDENCE.reportPath+"?ref="+EVIDENCE.reportCommit]));
async function publicRead(path,fetcher,readToken){
  requireFact(READ_PATHS.has(path),"EXTERNAL_API_PATH_NOT_ALLOWLISTED");
  requireFact(typeof readToken==="string" && readToken.length>=10,
    "NO_SCOPED_GITHUB_TOKEN_FOR_READONLY_PUBLIC_METADATA");
  const result=await fetcher("https://api.github.com"+path,{
    method:"GET",
    headers:{"Accept":"application/vnd.github+json",
      "X-GitHub-Api-Version":"2022-11-28",
      "User-Agent":"MathGraph-Check-External-Receipt-Reader",
      // Restricted *GitHub-only* static public metadata paths; the token's
      // installation scope is unchanged and cannot write this other repo.
      Authorization:"Bearer "+readToken},
    signal:AbortSignal.timeout(15000)
  });
  requireFact(result?.ok===true,"PUBLIC_GITHUB_RECEIPT_HTTP_"+String(result?.status||0));
  return result.json();
}
function validRun(r,p){
  return r?.id===p.id && r?.head_sha===p.head &&
    r?.status==="completed" && r?.conclusion==="success" &&
    r?.repository?.full_name===EVIDENCE.reporter &&
    r?.event==="push" && r?.run_attempt===1 && r?.path===p.path;
}
function validArchive(data,p){
  return Number.isSafeInteger(data?.total_count) &&
    Array.isArray(data.artifacts) && data.total_count<=data.artifacts.length &&
    data.artifacts.filter(a=>
      a.id===p.artifact && a.name===p.name && a.expired===false &&
      a.digest===p.digest && a.workflow_run?.id===p.id &&
      a.workflow_run?.head_sha===p.head
    ).length===1;
}
function safeCheck(c){
  return c?.name==="MathGraph Check / evidence scope" &&
    c?.status==="completed" && c?.conclusion==="neutral" &&
    typeof c?.output?.summary==="string";
}
function prepend(check,title,content){
  requireFact(safeCheck(check),"FORBIDDEN_CHECK_AUTHORITY");
  const update={...check,output:{...check.output,title,
    summary:(content+"\n\n---\n### Carrier PR's own evidence (separate source scope)\n"+
      check.output.summary).slice(0,60000)}};
  requireFact(safeCheck(update),"NATIVE_EVIDENCE_ESCALATED_CHECK");
  return update;
}
function unknown(check,code){
  return {state:code,check:prepend(check,"EXTERNAL_RECEIPT_UNKNOWN",[
    "### External evidence carrier — UNKNOWN",
    "**This is NOT an Ethereum software defect or merger decision.**",
    "The external native receipt could not be independently rechecked: "+code+".",
    "**Next action:** Revalidate pinned source report, native runs and archive digests.",
    "The original CI and PR findings remain separately visible below."
  ].join("\n"))};
}
export async function appendExternalNativeReceipt(report,check,githubRead,token,snapshot,{
  fetcher=fetch
}={}){
  if(report?.source?.repository!==EVIDENCE.carrier ||
      !Array.isArray(snapshot?.files) ||
      !snapshot.files.some(x=>x.filename===EVIDENCE.manifest))
    return {state:"NOT_APPLICABLE",check};
  if(!safeCheck(check) || snapshot.sha!==report.source.sha ||
      snapshot.number!==report.source.pr ||
      snapshot.files_visibility!=="COMPLETE" ||
      !snapshot.files.every(x=>EVIDENCE.carrierFiles.includes(x.filename)))
    return unknown(check,"CARRIER_SOURCE_SCOPE_INCOMPLETE");
  if(typeof githubRead!=="function" || !token)
    return unknown(check,"CARRIER_READ_ACCESS_MISSING");
  try{
    const file=await githubRead("/repos/"+EVIDENCE.carrier+
      "/contents/"+EVIDENCE.manifest+"?ref="+snapshot.sha,token);
    requireFact(validManifest(pinnedJSON(file,EVIDENCE.manifestBlob)),
      "MANIFEST_SUBJECT_MISMATCH");
    const reportFile=await publicRead(PREFIX+"/contents/"+EVIDENCE.reportPath+
      "?ref="+EVIDENCE.reportCommit,fetcher,token);
    requireFact(validResearchReport(pinnedJSON(reportFile,EVIDENCE.reportBlob)),
      "RESEARCH_REPORT_SUBJECT_MISMATCH");
    const checks=await Promise.all(EVIDENCE.runs.map(async pin=>{
      const run=await publicRead(PREFIX+"/actions/runs/"+pin.id,fetcher,token);
      requireFact(validRun(run,pin),"EXTERNAL_NATIVE_RUN_NOT_QUALIFIED");
      if(pin.artifact){
        const a=await publicRead(PREFIX+"/actions/runs/"+pin.id+
          "/artifacts?per_page=100",fetcher,token);
        requireFact(validArchive(a,pin),"EXTERNAL_ARCHIVE_DIGEST_MISMATCH");
      }
      return pin.id;
    }));
    requireFact(checks.length===3,"EXTERNAL_RUN_SET_INCOMPLETE");
    const summary=[
      "### One consequential finding — EXTERNAL source-native research",
      "**Subject: goccy/go-yaml PR #958, NOT this Ethereum evidence-carrier PR.**",
      "",
      "**Maintainer decision:** The author's PR repairs 69 of 130 frozen native cases, with 0 newly introduced regression cases in that matrix. The 20 remaining failures were inherited and are tracked in issue #872.",
      "",
      "**Smallest tested follow-up:** One-file keep-chomping repair closes the 20 inherited cases. Removing that patch reproduces all 20; original upstream Go suite passed.",
      "",
      "**Next action:** Do not block PR #958 solely for its out-of-scope inherited issue #872. Review the [separate fix](https://github.com/"+EVIDENCE.reporter+"/blob/"+EVIDENCE.reportCommit+"/research/mathgraph_pr958_one_finding_20261015/issue872_preserve_chomp.patch) and [machine-readable decision](https://github.com/"+EVIDENCE.reporter+"/blob/"+EVIDENCE.reportCommit+"/"+EVIDENCE.reportPath+").",
      "",
      "**Independently rechecked historical GitHub metadata:**",
      ...EVIDENCE.runs.map(p=>"- [Run "+p.id+"](https://github.com/"+EVIDENCE.reporter+"/actions/runs/"+p.id+") — success at exact SHA `"+p.head+"`"+(p.artifact?"; artifact "+p.artifact+" SHA-256 `"+p.digest.slice(7)+"`":"")),
      "",
      "**Authority boundary:** Prior Go tests and repairs were human-orchestrated. This App rechecked source report bytes, successful GitHub run identities and archive digests. The Cloudflare webhook did NOT rerun Go tests or independently prove software correctness. `ADVISORY_ONLY`. No Ethereum code defect is asserted, no autonomous method invention, and no merge authority."
    ].join("\n");
    return {state:"WARRANTED_BOUNDED_EXTERNAL_NATIVE_METADATA_RECHECKED",
      check:prepend(check,"EXTERNAL_NATIVE_ONE_FINDING_BOUNDED",summary),
      subject:EVIDENCE.subjectRepo,sourceSha:EVIDENCE.subjectHead,
      carrierSha:snapshot.sha};
  }catch(err){
    const msg=String(err?.message||"UNKNOWN");
    return unknown(check,/^[A-Z0-9_]+$/.test(msg)?
      msg:"EXTERNAL_RECEIPT_RECHECK_ERROR");
  }
}
