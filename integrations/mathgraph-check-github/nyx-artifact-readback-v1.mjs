// Readback consistency across the archived bytes and caller-supplied GitHub
// metadata. This is NOT a GitHub API client or an origin authenticator.
import { createHash } from 'node:crypto';
import { buildNyxRunReceiptV1, combineNyxRunReceiptsV1 } from './run-nyx-event-frame-v1.mjs';

const REPOSITORY='metalogiclabs/mathgraph';
const WORKFLOW='.github/workflows/mathgraph-check-nyx-event-frame-v1.yml';
const BRANCH='research/mathgraph-check-nyx-v1-20261102';
const SHA=/^[a-f0-9]{40}$/;

export function verifyNyxArtifactReadbackV1({combined,logs,lockfile,metadata} = {}) {
  const errors=[];
  const unknowns=['CALLER_SUPPLIED_GITHUB_METADATA_NOT_AUTHENTICATED','REQUIREMENT_AUTHOR_INTENT_NOT_INDEPENDENTLY_AUTHENTICATED'];
  const receipt=combined?.receipt;
  const supplied=combined?.verdict;
  if (metadata?.repository?.full_name!==REPOSITORY ||
      metadata?.head_branch!==BRANCH || metadata?.path!==WORKFLOW ||
      !SHA.test(metadata?.head_sha??'') ||
      !Number.isSafeInteger(metadata?.id) || metadata.id<=0 ||
      metadata?.status!=='completed' || metadata?.conclusion!=='success') {
    errors.push('GITHUB_RUN_METADATA_INVALID_OR_FAILED');
  }
  if (receipt?.runner?.workflowRunUrl!==`https://github.com/${REPOSITORY}/actions/runs/${metadata?.id}`) {
    errors.push('RECEIPT_RUN_ID_MISMATCH');
  }
  if (!receipt || typeof lockfile!=='string') errors.push('REQUIRED_ARTIFACT_MISSING');
  if (receipt?.toolchain?.cargoLockSha256!==createHash('sha256').update(String(lockfile??'')).digest('hex')) {
    errors.push('CARGO_LOCK_DIGEST_MISMATCH');
  }
  for (const mode of ['base','head']) {
    const stdout=logs?.[mode]?.stdout;
    const stderr=logs?.[mode]?.stderr;
    if (typeof stdout!=='string' || typeof stderr!=='string' || !receipt?.[mode]) {
      errors.push(`${mode.toUpperCase()}_LOGS_MISSING`);
      continue;
    }
    const rebuilt=buildNyxRunReceiptV1({
      mode,exitCode:receipt[mode].exitCode,stdout,stderr,sourceSha:receipt[mode].sourceSha
    });
    for (const key of ['exitCode','sourceSha','testCount','reason','regressionMarker','logSha256']) {
      if (receipt[mode][key]!==rebuilt[key]) errors.push(`${mode.toUpperCase()}_${key.toUpperCase()}_MISMATCH`);
    }
  }

  if (receipt && receipt.base && receipt.head && typeof lockfile==='string') {
    const rebuilt=combineNyxRunReceiptsV1({
      base:receipt.base,head:receipt.head,rustc:receipt.toolchain?.rustc,
      cargoLockSha256:receipt.toolchain?.cargoLockSha256,
      workflowRunUrl:receipt.runner?.workflowRunUrl
    });
    if (rebuilt.verdict.status!=='CANDIDATE_BOUNDED' || supplied?.status!=='CANDIDATE_BOUNDED' ||
        JSON.stringify(rebuilt.receipt.source)!==JSON.stringify(receipt.source)) {
      errors.push('BOUNDED_RECEIPT_NOT_QUALIFIED');
    }
  }
  return {
    schema:'mathgraph.nyx-artifact-readback.v1',
    status:errors.length===0?'READBACK_CONSISTENT':'UNKNOWN',
    authority:'ADVISORY_ONLY',
    errors,
    unknowns:[...unknowns,...(errors.length?['ARTIFACT_READBACK_FAILED']:[])],
    runUrl:errors.length===0?receipt.runner.workflowRunUrl:null
  };
}
