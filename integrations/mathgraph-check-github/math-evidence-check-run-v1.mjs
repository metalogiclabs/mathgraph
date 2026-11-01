/**
 * Opt-in GitHub Check Run surface for the independent mathematical evidence
 * collector. An observed proof/replay is NOT a semantic equivalence warrant.
 * Default is dry-run; publishing requires a separately scoped GitHub App token.
 */
import {buildAdvisoryCheck} from './advisory-publisher-v1.mjs';
import {collectMathSourceEvidenceWithEnvironment} from './math-source-environment-correlation-v1.mjs';
import {ARTIN_PIN} from './proofnet-artin-replay-v1.mjs';

const SHA40=/^[a-f0-9]{40}$/;
const SHA256=/^[a-f0-9]{64}$/;
const REPO=/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
const ID=n=>Number.isSafeInteger(n)&&n>0;
const error=code=>{throw Error(code);};
const markdown=s=>String(s).replace(/[\r\n<>]/g,' ').slice(0,120);

export function buildMathEvidenceCheck(observation,{repository,headSha}={}){
  if(!REPO.test(repository??'')||!SHA40.test(headSha??''))
    error('INVALID_DESTINATION');
  const o=observation;
  if(!o||o.schema!=='mathgraph.artin-environment-correlation.v1'||
    o.status!=='ENVIRONMENT_AND_REPLAY_CORRELATED'||
    o.subject?.repository!==repository||o.subject?.head_sha!==headSha||
    !ID(o.subject?.pr)||o.replay?.status!=='PINNED_REPLAY_OBSERVED'||
    !ID(o.replay.run_id)||o.replay.run_attempt!==1||
    !ID(o.replay.job_id)||!ID(o.replay.artifact_id)||
    !/^sha256:[a-f0-9]{64}$/.test(o.replay.artifact_digest??'')||
    !ID(o.environment_artifact_id)||o.environment_artifact_id===o.replay.artifact_id||
    !/^sha256:[a-f0-9]{64}$/.test(o.environment_artifact_digest??'')||
    o.environment?.status!=='ENVIRONMENT_MANIFEST_BYTES_PINNED'||
    !SHA256.test(o.environment.environment_sha256??'')||
    !SHA256.test(o.environment.manifest_sha256??'')||
    o.environment.resolved_dependency_count<1||
    !Number.isSafeInteger(o.environment.resolved_dependency_count)||
    !Array.isArray(o.environment.resolved_dependencies)||
    o.environment.resolved_dependencies.length!==o.environment.resolved_dependency_count||
    o.environment.mathlib_revision!=='8f9d9cff6bd728b17a24e163c9402775d9e6a365'||
    o.permission!=='ADVISORY_ONLY'||o.conclusion!=='neutral'||
    o.intent_verification!=='NOT_ESTABLISHED'||
    o.receipt_qualification!=='NOT_YET_CONTRACT_BOUND')
    error('UNQUALIFIED_MATH_EVIDENCE');

  const human=o.review?.status==='SOURCE_TO_FORMAL_REVIEWED';
  if(!human&&o.review?.status!=='UNKNOWN')error('UNQUALIFIED_HUMAN_REVIEW');
  if(human&&(!ID(o.review.review_id)||!ID(o.review.reviewer_id)||
    o.review.evidence_scope!=='EXPLICIT_SOURCE_AND_THEOREM_HASH_REVIEW'&&
    o.review.evidence_scope!=='INDEPENDENT_REVIEW_ATTESTATION_ONLY'))
    error('UNQUALIFIED_HUMAN_REVIEW');

  const generic={source:{repository,head_sha:headSha},
    status:'UNKNOWN',permission:'ADVISORY_ONLY',
    scope:'GITHUB_CHECK_RUN_OBSERVATION_ONLY',
    evidence:[{id:'pinned-lean-replay',status:'OBSERVED'},
      {id:'resolved-environment',status:'OBSERVED'}],
    results:[{id:'pinned-lean-replay',status:'OBSERVED'},
      {id:'resolved-environment',status:'OBSERVED'},
      {id:'source-to-formal-human-review',status:human?'OBSERVED':'UNKNOWN'}]};
  const basis=buildAdvisoryCheck(generic,{repository,sha:headSha});
  const title='Lean proof evidence observed · meaning '+(human?'review attested':'review pending');
  const lines=[
    '## MathGraph Check · Mathematical source assurance',
    '**Lean proof evidence is correlated with the original pinned statement and resolved environment.**',
    '**This is not a mathematical equivalence certificate, a proof of the informal claim, or merge approval.**',
    '| Obligation | Finding |',
    '| :-- | :-- |',
    '| Original source and formal statement | Pinned in collector |',
    '| Lean proof and classical axiom audit | Observed in authenticated run |',
    '| Full resolved Lake environment | Artifact bytes verified |',
    '| Independent human source-to-formal review | '+(human?'Review attested (not independently proven)':'UNKNOWN — review required')+' |',
    '| Formal-intent equivalence | NOT ESTABLISHED |',
    '',
    '**Theorem:** `'+ARTIN_PIN.theorem+'`',
    '**Source commit:** `'+ARTIN_PIN.commit+'`',
    '**Formal statement SHA-256:** `'+ARTIN_PIN.formalSha256+'`',
    '**Resolved environment SHA-256:** `'+o.environment.environment_sha256+'`',
    '**Replay attempt:** 1; **proof artifact:** '+o.replay.artifact_id+
      '; **environment artifact:** '+o.environment_artifact_id,
    '**Source repository:** `'+markdown(repository)+'` at `'+headSha+'`',
    '[Inspect the native replay](https://github.com/'+repository+'/actions/runs/'+o.replay.run_id+')',
    '',
    '**Authority:** ADVISORY_ONLY · Receipt qualification: NOT_YET_CONTRACT_BOUND.',
    'A new commit, rerun, withdrawn review, altered artifact or changed environment needs independent requalification.',
    'This check is always neutral and cannot grant merge authorization.'
  ];
  const body={...basis,name:'MathGraph Check / mathematical evidence (advisory)',
    external_id:'mathgraph-math-evidence-v1:'+repository+':'+headSha,
    output:{title,summary:lines.join('\n').slice(0,65000)}};
  return body;
}

/**
 * Publish only after a human operator has enabled checks:write for this exact
 * repository. The head is independently read from GitHub before posting.
 * Never accept a PR-authored token, destination, or trusted evidence record.
 */
export async function publishMathEvidenceCheck(observation,{
  repository,headSha,token,fetcher=fetch,dryRun=true,
}={}){
  const request=buildMathEvidenceCheck(observation,{repository,headSha});
  if(dryRun)return {mode:'PREVIEW',request};
  if(typeof token!=='string'||token.length<10||typeof fetcher!=='function')
    error('APP_INSTALLATION_TOKEN_REQUIRED');
  const headers={Accept:'application/vnd.github+json',
    'X-GitHub-Api-Version':'2022-11-28',
    Authorization:'Bearer '+token};
  const pr=observation.subject.pr;
  const p=await fetcher('https://api.github.com/repos/'+repository+'/pulls/'+pr,{
    method:'GET',redirect:'error',headers,signal:AbortSignal.timeout(15000)});
  if(!p?.ok)error('GITHUB_HEAD_READ_FAILED');
  const live=await p.json();
  if(live?.head?.sha!==headSha||live?.head?.repo?.full_name!==repository||
    live?.base?.repo?.full_name!==repository||live?.number!==pr)
    error('GITHUB_HEAD_MOVED');
  const r=await fetcher('https://api.github.com/repos/'+repository+'/check-runs',{
    method:'POST',redirect:'error',
    headers:{...headers,'Content-Type':'application/json'},
    body:JSON.stringify(request),signal:AbortSignal.timeout(15000)});
  if(!r?.ok)error('GITHUB_CHECK_PUBLISH_FAILED');
  const check=await r.json();
  if(!ID(check?.id)||check.head_sha!==headSha||
    check.name!==request.name||check.conclusion!=='neutral')
    error('GITHUB_CHECK_READBACK_UNVERIFIED');
  return {mode:'PUBLISHED',check_run_id:check.id,url:check.html_url??null};
}


/**
 * Production-boundary entry: always re-run the authenticated collector before
 * rendering or publishing. No externally supplied observation objects accepted.
 * Input must come from a trusted operator/installation handler, never a PR.
 */
export async function collectAndPublishMathEvidence(input,{publish=false}={}){
  if(!input||typeof input!=='object'||publish!==true&&publish!==false||
    typeof input.token!=='string'||input.token.length<10||
    !REPO.test(input.repository??'')||
    input.trusted?.repository!==input.repository||
    input.trusted?.pr!==input.pr||
    !SHA40.test(input.trusted?.headSha??''))
    error('INVALID_OPERATOR_TRUST_SCOPE');
  const observed=await collectMathSourceEvidenceWithEnvironment(input);
  if(observed.status!=='ENVIRONMENT_AND_REPLAY_CORRELATED')
    return {mode:'UNKNOWN',reason:observed.reason??'UNQUALIFIED_COLLECTOR_OBSERVATION',
      permission:'ADVISORY_ONLY',intent_verification:'NOT_ESTABLISHED'};
  return publishMathEvidenceCheck(observed,{
    repository:input.repository,headSha:input.trusted.headSha,
    token:input.token,fetcher:input.fetcher??fetch,dryRun:!publish,
  });
}
