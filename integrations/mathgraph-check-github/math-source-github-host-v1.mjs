/**
 * Read-only GitHub App host for mathematical provenance and human review.
 *
 * Only the installation holder supplies `trusted`. GitHub REST, not a PR JSON
 * boolean or check-name match, authenticates the identities and their scope.
 * This is a bounded observation layer, NOT a signed intent-probe receipt:
 * do not feed its output into auditMathSource as independent authority.
 */
import {createHash} from 'node:crypto';

export const GITHUB_MATH_OBSERVATION_SCHEMA='mathgraph.github-math-observations.v1';
const SHA40=/^[a-f0-9]{40}$/;
const SHA256=/^[a-f0-9]{64}$/;
const REPO=/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
const WORKFLOW=/^\.github\/workflows\/[A-Za-z0-9_.-]+\.yml$/;
const DATES=s=>typeof s==='string'&&Number.isFinite(Date.parse(s));
const sha=x=>createHash('sha256').update(x).digest('hex');
const plain=x=>x!==null&&typeof x==='object'&&!Array.isArray(x)&&
  (Object.getPrototypeOf(x)===Object.prototype||Object.getPrototypeOf(x)===null);
const requireFact=(v,reason)=>{if(!v)throw Error(reason);};

const unknown=(reason,subject=null)=>({
  schema:GITHUB_MATH_OBSERVATION_SCHEMA,status:'UNKNOWN',reason,
  subject,replay:{status:'UNKNOWN'},review:{status:'UNKNOWN'},
  receipt_qualification:'NOT_YET_CONTRACT_BOUND',conclusion:'neutral',
  permission:'ADVISORY_ONLY',intent_verification:'NOT_ESTABLISHED',
});

function validOptions(o){
  if(!plain(o)||!REPO.test(o.repository??'')||!Number.isSafeInteger(o.pr)||o.pr<1||
    !Number.isSafeInteger(o.runId)||o.runId<1||typeof o.token!=='string'||o.token.length<8||
    typeof o.fetcher!=='function'||!plain(o.trusted))return false;
  const t=o.trusted;
  return t.repository===o.repository&&t.pr===o.pr&&SHA40.test(t.headSha??'')&&
    WORKFLOW.test(t.workflowPath??'')&&SHA256.test(t.workflowSha256??'')&&
    Number.isSafeInteger(t.workflowId)&&t.workflowId>0&&
    typeof t.jobName==='string'&&t.jobName.length>0&&t.jobName.length<=80&&
    typeof t.artifactName==='string'&&t.artifactName.length>0&&t.artifactName.length<=80&&
    ['sourceSha256','claimSha256','formalSha256','environmentSha256']
      .every(k=>SHA256.test(t[k]??''))&&
    Array.isArray(t.approvedReviewerIds)&&t.approvedReviewerIds.length<=32&&
    t.approvedReviewerIds.every(n=>Number.isSafeInteger(n)&&n>0)&&
    new Set(t.approvedReviewerIds).size===t.approvedReviewerIds.length;
}

function workflowContent(record){
  requireFact(record?.encoding==='base64'&&typeof record.content==='string',
    'WORKFLOW_CONTENT_UNREADABLE');
  const value=record.content.replace(/\s+/g,'');
  requireFact(value.length>0&&value.length<128*1024&&
    /^[A-Za-z0-9+/]*={0,2}$/.test(value),'WORKFLOW_CONTENT_INVALID');
  return Buffer.from(value,'base64');
}

function validateRun(pr,run,trust,runId){
  requireFact(pr?.number===trust.pr&&pr?.base?.repo?.full_name===trust.repository&&
    pr?.head?.repo?.full_name===trust.repository&&
    SHA40.test(pr.base.sha)&&pr.head.sha===trust.headSha&&
    Number.isSafeInteger(pr.user?.id),'PR_HEAD_OR_REPOSITORY_CHANGED');
  requireFact(run?.id===runId&&run.workflow_id===trust.workflowId&&
    run.head_sha===trust.headSha&&run.repository?.full_name===trust.repository&&
    Number.isSafeInteger(run.repository?.id)&&
    run.head_repository?.id===run.repository.id&&
    typeof run.path==='string'&&run.path.startsWith(trust.workflowPath+'@')&&
    ['push','pull_request','workflow_dispatch'].includes(run.event)&&
    // GitHub's artifact list does not carry a trustworthy per-attempt ID.
    // Until the artifact is attempt-bound, never reuse a run that was rerun.
    Number.isSafeInteger(run.run_attempt)&&run.run_attempt===1&&
    DATES(run.run_started_at)&&run.status==='completed'&&run.conclusion==='success',
  'GITHUB_REPLAY_RUN_UNQUALIFIED');
}

function validJobAndArtifact(jobsResponse,artifactsResponse,run,trust){
  requireFact(Array.isArray(jobsResponse?.jobs)&&jobsResponse.total_count===jobsResponse.jobs.length&&
    jobsResponse.jobs.length<=100,'JOBS_INCOMPLETE');
  const matches=jobsResponse.jobs.filter(j=>j.name===trust.jobName);
  requireFact(matches.length===1,'REPLAY_JOB_MISSING_OR_DUPLICATE');
  const j=matches[0];
  const expectedSteps=[
    'Fetch exactly pinned third-party audited benchmark',
    'Bind exact source, theorem statement and archived proof hashes',
    'Native Lean replay and scoped theorem axiom audit',
    'Save bounded machine evidence (never the gold proof)',
  ];
  requireFact(j.run_id===run.id&&Number.isSafeInteger(j.id)&&
    j.status==='completed'&&j.conclusion==='success'&&Array.isArray(j.steps)&&
    expectedSteps.every(n=>j.steps.filter(s=>s.name===n&&s.conclusion==='success').length===1),
  'REPLAY_JOB_OR_OBLIGATION_INCOMPLETE');

  requireFact(Array.isArray(artifactsResponse?.artifacts)&&
    artifactsResponse.total_count===artifactsResponse.artifacts.length&&
    artifactsResponse.artifacts.length<=100,'ARTIFACTS_INCOMPLETE');
  const artifacts=artifactsResponse.artifacts.filter(a=>a.name===trust.artifactName);
  requireFact(artifacts.length===1,'REPLAY_ARTIFACT_MISSING_OR_DUPLICATE');
  const a=artifacts[0];
  requireFact(Number.isSafeInteger(a.id)&&a.id>0&&a.expired===false&&
    Number.isSafeInteger(a.size_in_bytes)&&a.size_in_bytes>0&&
    typeof a.digest==='string'&&/^sha256:[a-f0-9]{64}$/.test(a.digest)&&
    a.workflow_run?.id===run.id&&a.workflow_run?.head_sha===trust.headSha&&
    a.workflow_run?.repository_id===run.repository.id&&
    DATES(a.created_at)&&Date.parse(a.created_at)>=Date.parse(run.run_started_at),
  'REPLAY_ARTIFACT_OUT_OF_SCOPE');
  return {job:j,artifact:a};
}

function explicitReview(review,trust,pr,run){
  if(review?.state!=='APPROVED'||review.commit_id!==trust.headSha||
    review.user?.type!=='User'||review.user.id===pr.user.id||
    review.user.id===run.actor?.id||
    typeof review.body!=='string'||review.body.length>4096)return false;
  let d;
  try{d=JSON.parse(review.body);}catch{return false;}
  return plain(d)&&Object.keys(d).length===6&&
    d.schema==='mathgraph.source-to-formal-review.v1'&&
    d.source_sha256===trust.sourceSha256&&
    d.claim_sha256===trust.claimSha256&&
    d.statement_sha256===trust.formalSha256&&
    d.environment_sha256===trust.environmentSha256&&
    d.verdict==='SOURCE_TO_FORMAL_REVIEWED';
}

function latestReviewer(reviews,trust,pr,run){
  requireFact(Array.isArray(reviews)&&reviews.length<100,'REVIEWS_INCOMPLETE');
  const eligible=reviews.filter(r=>trust.approvedReviewerIds.includes(r?.user?.id));
  requireFact(eligible.every(r=>Number.isSafeInteger(r.id)&&DATES(r.submitted_at)),
    'REVIEW_HISTORY_UNREADABLE');
  const latest=new Map();
  for(const r of eligible){
    const old=latest.get(r.user.id);
    if(!old||Date.parse(r.submitted_at)>Date.parse(old.submitted_at)||
      (r.submitted_at===old.submitted_at&&r.id>old.id))latest.set(r.user.id,r);
  }
  // An allowlisted reviewer withdrawing/challenging the approval blocks a
  // conflicting positive from another reviewer on this exact head.
  const current=[...latest.values()];
  if(current.some(r=>r.state==='CHANGES_REQUESTED'||r.state==='DISMISSED'))return null;
  return current.find(r=>explicitReview(r,trust,pr,run))??null;
}

/**
 * Source and trust configuration MUST be supplied out-of-band by an app admin.
 * No mutations, comments, PR approvals or Check Runs are written by this API.
 */
export async function observeGitHubMathSource(input){
  const options={...input,fetcher:input?.fetcher??fetch};
  if(!validOptions(options))return unknown('INVALID_INDEPENDENT_TRUST_SCOPE');
  const {repository,pr,runId,token,fetcher,trusted:t}=options;
  const subject={repository,pr,head_sha:t.headSha};
  const read=async path=>{
    const url='https://api.github.com/repos/'+repository+path;
    const r=await fetcher(url,{method:'GET',redirect:'error',
      headers:{Accept:'application/vnd.github+json',Authorization:'Bearer '+token,
        'X-GitHub-Api-Version':'2022-11-28'},signal:AbortSignal.timeout(15000)});
    requireFact(r?.ok===true,'GITHUB_READ_FAILED');
    return r.json();
  };
  let target,run;
  try{
    target=await read('/pulls/'+pr);
    run=await read('/actions/runs/'+runId);
    validateRun(target,run,t,runId);
  }catch{return unknown('GITHUB_RUN_OR_HEAD_UNVERIFIED',subject);}

  let replay={status:'UNKNOWN'},review={status:'UNKNOWN'};
  try{
    const [file,jobs,artifacts]=await Promise.all([
      read('/contents/'+t.workflowPath+'?ref='+t.headSha),
      read('/actions/runs/'+runId+'/jobs?per_page=100'),
      read('/actions/runs/'+runId+'/artifacts?per_page=100'),
    ]);
    requireFact(sha(workflowContent(file))===t.workflowSha256,
      'INDEPENDENT_VERIFIER_PIN_MISMATCH');
    const {job,artifact}=validJobAndArtifact(jobs,artifacts,run,t);
    replay={status:'PINNED_REPLAY_OBSERVED',run_id:runId,run_attempt:run.run_attempt,
      job_id:job.id,artifact_id:artifact.id,artifact_digest:artifact.digest,
      workflow_sha256:t.workflowSha256,
      evidence_scope:'GITHUB_RUN_JOB_AND_ARTIFACT_METADATA',
      artifact_bytes:'NOT_DOWNLOADED'};
  }catch{replay={status:'UNKNOWN'};}

  try{
    const reviews=await read('/pulls/'+pr+'/reviews?per_page=100');
    const r=latestReviewer(reviews,t,target,run);
    if(r)review={status:'SOURCE_TO_FORMAL_REVIEWED',review_id:r.id,
      reviewer_id:r.user.id,reviewed_head_sha:t.headSha,
      evidence_scope:'EXPLICIT_SOURCE_AND_THEOREM_HASH_REVIEW'};
  }catch{review={status:'UNKNOWN'};}

  // A run can be retried and the PR head can move while separate endpoints
  // are being read. Recheck both identities at the end; never report the
  // earlier successful attempt as applying to the new live state.
  try{
    const [latestPr,latestRun]=await Promise.all([
      read('/pulls/'+pr),read('/actions/runs/'+runId),
    ]);
    validateRun(latestPr,latestRun,t,runId);
    requireFact(latestPr.base.sha===target.base.sha&&
      latestRun.run_attempt===run.run_attempt&&
      latestRun.run_started_at===run.run_started_at,
    'GITHUB_HEAD_OR_ATTEMPT_MOVED');
  }catch{return unknown('GITHUB_HEAD_OR_ATTEMPT_MOVED_DURING_OBSERVATION',subject);}

  const both=replay.status==='PINNED_REPLAY_OBSERVED'&&
    review.status==='SOURCE_TO_FORMAL_REVIEWED';
  return {schema:GITHUB_MATH_OBSERVATION_SCHEMA,
    status:both?'OBSERVED':'UNKNOWN',
    reason:both?'BOUNDED_INDEPENDENT_GITHUB_OBSERVATIONS':'MISSING_OR_UNQUALIFIED_REPLAY_OR_REVIEW',
    subject,replay,review,receipt_qualification:'NOT_YET_CONTRACT_BOUND',
    conclusion:'neutral',permission:'ADVISORY_ONLY',intent_verification:'NOT_ESTABLISHED'};
}
