import {createHash} from "node:crypto";

const h=(algo,b)=>createHash(algo).update(b).digest("hex");
const raw=b=>{if(!(b instanceof Uint8Array))throw Error("MISSING_ORIGINAL_BYTES");return Buffer.from(b)};
const parse=b=>JSON.parse(raw(b).toString("utf8"));
const goBlob=b=>h("sha1",Buffer.concat([Buffer.from("blob "+b.length+"\0"),b]));
const required=(ok,why)=>{if(!ok)throw Error(why)};
export const VERSION="mathgraph.check.decision-closure.v1";
export const ROOTS=Object.freeze({
 yaml:{
  subject:{repository:"goccy/go-yaml",pr:958,base:"edee2f91616c6d73112a13e7c0dbde72ce938877",head:"a34b94ecb553bb5a693296c30232a89026db79ca"},
  rawGitBlob:"1aa1a916df72fbcf6a62abea5c4160c257e205f3",
  runs:[
   [38559572638,"0edf9eed9cdd9fd076e5f0e4395a97f04898580c",".github/workflows/mathgraph-one-consequential-pr958.yml"],
   [38560167831,"332e3119498bd080b195ac33d200707569313b7d",".github/workflows/mathgraph-issue872-native-repair.yml"],
   [38560825707,"20864090c084efc0511cffcf47aae556b4003fea",".github/workflows/mathgraph-issue872-apply-diff.yml"]]
 },
 gimmes:{
  subject:{repository:"allan-mobley-jr/gimmes",pr:468,base:"08efd0bbc34fd29de2a4077f07d24f3dc02a63b6",head:"e1477f8b3f18c1de6ff87dbca9465a7b106dc193"},
  reviewZip:"590e19d88f3203b7915084eab71615d27bf8aca373d254cf666abdc5a28e7df4",
  nativeZip:"0e567242796ff0a68fadb4ded8fe754b0721c450b221d5733b9edad1be793fbe",
  reviewRaw:"3f6f0a2c221753046ae7a5680caac406f5ca5b942cfe21696331e42c31865d44",
  nativeRaw:"e3507d4e0e7bc402ffe1cc0646b2315361d677cc456e9d83eba9da5f6a577997",
  runs:[
   [38638946524,"a9dbef7b0293237420e9c6071180df22cab82755",".github/workflows/mgcheck-reviewer-uplift-20261015.yml"],
   [38639617928,"6e9853341a81b1933e9cefd14a10cd7e09d9ad77",".github/workflows/mgcheck-reviewer-projection-20261015.yml"]]
 }});
function no(p,status,reason){return {schema:VERSION,subject:p?.subject||null,status,reason,claims:[],action:"INDEPENDENTLY_RECHECK_EVIDENCE",merge:"UNKNOWN",authorization:"NONE"}}
function checkRuns(p,v){
 required(Array.isArray(v)&&v.length===p.runs.length,"RUN_SET_INCOMPLETE");
 for(const [id,sha,path] of p.runs){
  const matches=v.filter(r=>r.id===id);
  required(matches.length===1,"RUN_IDENTITY_NOT_UNIQUE");
  const r=matches[0];
  required(r.status==="completed"&&r.conclusion==="success"&&r.head_sha===sha&&
   r.path===path&&r.repository?.full_name==="heathsanchez/test"&&
   r.run_attempt===1&&r.event==="push","RUN_NOT_QUALIFIED");
 }}
function fromYaml(p,b){
 required(goBlob(b)===p.rawGitBlob,"REPORT_SOURCE_BLOB_MISMATCH");
 const r=parse(b),d=r.decision,patch=r.repair;
 required(r.schema==="mathgraph.one-consequential-maintainer-decision.v1"&&
  r.subject?.repo===p.subject.repository&&r.subject?.pr===p.subject.pr&&
  r.subject?.head_sha===p.subject.head&&r.subject?.base_sha===p.subject.base,
  "REPORT_SUBJECT_MISMATCH");
 required(d?.introduced_case_count===0&&d?.fixed_by_author_case_count===69&&
  d?.unresolved_inherited_count===20&&d?.passed_unchanged_native_original_suites===true&&
  d?.report_authority==="WARRANTED_BOUNDED_NATIVE_SEMANTICS_NOT_GLOBAL_MERGE_ASSURANCE"&&
  d?.independent_preexisting_issue==="https://github.com/goccy/go-yaml/issues/872"&&
  patch?.original_nesting_failures===20&&patch?.patched_nesting_failures===0&&
  patch?.ablation_failures===20&&patch?.protected_original_suite==="PASS"&&
  r.evidence?.pr_trial?.run===p.runs[0][0]&&r.evidence?.repair_trial?.run===p.runs[1][0],
  "NATIVE_SEMANTICS_NOT_QUALIFIED");
 return {claims:[
  {key:"PR_AUTHOR_REPAIRS",state:"WARRANTED_BOUNDED",cases:69},
  {key:"PR_INTRODUCED_REGRESSIONS",state:"ZERO_IN_DECLARED_130_CASE_MATRIX",cases:0},
  {key:"INHERITED_KEEP_CHOMPING",state:"WARRANTED_BOUNDED_INHERITED",cases:20,
   causal_repair:{original:20,patched:0,ablation:20}}],
   action:"REVIEW_SEPARATE_INHERITED_FIX_NOT_BLOCK_PR_SOLELY_FOR_ISSUE_872",
   unresolved:["GLOBAL_MERGE_SAFETY_UNKNOWN"]};
}
function fromGimmes(p,input){
 const z=raw(input.reviewZip),n=raw(input.nativeZip),b=raw(input.reportBytes),c=raw(input.nativeBytes);
 required(h("sha256",z)===p.reviewZip&&h("sha256",n)===p.nativeZip,
  "ORIGINAL_NATIVE_ARCHIVE_CHANGED");
 required(h("sha256",b)===p.reviewRaw&&h("sha256",c)===p.nativeRaw,
  "ORIGINAL_RECEIPT_BYTES_CHANGED");
 const report=parse(b),native=parse(c);
 required(report.schema==="mathgraph-check.review-resolution-receipt.v1"&&
  report.subject?.repo===p.subject.repository&&report.subject?.pr===p.subject.pr&&
  report.subject?.base===p.subject.base&&report.subject?.head===p.subject.head&&
  report.native_findings_promoted===1&&report.unknown_or_withheld===2&&
  report.records?.length===3&&report.merger_authority==="UNKNOWN",
  "REVIEW_DISPOSITION_SUBJECT_INVALID");
 required(native.subject_head===p.subject.head&&
  native.native_execution_completed===true&&native.original_native_observer?.exit!==0&&
  native.candidate_native_observer_and_old_suite?.exit===0&&
  native.physical_patch_removal?.exit!==0&&
  native.deliberately_wrong_candidate?.exit!==0&&
  native.final_exact_original_source_restored===true,
  "CAUSAL_REPAIR_NOT_QUALIFIED");
 const logs=[["original_review_witness.log","original_native_observer"],
  ["candidate_review_and_suite.log","candidate_native_observer_and_old_suite"],
  ["physically_restored_observer.log","physical_patch_removal"],
  ["wrong_candidate_negative.log","deliberately_wrong_candidate"]];
 for(const [file,phase] of logs)
  required(h("sha256",raw(input.logs?.[file]))===native[phase].log_sha256,
   "ORIGINAL_NATIVE_LOG_TAMPER");
 required(report.records.filter(x=>x.status==="WARRANTED_BOUNDED_NATIVE_WITNESS_AND_CANDIDATE_REPAIR").length===1&&
  report.records.filter(x=>x.status==="UNKNOWN_NORMATIVE_CONTRACT").length===2,
  "UNWARRANTED_REVIEW_PROMOTION");
 return {claims:report.records.map(x=>({key:x.key,state:x.status,location:x.location})),
  action:"REVIEW_VERIFIED_PATCH_AND_RESOLVE_TWO_POLICY_QUESTIONS",
  unresolved:["TWO_POLICY_QUESTIONS_UNKNOWN","GLOBAL_MERGE_SAFETY_UNKNOWN"]};
}
export function decide(root,input={}){
 const p=ROOTS[root];
 if(!p)return no(null,"UNKNOWN_UNRECOGNIZED_CAPABILITY","UNREGISTERED_POLICY");
 if(input.withdrawn)return no(p,"STALE_SUPPORT_WITHDRAWN","EXACT_ANCESTOR_WITHDRAWN");
 if(input.subject?.repository!==p.subject.repository||input.subject?.pr!==p.subject.pr)
  return no(p,"UNKNOWN_WRONG_SUBJECT","WRONG_RESEARCH_SUBJECT");
 if(input.subject?.head!==p.subject.head)
  return no(p,"STALE_SOURCE_HEAD","CURRENT_HEAD_NO_LONGER_PINNED");
 try{
  checkRuns(p,input.runReadbacks);
  const result=root==="yaml"?fromYaml(p,raw(input.reportBytes)):fromGimmes(p,input);
  return {schema:VERSION,subject:p.subject,status:"WARRANTED_BOUNDED_SOURCE_SPECIFIC",
   ...result,merge:"UNKNOWN",authorization:"NONE",historical:true,
   native_executed_in_this_consumer:false};
 }catch(e){return no(p,"UNKNOWN_EVIDENCE_NOT_QUALIFIED",String(e.message||e))}
}
export function reclose(frontiers){
 required(Array.isArray(frontiers)&&frontiers.length<=32,"INVALID_FRONTIERS");
 const states=frontiers.map(x=>({id:x.id,...decide(x.root,x.input)}));
 return {schema:VERSION,states,
   warranted:states.filter(x=>x.status==="WARRANTED_BOUNDED_SOURCE_SPECIFIC").length,
   unknown:states.filter(x=>x.status!=="WARRANTED_BOUNDED_SOURCE_SPECIFIC").length,
   merge_authority:"UNKNOWN",autonomous_action:"NONE"};
}
