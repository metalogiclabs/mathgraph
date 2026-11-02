// Pure internal-consistency recheck of a downloaded archive. The caller must
// independently authenticate the origin of GitHub metadata and artifact bytes.
import {createHash} from 'node:crypto';
import {BRAHE_SOURCE_V1} from './brahe-endpoint-v1.mjs';
import {buildBraheRunReceiptV1,combineBraheReceiptsV1} from './run-brahe-endpoint-v1.mjs';

const HASH=/^[a-f0-9]{64}$/;
const SHA=/^[a-f0-9]{40}$/;

export function verifyBraheArtifactReadbackV1({combined,logs,lockfile,transplantManifest,metadata}={}) {
  const errors=[];
  const receipt=combined?.receipt;
  if (metadata?.repository?.full_name!=='metalogiclabs/mathgraph'||
      metadata?.head_branch!=='research/mathgraph-check-brahe-v1-20261102'||
      metadata?.path!=='.github/workflows/mathgraph-check-brahe-endpoint-v1.yml'||
      !Number.isSafeInteger(metadata?.id)||metadata.id<=0||!SHA.test(metadata?.head_sha??'')||
      metadata?.status!=='completed'||metadata?.conclusion!=='success') {
    errors.push('GITHUB_RUN_METADATA_INVALID_OR_FAILED');
  }
  if (receipt?.runner?.workflowRunUrl!==`https://github.com/metalogiclabs/mathgraph/actions/runs/${metadata?.id}`)
    errors.push('RECEIPT_RUN_ID_MISMATCH');
  for (const [key,value] of Object.entries(BRAHE_SOURCE_V1)) {
    if (receipt?.source?.[key]!==value||transplantManifest?.source?.[key]!==value)
      errors.push('SOURCE_PIN_MISMATCH_'+key.toUpperCase());
  }
  if (!HASH.test(transplantManifest?.patchedSourceSha256??'')||
      !Number.isSafeInteger(transplantManifest?.baseProductionBytes)||transplantManifest.baseProductionBytes<=0||
      !Number.isSafeInteger(transplantManifest?.headTestModuleBytes)||transplantManifest.headTestModuleBytes<=0||
      !SHA.test(receipt?.source?.basePatchedBlobSha??''))
    errors.push('TRANSPLANT_MANIFEST_INCOMPLETE');
  if (typeof lockfile!=='string'||receipt?.toolchain?.cargoLockSha256!==createHash('sha256').update(String(lockfile??'')).digest('hex'))
    errors.push('CARGO_LOCK_MISMATCH');
  for (const mode of ['base','head']) {
    const stdout=logs?.[mode]?.stdout,stderr=logs?.[mode]?.stderr;
    if (typeof stdout!=='string'||typeof stderr!=='string'||!receipt?.[mode]) {
      errors.push(mode.toUpperCase()+'_LOGS_MISSING');continue;
    }
    const rebuilt=buildBraheRunReceiptV1({mode,sourceSha:receipt[mode].sourceSha,exitCode:receipt[mode].exitCode,stdout,stderr});
    for (const key of ['sourceSha','exitCode','testCount','regressionCount','reason','logSha256']) {
      if (rebuilt[key]!==receipt[mode][key])errors.push(mode.toUpperCase()+'_'+key.toUpperCase()+'_MISMATCH');
    }
  }
  if (receipt?.base&&receipt?.head) {
    const again=combineBraheReceiptsV1({
      base:receipt.base,head:receipt.head,rustc:receipt.toolchain?.rustc,
      cargoLockSha256:receipt.toolchain?.cargoLockSha256,
      basePatchedBlobSha:receipt.source?.basePatchedBlobSha,
      workflowRunUrl:receipt.runner?.workflowRunUrl
    });
    if (again.verdict.status!=='CANDIDATE_BOUNDED'||combined?.verdict?.status!=='CANDIDATE_BOUNDED')
      errors.push('BOUNDED_RECEIPT_NOT_QUALIFIED');
  } else errors.push('REQUIRED_RECEIPT_MISSING');
  return {
    schema:'mathgraph.brahe-artifact-readback.v1',
    status:errors.length===0?'READBACK_CONSISTENT':'UNKNOWN',
    authority:'ADVISORY_ONLY',errors,
    unknowns:['CALLER_SUPPLIED_GITHUB_METADATA_NOT_AUTHENTICATED','TRANSPLANT_SOURCE_BYTES_NOT_IN_ARCHIVE','EXTERNAL_CHECK_USE_UNKNOWN',...(errors.length?['ARTIFACT_READBACK_FAILED']:[])],
    runUrl:errors.length===0?receipt.runner.workflowRunUrl:null
  };
}
