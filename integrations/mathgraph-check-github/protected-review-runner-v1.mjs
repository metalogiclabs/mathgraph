/**
 * A read-only admission consumer for execution by an independently controlled
 * host. In-band context labels, reviewer keys and receipt policies do NOT
 * establish trust if the caller obtained them from the audited PR.
 * This module cannot attest its own deployment or replace Lean proof replay.
 */
import {githubSnapshot} from './authenticated-cycle-v1.mjs';

export const PROTECTED_REVIEW_SCHEMA='mathgraph.protected-review-admission.v1';
const SHA40=/^[0-9a-f]{40}$/;
const SHA64=/^[0-9a-f]{64}$/;
const REPO=/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
const BRANCH=/^[A-Za-z0-9_.\/-]+$/;
const unknown=reason=>({schema:PROTECTED_REVIEW_SCHEMA,status:'UNKNOWN',reason,
 terminal_form:null,artifact_corroboration:'UNKNOWN',proof_replay:'NOT_PERFORMED',
 universal_sufficiency:'NOT_ESTABLISHED',permission:'ADVISORY_ONLY'});

export function eligibleProtectedContext(c){
 return c&&c.event_name==='workflow_dispatch'&&typeof c.default_branch==='string'&&
  BRANCH.test(c.default_branch)&&!c.default_branch.includes('..')&&
  c.ref==='refs/heads/'+c.default_branch&&REPO.test(c.repository??'')&&
  Number.isSafeInteger(c.pr)&&c.pr>0&&
  typeof c.token==='string'&&c.token.length>=8&&
  typeof c.evidence_token==='string'&&c.evidence_token.length>=8;
}

/**
 * Verify the identity of the independently pinned original GitHub artifact
 * and the exact successful Lean proof job. ZIP bytes are a *separate* check.
 */
async function authenticatedHistoricalEvidence(context,policy,artifactId,fetcher){
 if(!policy||!REPO.test(policy.repository??'')||
  !Number.isSafeInteger(policy.run)||policy.run<1||
  !Number.isSafeInteger(policy.job)||policy.job<1||
  !Number.isSafeInteger(artifactId)||artifactId<1||
  !SHA40.test(policy.commit??'')||!SHA64.test(policy.artifact_sha256??''))
  return false;
 const api=async route=>{
  const response=await fetcher('https://api.github.com/repos/'+policy.repository+route,{
   method:'GET',redirect:'error',signal:AbortSignal.timeout(15000),
   headers:{Accept:'application/vnd.github+json',
    Authorization:'Bearer '+context.evidence_token,
    'X-GitHub-Api-Version':'2022-11-28'}});
  if(!response?.ok)throw Error('EVIDENCE_API_UNAVAILABLE');
  return response.json();
 };
 try{
  const [artifact,jobs]=await Promise.all([
   api('/actions/artifacts/'+artifactId),
   api('/actions/runs/'+policy.run+'/jobs?per_page=100'),
  ]);
  if(artifact?.id!==artifactId||artifact.expired!==false||
    artifact.digest!=='sha256:'+policy.artifact_sha256||
    artifact.workflow_run?.id!==policy.run||
    artifact.workflow_run?.head_sha!==policy.commit||
    !Number.isSafeInteger(artifact.workflow_run.repository_id)||
    artifact.workflow_run.repository_id!==artifact.workflow_run.head_repository_id||
    !Number.isSafeInteger(jobs?.total_count)||
    jobs.total_count!==jobs.jobs?.length||jobs.total_count>100)
   return false;
  const matching=jobs.jobs.filter(j=>j?.id===policy.job);
  if(matching.length!==1)return false;
  const job=matching[0];
  return job.run_id===policy.run&&job.name==='directive-proofs'&&
    job.status==='completed'&&job.conclusion==='success'&&
    Array.isArray(job.steps)&&job.steps.filter(s=>
      s.name==='Qualify persistent capstone boundary and retained positive repair'&&
      s.conclusion==='success').length===1;
 }catch{return false;}
}

/**
 * Host-supplied trust roots remain necessary. No network writes, no Check Run
 * publication and no reuse on a changed PR head.
 */
export async function qualifyProtectedReview({context,signedProjectionReview,
 trustedReviewerKeys,trustedProofReceipt,artifactPath,artifactId,
 fetcher=fetch}={}){
 if(!eligibleProtectedContext(context))return unknown('PROTECTED_DEFAULT_BRANCH_DISPATCH_REQUIRED');
 if(typeof fetcher!=='function')return unknown('AUTHENTICATED_GITHUB_READER_REQUIRED');
 const opts={repository:context.repository,pr:context.pr,token:context.token,
  signedProjectionReview,trustedReviewerKeys,proofArtifactPath:artifactPath,
  trustedProofReceipt,fetcher};
 try{
  const first=await githubSnapshot(opts);
  if(first.projection?.status!=='BLOCKED'||
    first.projection.review?.artifact_corroboration!=='CORROBORATED')
   return unknown('INDEPENDENTLY_ADMITTED_SIGNED_PROOF_REQUIRED');
  if(!(await authenticatedHistoricalEvidence(context,trustedProofReceipt,
    artifactId,fetcher)))return unknown('HISTORICAL_GITHUB_ARTIFACT_OR_JOB_UNQUALIFIED');
  const second=await githubSnapshot(opts);
  if(first.result.subject?.head_sha!==second.result.subject?.head_sha||
    second.projection?.status!=='BLOCKED'||
    second.projection.review?.artifact_corroboration!=='CORROBORATED')
   return unknown('CURRENT_PR_SOURCE_CHANGED_OR_REVIEW_WITHDRAWN');
  return {schema:PROTECTED_REVIEW_SCHEMA,status:'BLOCKED',
   terminal_form:'NAMED_OBSTRUCTION',permission:'ADVISORY_ONLY',
   subject:second.result.subject,artifact_corroboration:'CORROBORATED',
   proof_replay:'NOT_PERFORMED',universal_sufficiency:'NOT_ESTABLISHED',
   reviewed_claim_id:second.projection.results[0]?.id??null,
   evidence_kind:'HISTORICAL_GITHUB_JOB_METADATA_AND_PINNED_ARTIFACT_BYTES',
   reviewer_key_id:second.projection.review.key_id,
   receipt_ref:second.projection.review.receipt_ref};
 }catch{return unknown('PROTECTED_REVIEW_EXECUTION_INCOMPLETE');}
}
