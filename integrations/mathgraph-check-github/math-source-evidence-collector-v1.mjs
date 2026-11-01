/**
 * Read-only correlation of independently authenticated GitHub replay metadata,
 * the GitHub artifact ZIP bytes, and exact upstream mathematical source bytes.
 * No output from this module is a semantic-equivalence certificate, trusted
 * intent-probes receipt, GitHub Check Run, or permission to act.
 */
import {ARTIN_PIN} from './proofnet-artin-replay-v1.mjs';
import {observeGitHubMathSource}
  from './math-source-github-host-v1.mjs';
import {verifyPinnedArtinArtifactBytes,verifyPinnedArtinUpstreamBytes}
  from './math-source-evidence-bytes-v1.mjs';
import {fetchPinnedArtifactZip,fetchPinnedArtinUpstream}
  from './math-source-evidence-fetch-v1.mjs';

export const MATH_EVIDENCE_COLLECTOR_SCHEMA='mathgraph.artin-evidence-collector.v1';
const CLAIM_SHA256='a908ad4a14106793dec67703b4051fd3587be202fcd94c5778981cab409051a0';
const SHA40=/^[0-9a-f]{40}$/;

const unknown=(reason,subject=null)=>({
  schema:MATH_EVIDENCE_COLLECTOR_SCHEMA,status:'UNKNOWN',reason,subject,
  replay:{status:'UNKNOWN'},review:{status:'UNKNOWN'},
  receipt_qualification:'NOT_YET_CONTRACT_BOUND',intent_verification:'NOT_ESTABLISHED',
  permission:'ADVISORY_ONLY',conclusion:'neutral',
});

function validPin(t){
  return t&&typeof t==='object'&&
    t.sourceSha256===ARTIN_PIN.sourceSha256&&
    t.claimSha256===CLAIM_SHA256&&
    t.formalSha256===ARTIN_PIN.formalSha256&&
    t.workflowPath==='.github/workflows/mathgraph-check-proofnet-artin-replay-v1.yml'&&
    t.jobName==='pinned-artin-replay'&&
    t.artifactName==='mathgraph-proofnet-artin-evidence'&&
    SHA40.test(t.headSha??'');
}

function stableReplay(a,b){
  if(a?.replay?.status!=='PINNED_REPLAY_OBSERVED'||
    b?.replay?.status!=='PINNED_REPLAY_OBSERVED')return false;
  return a.subject?.repository===b.subject?.repository&&
    a.subject?.pr===b.subject?.pr&&a.subject?.head_sha===b.subject?.head_sha&&
    ['run_id','run_attempt','job_id','artifact_id','artifact_digest','workflow_sha256']
      .every(k=>a.replay[k]===b.replay[k]);
}

function stableReview(a,b){
  if(a?.review?.status!==b?.review?.status)return false;
  if(a?.review?.status!=='SOURCE_TO_FORMAL_REVIEWED')return true;
  return a.review.review_id===b.review.review_id&&
    a.review.reviewer_id===b.review.reviewer_id&&
    a.review.reviewed_head_sha===b.review.reviewed_head_sha;
}

/**
 * The caller supplies an installation-scoped token and an *independent admin*
 * trust manifest. It must NOT derive the manifest from PR content.
 */
export async function collectMathSourceEvidence(input){
  if(!input||typeof input!=='object'||!validPin(input.trusted))
    return unknown('INVALID_PINNED_ARTIN_TRUST_SCOPE');
  // A fresh local copy prevents an external async caller changing the pins
  // between the two authenticated GitHub readbacks.
  let trusted;
  try{trusted=structuredClone(input.trusted);}catch{
    return unknown('INVALID_PINNED_ARTIN_TRUST_SCOPE');
  }
  const {repository,pr,runId,token,fetcher=fetch}=input;
  const subject={repository,pr,head_sha:trusted.headSha};
  const hostInput={repository,pr,runId,token,trusted,fetcher};
  let first;
  try{first=await observeGitHubMathSource(hostInput);}catch{
    return unknown('GITHUB_REPLAY_UNVERIFIED',subject);
  }
  if(first.replay?.status!=='PINNED_REPLAY_OBSERVED'||
    first.subject?.head_sha!==trusted.headSha||
    first.subject?.repository!==repository||first.subject?.pr!==pr)
    return unknown('GITHUB_REPLAY_UNVERIFIED',subject);

  let artifact,upstream;
  try{
    const zipBytes=await fetchPinnedArtifactZip({repository,
      artifactId:first.replay.artifact_id,token,fetcher});
    artifact=verifyPinnedArtinArtifactBytes({zipBytes,
      artifactDigest:first.replay.artifact_digest});
    upstream=verifyPinnedArtinUpstreamBytes(await fetchPinnedArtinUpstream({fetcher}));
  }catch{return unknown('ARTIFACT_OR_UPSTREAM_BYTES_UNVERIFIED',subject);}

  let last;
  try{last=await observeGitHubMathSource(hostInput);}catch{
    return unknown('GITHUB_READBACK_UNVERIFIED',subject);
  }
  if(!stableReplay(first,last)||!stableReview(first,last))
    return unknown('GITHUB_HEAD_ATTEMPT_ARTIFACT_OR_REVIEW_MOVED',subject);

  return {schema:MATH_EVIDENCE_COLLECTOR_SCHEMA,
    status:'EVIDENCE_BYTES_CORRELATED',
    reason:last.review?.status==='SOURCE_TO_FORMAL_REVIEWED'?
      'INDEPENDENT_REVIEW_ATTESTED_NOT_SEMANTICALLY_PROVED':
      'SOURCE_TO_FORMAL_HUMAN_REVIEW_NOT_ESTABLISHED',
    subject,replay:{status:'PINNED_REPLAY_OBSERVED',
      run_id:last.replay.run_id,run_attempt:last.replay.run_attempt,
      job_id:last.replay.job_id,artifact_id:last.replay.artifact_id,
      artifact_digest:last.replay.artifact_digest,
      evidence_scope:'GITHUB_RUN_JOB_ARTIFACT_PLUS_PINNED_BYTES'},
    artifact,upstream,
    review:last.review?.status==='SOURCE_TO_FORMAL_REVIEWED'?{
      status:'SOURCE_TO_FORMAL_REVIEWED',review_id:last.review.review_id,
      reviewer_id:last.review.reviewer_id,
      evidence_scope:'INDEPENDENT_REVIEW_ATTESTATION_ONLY'}:{status:'UNKNOWN'},
    environment:'REQUESTED_LEAN_AND_MATHLIB_TAGS_ONLY',
    receipt_qualification:'NOT_YET_CONTRACT_BOUND',intent_verification:'NOT_ESTABLISHED',
    permission:'ADVISORY_ONLY',conclusion:'neutral'};
}
