/**
 * Pure, advisory bridge from a pinned mathematical source and Lean statement
 * to the existing MathGraph Check intent/probe contract. This module neither
 * authenticates humans nor runs Lean nor publishes to GitHub. The host must
 * supply qualified authority independently of all PR-authored inputs.
 */
import {createHash} from 'node:crypto';
import {auditIntent,digestContract,SCHEMA as INTENT_SCHEMA} from './intent-contract-v1.mjs';
import {buildAdvisoryCheck} from './advisory-publisher-v1.mjs';

export const MATH_SOURCE_SCHEMA='mathgraph.math-source.v1';
const SHA40=/^[a-f0-9]{40}$/;
const SHA256=/^[a-f0-9]{64}$/;
const REPO=/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
const HASH=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
const obj=x=>x!==null&&typeof x==='object'&&!Array.isArray(x)&&
  (Object.getPrototypeOf(x)===Object.prototype||Object.getPrototypeOf(x)===null);
const exactly=(x,ks)=>obj(x)&&Object.keys(x).length===ks.length&&ks.every(k=>Object.hasOwn(x,k));

function validManifest(m){
  if(!exactly(m,['schema','subject','source','formal','checks'])||m.schema!==MATH_SOURCE_SCHEMA)return false;
  const s=m.subject,src=m.source,f=m.formal,c=m.checks;
  if(!exactly(s,['repository','pr','base_sha','head_sha'])||!REPO.test(s.repository)||
    !Number.isSafeInteger(s.pr)||s.pr<1||!SHA40.test(s.base_sha)||!SHA40.test(s.head_sha))return false;
  if(!exactly(src,['reference','sha256','claim_sha256'])||
    typeof src.reference!=='string'||!/^https:\/\/[^\s]+$/.test(src.reference)||
    src.reference.length>1024||!SHA256.test(src.sha256)||!SHA256.test(src.claim_sha256))return false;
  if(!exactly(f,['path','statement_sha256','environment_sha256'])||
    typeof f.path!=='string'||f.path.length>240||!/^[-A-Za-z0-9_./]+$/.test(f.path)||
    f.path.split('/').some(x=>!x||x==='.'||x==='..')||
    !SHA256.test(f.statement_sha256)||!SHA256.test(f.environment_sha256))return false;
  if(!exactly(c,['review','replay']))return false;
  if(![c.review,c.replay].every(p=>exactly(p,['oracle_sha256','verifier_sha'])&&
    SHA256.test(p.oracle_sha256)&&SHA40.test(p.verifier_sha)))return false;
  return Buffer.byteLength(JSON.stringify(m))<=8192;
}

/** Deterministic domain binding: neither contract nor self-hash grants authority. */
export function buildMathIntentContract(manifest){
  if(!validManifest(manifest))throw Error('INVALID_MATH_SOURCE_MANIFEST');
  const m=manifest;
  return {schema:INTENT_SCHEMA,
    subject:{...m.subject},
    claims:[
      {id:'math-source-review',
        statement:`Qualified human comparison of source ${m.source.sha256}, source claim ${m.source.claim_sha256}, and Lean statement ${m.formal.statement_sha256}.`,
        requires:['source-review']},
      {id:'math-lean-replay',
        statement:`Exact Lean replay of theorem ${m.formal.statement_sha256} in environment ${m.formal.environment_sha256}.`,
        requires:['lean-replay']},
    ],
    probes:[
      {id:'source-review',
        input_sha256:HASH({source:m.source,statement_sha256:m.formal.statement_sha256}),
        oracle_sha256:m.checks.review.oracle_sha256,verifier_sha:m.checks.review.verifier_sha},
      {id:'lean-replay',
        input_sha256:HASH({formal:m.formal}),
        oracle_sha256:m.checks.replay.oracle_sha256,verifier_sha:m.checks.replay.verifier_sha},
    ]};
}

const unknown=(reason,subject=null,contract_sha256=null)=>({
  schema:MATH_SOURCE_SCHEMA,status:'UNKNOWN',reason,
  source_review:'UNKNOWN',formal_replay:'UNKNOWN',
  permission:'ADVISORY_ONLY',intent_verification:'NOT_ESTABLISHED',
  checked_scope:'NONE',subject,contract_sha256,
  next_actions:['QUALIFY_EXACT_SOURCE_AND_THEOREM','OBTAIN_HUMAN_REVIEW','REPLAY_LEAN_IN_PINNED_ENVIRONMENT'],
});

/**
 * An OBSERVED result only records independent review/replay receipts. It is
 * NOT a proof that the original natural-language intent is equivalent to Lean.
 */
export function auditMathSource(manifest,receipts,authority={}){
  let contract;
  try{contract=buildMathIntentContract(manifest);}catch{return unknown('INVALID_MATH_SOURCE_MANIFEST');}
  const sha=digestContract(contract);
  const base=auditIntent(contract,receipts,authority);
  if(base.reason!=='BOUNDED_PROBE_AUDIT')
    return unknown(base.reason,contract.subject,sha);

  // These hashes MUST be independently fetched/derived by the trusted host,
  // never taken from PR metadata or an AI-supplied self-attestation.
  if(!obj(authority)||authority.observedSourceSha256!==manifest.source.sha256||
    authority.observedClaimSha256!==manifest.source.claim_sha256||
    authority.observedFormalSha256!==manifest.formal.statement_sha256||
    authority.observedEnvironmentSha256!==manifest.formal.environment_sha256)
    return unknown('INDEPENDENT_SOURCE_OBSERVATION_REQUIRED',contract.subject,sha);
  if(!Array.isArray(authority.qualifiedHumanReviewReceiptIds)||
    !Array.isArray(authority.qualifiedLeanReplayReceiptIds))
    return unknown('SPECIALIST_AUTHORITY_REQUIRED',contract.subject,sha);

  const review=base.results.find(x=>x.id==='math-source-review')?.probes?.[0];
  const replay=base.results.find(x=>x.id==='math-lean-replay')?.probes?.[0];
  const reviewOk=review?.status==='OBSERVED'&&
    authority.qualifiedHumanReviewReceiptIds.includes(review.receipt_id);
  const replayOk=replay?.status==='OBSERVED'&&
    authority.qualifiedLeanReplayReceiptIds.includes(replay.receipt_id);
  const source_review=reviewOk?'SOURCE_TO_FORMAL_REVIEWED':'UNKNOWN';
  const formal_replay=replayOk?'FORMAL_REPLAY_PASSED':'UNKNOWN';
  return {schema:MATH_SOURCE_SCHEMA,
    status:reviewOk&&replayOk?'OBSERVED':'UNKNOWN',
    reason:reviewOk&&replayOk?'QUALIFIED_PINNED_RECEIPTS_ONLY':'SPECIALIST_AUTHORITY_MISSING_OR_INCONCLUSIVE',
    source_review,formal_replay,
    permission:'ADVISORY_ONLY',intent_verification:'NOT_ESTABLISHED',
    checked_scope:'EXACT_PINNED_RECEIPTS_ONLY',subject:contract.subject,
    contract_sha256:sha,
    next_actions:[...(reviewOk?[]:['OBTAIN_QUALIFIED_HUMAN_SOURCE_REVIEW']),
      ...(replayOk?[]:['REPLAY_LEAN_WITH_INDEPENDENT_QUALIFIED_VERIFIER'])],
  };
}

/** API payload only: trusted expected head is mandatory; never calls GitHub. */
export function toAdvisoryCheckRun(report,expectedHeadSha){
  if(!obj(report)||report.schema!==MATH_SOURCE_SCHEMA||
    !obj(report.subject)||!SHA40.test(report.subject.head_sha)||
    !(report.contract_sha256===null&&report.status==='UNKNOWN'||
      typeof report.contract_sha256==='string'&&SHA256.test(report.contract_sha256))||
    !['OBSERVED','UNKNOWN'].includes(report.status)||
    !['SOURCE_TO_FORMAL_REVIEWED','UNKNOWN'].includes(report.source_review)||
    !['FORMAL_REPLAY_PASSED','UNKNOWN'].includes(report.formal_replay)||
    (report.status==='OBSERVED')!==
      (report.source_review==='SOURCE_TO_FORMAL_REVIEWED'&&report.formal_replay==='FORMAL_REPLAY_PASSED')||
    report.permission!=='ADVISORY_ONLY'||report.intent_verification!=='NOT_ESTABLISHED')
    throw Error('INVALID_MATH_SOURCE_REPORT');
  if(!SHA40.test(expectedHeadSha)||report.subject.head_sha!==expectedHeadSha)
    throw Error('UNBOUND_CHECK_HEAD');
  const lines=[
    `Source-to-formal human review receipt: ${report.source_review}`,
    `Pinned Lean replay receipt: ${report.formal_replay}`,
    `Contract SHA-256: ${report.contract_sha256??'UNBOUND'}`,
    'Intent verification: NOT_ESTABLISHED',
    'Permission: ADVISORY_ONLY — no merge authorization, no mathematical equivalence certificate.',
    'Missing, changed, or unqualified evidence must be independently rechecked.',
  ];
  const reviewStatus=report.source_review==='SOURCE_TO_FORMAL_REVIEWED'?'OBSERVED':'UNKNOWN';
  const replayStatus=report.formal_replay==='FORMAL_REPLAY_PASSED'?'OBSERVED':'UNKNOWN';
  const results=[{id:'human-source-to-formal-review',status:reviewStatus},
    {id:'pinned-Lean-kernel-replay',status:replayStatus}];
  const generic={source:report.subject,status:report.status,
    permission:'ADVISORY_ONLY',scope:'GITHUB_CHECK_RUN_OBSERVATION_ONLY',
    results,evidence:results.filter(r=>r.status==='OBSERVED')};
  // Reuse the app's established destination validation and neutral payload
  // generation. Publishing remains a separate, explicitly gated operation.
  const built=buildAdvisoryCheck(generic,{repository:report.subject.repository,sha:expectedHeadSha});
  // Separate GitHub Check identity avoids colliding with the app's ordinary
  // advisory evidence run for the same repository and exact commit.
  return {...built,name:'MathGraph Check / math source (advisory)',
    external_id:'mathgraph-math-source-v1:'+report.subject.repository+':'+expectedHeadSha,
    output:{title:report.status==='OBSERVED'?
    'Recorded source review and Lean replay receipts (advisory)':
    'Math source evidence incomplete (advisory)',
    summary:built.output.summary+'\n\n'+lines.join('\n\n')}};
}
