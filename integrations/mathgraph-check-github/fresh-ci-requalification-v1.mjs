// A fresh GitHub check-run readback is separate from the raw, fail-closed
// MONITOR transition. No caller-supplied report/boolean is a trust anchor.
// This result establishes CI observations only, never semantic truth or effects.
import {githubSnapshot} from "./authenticated-cycle-v1.mjs";
// GitHub matrix check names can contain commas, e.g. "(ubuntu-latest, stable)".
const CLAIM=/^[A-Za-z0-9][A-Za-z0-9 ._:/(),-]{0,127}$/;
const OWNER=/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
const SHA=/^[a-f0-9]{40}$/;
const reply=(reason,subject=null,checks=[])=>({
 schema:"mathgraph.check.fresh-github-ci-readback.v1",status:"UNKNOWN",
 permission:"ADVISORY_ONLY",semantic_verification:"NOT_ESTABLISHED",
 source:"GITHUB_API_INDEPENDENT_CHECK_RUNS",reason,subject,checks,
});
export async function requalifyFreshGitHubCI({repository,pr,token,requiredChecks,previous}={}){
 if(typeof repository!=="string"||!OWNER.test(repository)||
    !Number.isSafeInteger(pr)||pr<1||
    typeof token!=="string"||token.length<8||
    !Array.isArray(requiredChecks)||requiredChecks.length===0||
    requiredChecks.length>20||new Set(requiredChecks).size!==requiredChecks.length||
    !requiredChecks.every(n=>typeof n==="string"&&CLAIM.test(n)))
    return reply("INVALID_FRESH_READBACK_REQUEST");
 // Previous status is advisory context, not verification authority.
 const prior=previous?.result?.subject??previous?.subject;
 if(prior && (prior.repository!==repository||prior.pr!==pr))
    return reply("PREVIOUS_SUBJECT_MISMATCH");
 const fresh=await githubSnapshot({repository,pr,token});
 const subject=fresh.result?.subject;
 if(subject?.repository!==repository||subject?.pr!==pr||!SHA.test(subject.head_sha??""))
    return reply("FRESH_SUBJECT_MISMATCH",subject);
 const checks=requiredChecks.map(name=>{
   const result=fresh.result.results?.find(r=>r.id===name);
   const claim=fresh.input.claims?.find(c=>c.id===name);
   const evid=fresh.input.evidence?.find(e=>e.name===name);
   if(!result||!claim||!evid||
      claim.requires?.length!==1||claim.requires[0]!==evid.id||
      evid.subject_sha!==subject.head_sha||!Number.isSafeInteger(evid.check_run_id))
     return {name,status:"UNKNOWN",reason:"NO_EXACT_HEAD_INDEPENDENT_CHECK"};
   if(result.status==="BLOCKED"&&evid.conclusion==="failure")
     return {name,status:"BLOCKED",reason:"FRESH_GITHUB_CHECK_FAILURE",check_run_id:evid.check_run_id};
   if(result.status==="OBSERVED"&&result.reason==="CI_SUCCESS_NOT_SEMANTIC_WARRANT"&&
      evid.conclusion==="success")
     return {name,status:"OBSERVED",reason:"FRESH_GITHUB_CI_SUCCESS_ONLY",check_run_id:evid.check_run_id};
   return {name,status:"UNKNOWN",reason:"CHECK_NOT_SUCCESSFUL_AND_COMPLETED",check_run_id:evid.check_run_id};
 });
 const status=checks.some(c=>c.status==="BLOCKED")?"BLOCKED":
   checks.some(c=>c.status==="UNKNOWN")?"UNKNOWN":"OBSERVED";
 return {schema:"mathgraph.check.fresh-github-ci-readback.v1",status,
   permission:"ADVISORY_ONLY",semantic_verification:"NOT_ESTABLISHED",
   source:"GITHUB_API_INDEPENDENT_CHECK_RUNS",subject,checks,
   previous_head_sha:prior?.head_sha??null,
   changed_head:!!prior&&prior.head_sha!==subject.head_sha,
   // In-band claims and flags from a prior report are never trusted.
   reason:status==="OBSERVED"?"FRESH_CI_READBACK_NOT_A_WARRANT":
     "FRESH_RECHECK_NOT_QUALIFIED"};
}
