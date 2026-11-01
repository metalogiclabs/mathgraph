/**
 * Pure bounded correlation of an already authenticated replay observation and
 * an independently retrieved GitHub environment artifact. Caller MUST get
 * primary/record from the GitHub host and artifact API, not from PR content.
 */
import {verifyPinnedArtinEnvironmentArtifactBytes}
  from './math-source-environment-closure-v1.mjs';
import {collectMathSourceEvidence}
  from './math-source-evidence-collector-v1.mjs';
import {fetchPinnedArtifactZip}
  from './math-source-evidence-fetch-v1.mjs';

export const ENVIRONMENT_CORRELATION_SCHEMA='mathgraph.artin-environment-correlation.v1';
const SHA40=/^[a-f0-9]{40}$/;
const SHA256=/^[a-f0-9]{64}$/;
const unknown=reason=>({schema:ENVIRONMENT_CORRELATION_SCHEMA,status:'UNKNOWN',reason,
  replay:{status:'UNKNOWN'},review:{status:'UNKNOWN'},
  permission:'ADVISORY_ONLY',intent_verification:'NOT_ESTABLISHED',
  receipt_qualification:'NOT_YET_CONTRACT_BOUND',conclusion:'neutral'});

export function correlatePinnedEnvironmentArtifact({primary,environmentArtifact:a,
  trusted:t,zipBytes}={}){
  if(primary?.schema!=='mathgraph.artin-evidence-collector.v1'||
    primary.status!=='EVIDENCE_BYTES_CORRELATED'||
    primary.permission!=='ADVISORY_ONLY'||
    primary.intent_verification!=='NOT_ESTABLISHED'||
    primary.conclusion!=='neutral'||
    primary.replay?.status!=='PINNED_REPLAY_OBSERVED'||
    !Number.isSafeInteger(primary.replay.run_id)||primary.replay.run_id<1||
    !Number.isSafeInteger(primary.replay.artifact_id)||primary.replay.artifact_id<1||
    !Number.isSafeInteger(primary.replay.run_attempt)||primary.replay.run_attempt<1||
    !SHA40.test(primary.subject?.head_sha??'')||
    !SHA40.test(t?.headSha??'')||t.headSha!==primary.subject.head_sha||
    !SHA256.test(t?.environmentSha256??''))return unknown('PRIMARY_OR_TRUST_UNQUALIFIED');
  if(a?.name!=='mathgraph-proofnet-artin-environment'||a.expired!==false||
    !Number.isSafeInteger(a.id)||a.id<1||a.id===primary.replay.artifact_id||
    !Number.isSafeInteger(a.size_in_bytes)||a.size_in_bytes<1||
    a.size_in_bytes>2*1024*1024||!Buffer.isBuffer(zipBytes)||
    zipBytes.length!==a.size_in_bytes||
    !/^sha256:[a-f0-9]{64}$/.test(a.digest??'')||
    a.workflow_run?.id!==primary.replay.run_id||
    a.workflow_run?.head_sha!==primary.subject.head_sha||
    !Number.isSafeInteger(a.workflow_run?.repository_id)||
    a.workflow_run.repository_id<1)return unknown('ENVIRONMENT_ARTIFACT_OUT_OF_SCOPE');
  let env;
  try{env=verifyPinnedArtinEnvironmentArtifactBytes({
    zipBytes,artifactDigest:a.digest});}
  catch{return unknown('ENVIRONMENT_BYTES_UNVERIFIED');}
  if(env.environment_sha256!==t.environmentSha256)
    return unknown('ENVIRONMENT_TRUST_DIGEST_MISMATCH');
  return {schema:ENVIRONMENT_CORRELATION_SCHEMA,
    status:'ENVIRONMENT_AND_REPLAY_CORRELATED',
    reason:'PINNED_REPLAY_AND_RESOLVED_ENVIRONMENT_BYTES_CORRELATED',
    subject:primary.subject,replay:primary.replay,
    environment_artifact_id:a.id,environment_artifact_digest:a.digest,
    environment:env,
    review:primary.review?.status==='SOURCE_TO_FORMAL_REVIEWED'?
      primary.review:{status:'UNKNOWN'},
    permission:'ADVISORY_ONLY',intent_verification:'NOT_ESTABLISHED',
    receipt_qualification:'NOT_YET_CONTRACT_BOUND',conclusion:'neutral'};
}

function samePrimary(a,b){
  if(a?.status!=='EVIDENCE_BYTES_CORRELATED'||
    b?.status!=='EVIDENCE_BYTES_CORRELATED')return false;
  const p=x=>x.replay;
  return a.subject?.repository===b.subject?.repository&&
    a.subject?.pr===b.subject?.pr&&a.subject?.head_sha===b.subject?.head_sha&&
    ['run_id','run_attempt','job_id','artifact_id','artifact_digest']
      .every(k=>p(a)?.[k]===p(b)?.[k])&&
    a.review?.status===b.review?.status&&
    (a.review?.status!=='SOURCE_TO_FORMAL_REVIEWED'||
      (a.review.review_id===b.review.review_id&&
        a.review.reviewer_id===b.review.reviewer_id));
}

async function readEnvironmentMetadata({repository,runId,token,fetcher},primary){
  const url=`https://api.github.com/repos/${repository}/actions/runs/${runId}/artifacts?per_page=100`;
  const response=await fetcher(url,{method:'GET',redirect:'error',
    headers:{Accept:'application/vnd.github+json',
      'X-GitHub-Api-Version':'2022-11-28',Authorization:'Bearer '+token},
    signal:AbortSignal.timeout(15000)});
  if(response?.ok!==true)throw Error('ARTIFACTS_READ_FAILED');
  const data=await response.json();
  if(!Array.isArray(data?.artifacts)||data.total_count!==2||data.artifacts.length!==2)
    throw Error('ENVIRONMENT_ARTIFACTS_INCOMPLETE');
  const original=data.artifacts.filter(a=>a.name==='mathgraph-proofnet-artin-evidence');
  const closure=data.artifacts.filter(a=>a.name==='mathgraph-proofnet-artin-environment');
  if(original.length!==1||closure.length!==1||
    original[0].id!==primary.replay.artifact_id||
    original[0].digest!==primary.replay.artifact_digest||
    original[0].expired!==false||
    original[0].workflow_run?.id!==primary.replay.run_id||
    original[0].workflow_run?.head_sha!==primary.subject.head_sha||
    original[0].workflow_run?.repository_id!==closure[0].workflow_run?.repository_id)
    throw Error('ENVIRONMENT_ARTIFACTS_OUT_OF_SCOPE');
  return closure[0];
}

function stableArtifact(a,b){
  return a?.id===b?.id&&a?.digest===b?.digest&&
    a?.size_in_bytes===b?.size_in_bytes&&a?.expired===false&&b?.expired===false&&
    a?.workflow_run?.id===b?.workflow_run?.id&&
    a?.workflow_run?.head_sha===b?.workflow_run?.head_sha&&
    a?.workflow_run?.repository_id===b?.workflow_run?.repository_id;
}

/**
 * Full V2 read-only backend observation. The operator-supplied environment
 * SHA is bound to a *second artifact from the same run*, with another full
 * GitHub PR/run observation and artifact-list readback after the download.
 */
export async function collectMathSourceEvidenceWithEnvironment(input){
  if(!input||input.trusted?.workflowPath!==
      '.github/workflows/mathgraph-check-proofnet-artin-replay-v2.yml'||
      !SHA256.test(input.trusted?.environmentSha256??''))
    return unknown('INVALID_V2_ENVIRONMENT_TRUST_SCOPE');
  let trusted;
  try{trusted=structuredClone(input.trusted);}catch{
    return unknown('INVALID_V2_ENVIRONMENT_TRUST_SCOPE');
  }
  const options={...input,trusted},fetcher=input.fetcher??fetch;
  const first=await collectMathSourceEvidence(options);
  if(first.status!=='EVIDENCE_BYTES_CORRELATED')
    return unknown('PRIMARY_GITHUB_REPLAY_OR_BYTES_UNVERIFIED');
  let initial,joined;
  try{
    initial=await readEnvironmentMetadata({...options,fetcher},first);
    const bytes=await fetchPinnedArtifactZip({repository:options.repository,
      artifactId:initial.id,token:options.token,fetcher});
    joined=correlatePinnedEnvironmentArtifact({primary:first,
      environmentArtifact:initial,trusted,zipBytes:bytes});
  }catch{return unknown('ENVIRONMENT_ARTIFACT_UNVERIFIED');}
  if(joined.status!=='ENVIRONMENT_AND_REPLAY_CORRELATED')
    return unknown('ENVIRONMENT_ARTIFACT_UNVERIFIED');

  const last=await collectMathSourceEvidence(options);
  if(!samePrimary(first,last))return unknown('GITHUB_REPLAY_OR_REVIEW_MOVED');
  try{
    const final=await readEnvironmentMetadata({...options,fetcher},last);
    if(!stableArtifact(initial,final))return unknown('ENVIRONMENT_ARTIFACT_MOVED');
  }catch{return unknown('ENVIRONMENT_ARTIFACT_READBACK_FAILED');}
  return {...joined,subject:last.subject,replay:last.replay,review:last.review};
}
