#!/usr/bin/env node
// Source-bound research replay against a real third-party PR.
// Host-named finite evidence; not independent owner-authorized release.
import assert from 'node:assert/strict'
import {createHash} from 'node:crypto'
import {readFileSync,writeFileSync} from 'node:fs'
import {auditIntent,digestContract,renderIntentReport,SCHEMA}
  from '../../integrations/mathgraph-check-github/intent-contract-v1.mjs'

const directory=process.argv[2]
if(!directory)throw Error('USAGE: node classify.mjs <evidence-dir>')
const load=n=>JSON.parse(readFileSync(directory+'/'+n,'utf8'))
const BASE='528ef30d6ded4bd9f2c3521b670eb2b29d503c5c'
const HEAD='9a1c4bd1a5c76272fd66a7a75c3aa37c54fd129d'
const ORACLE_BLOB='7ee58d525b6078d6e78cf57ddf85c71345ae58a4'
const sha=s=>createHash('sha256').update(s).digest('hex')
const before=load('source-before.json'),after=load('source-after.json')
const base=load('base.json'),head=load('head.json')
assert.equal(before.prHeadSha,HEAD)
assert.equal(after.prHeadSha,HEAD)
assert.equal(before.prBaseSha,BASE)
assert.equal(after.prBaseSha,BASE)
assert.equal(before.issueBodySha256,after.issueBodySha256,'ISSUE_EDITED_DURING_TEST')
assert.equal(before.prDescriptionSha256,after.prDescriptionSha256,'PR_EDITED_DURING_TEST')
assert.equal(before.issueUpdated,after.issueUpdated,'ISSUE_SOURCE_DRIFT')
assert.equal(before.prState,'open')
assert.equal(after.prState,'open')
assert.equal(before.ownerAuthority,'NOT_AUTHENTICATED')
assert.equal(base.phase,'BASE')
assert.equal(head.phase,'HEAD')
assert.equal(base.total,455)
assert.equal(head.total,455)
assert.equal(base.casesSha256,head.casesSha256,'DIFFERENT_ORACLE_INPUTS')
for(const evidence of [base,head]){
 assert.equal(evidence.sourceRepository,'eemeli/yaml')
 assert.equal(evidence.issue,733)
 assert.equal(evidence.pr,738)
 assert.equal(evidence.total,evidence.pass+evidence.fail)
 assert.equal(evidence.perGroup['reporter-exact'].total,5)
 assert.equal(evidence.perGroup['positive-control'].total,2)
 assert.equal(evidence.perGroup['pr733-mapping-matrix'].total,448)
 assert.equal(evidence.perGroup['positive-control'].fail,0,'POSITIVE_CONTROL_FAILED')
 assert.equal(evidence.fail,evidence.failures.length)
}
// The publicly reported bug MUST be red at the original base, or this
// replay does not establish the claimed repair-to-pr-head contrast.
assert.ok(base.perGroup['reporter-exact'].fail>0,'BASE_REPORTER_BUG_NOT_REPRODUCED')
const scope='Reporter issue #733: mapping block scalars with leading spaces round-trip for custom indent (finite pinned inputs only).'
function contractAt(sourceSha){
 return {schema:SCHEMA,
  subject:{repository:'eemeli/yaml',pr:738,base_sha:BASE,head_sha:sourceSha},
  claims:[{id:'reporter_issue733',statement:scope,requires:['reporter_exact','matrix','positive_control']}],
  probes:['reporter_exact','matrix','positive_control'].map(id=>({
   id,input_sha256:base.casesSha256,
   oracle_sha256:sha(readFileSync(new URL('./oracle.mjs',import.meta.url))),
   verifier_sha:ORACLE_BLOB
  }))}
}
const groups={reporter_exact:'reporter-exact',
 matrix:'pr733-mapping-matrix',positive_control:'positive-control'}
function run(evidence,sourceSha){
 const contract=contractAt(sourceSha),contractSha=digestContract(contract)
 const receipts=Object.entries(groups).map(([id,group])=>{
  const summary=evidence.perGroup[group]
  const failures=evidence.failures.filter(f=>f.group===group)
  return {id:'research-'+evidence.phase.toLowerCase()+'-'+id,probe_id:id,
   subject_sha:sourceSha,contract_sha256:contractSha,
   input_sha256:evidence.casesSha256,oracle_sha256:contract.probes[0].oracle_sha256,
   verifier_sha:ORACLE_BLOB,
   result:summary.fail?'COUNTEREXAMPLE':'PASS',
   exit_code:summary.fail?1:0,
   log_sha256:sha(JSON.stringify({phase:evidence.phase,group,summary,failures})),
   witness_sha256:summary.fail?sha(JSON.stringify(failures)):null}
 })
 // These allowlists are supplied by this research runner, not the third-party
 // PR packet. They do NOT authenticate external owner intent, oracle authorship
 // independence, reviewer consent, or permission to merge/release.
 const researchRunnerAuthority={
  allowedRepositories:['eemeli/yaml'],
  expectedHeadSha:sourceSha,
  expectedContractSha256:contractSha,
  authenticatedReceiptIds:receipts.map(r=>r.id),
  qualifiedVerifierShas:[ORACLE_BLOB],
  qualifiedOracleShas:[contract.probes[0].oracle_sha256]
 }
 const result=auditIntent(contract,receipts,researchRunnerAuthority)
 return {contract,receipts,researchRunnerAuthority,result}
}
const a=run(base,BASE),b=run(head,HEAD)
assert.equal(a.result.status,'BLOCKED')
assert.ok(['OBSERVED','BLOCKED'].includes(b.result.status))
assert.equal(b.result.permission,'ADVISORY_ONLY')
assert.equal(b.result.intent_verification,'NOT_ESTABLISHED')
assert.equal(b.result.checked_scope,'DECLARED_PINNED_PROBES_ONLY')
// The controls establish the binder actually refuses a changed statement,
// a forged oracle hash, stale subject evidence and missing trusted-host input.
const statementTamper=structuredClone(b.contract)
statementTamper.claims[0].statement='All YAML strings in all contexts preserve roundtrips'
assert.equal(auditIntent(statementTamper,b.receipts,b.researchRunnerAuthority).status,'UNKNOWN')
const forged=structuredClone(b.receipts)
forged[0].oracle_sha256='f'.repeat(64)
assert.equal(auditIntent(b.contract,forged,b.researchRunnerAuthority).status,'UNKNOWN')
const stale=structuredClone(b.receipts)
stale[0].subject_sha=BASE
assert.equal(auditIntent(b.contract,stale,b.researchRunnerAuthority).status,'UNKNOWN')
assert.equal(auditIntent(b.contract,b.receipts,{...b.researchRunnerAuthority,
 authenticatedReceiptIds:[]}).status,'UNKNOWN')
const headVerdict=b.result.status==='BLOCKED'?'COUNTEREXAMPLE_IN_PINNED_SCOPE':
 'BOUNDED_PASS_ON_PINNED_SCOPE'
// Conventional reviewer with identical inputs/authorities and *same oracle*
// reaches the same finite-scope result. No comparative superiority is claimed.
const conventional=head.fail>0?'COUNTEREXAMPLE_IN_PINNED_SCOPE':'BOUNDED_PASS_ON_PINNED_SCOPE'
assert.equal(conventional,headVerdict)
const outcome={
 schema:'mathgraph-check-real-pr-comparative-report-v0',
 observedSource:{repository:'eemeli/yaml',issue:733,pr:738,
  issueBodySha256:after.issueBodySha256,prDescriptionSha256:after.prDescriptionSha256,
  sourceReadbackBefore:before.observedAt,sourceReadbackAfter:after.observedAt,
  baseSha:BASE,headSha:HEAD},
 issueExpectationAuthority:'REPORTER_AUTHORED_ONLY_OWNER_APPROVAL_NOT_ESTABLISHED',
 oracle:{gitBlob:ORACLE_BLOB,casesSha256:head.casesSha256,
  exactCaseCount:head.total,hasSeparateIssue692OutOfScope:true},
 sourceNativeResults:{
  base:{pass:base.pass,fail:base.fail,perGroup:base.perGroup},
  head:{pass:head.pass,fail:head.fail,perGroup:head.perGroup},
  headFailures:head.failures.slice(0,30),headFailureCount:head.fail,
  baseFailureCount:base.fail,observedRepairs:base.fail-head.fail,
  outsideScopeIssue692:{base:base.outsideScopeIssue692,head:head.outsideScopeIssue692}
 },
 mathgraph:{status:b.result.status,reason:b.result.reason,
  checkedScope:b.result.checked_scope,permission:b.result.permission,
  intentVerification:b.result.intent_verification,verdict:headVerdict,
  authority:'RESEARCH_RUNNER_SOURCE_PINS_NOT_INDEPENDENT_OWNER_AUTHORITY'},
 conventionalEqualInformationBaseline:{verdict:conventional,
  sameInputs:true,sameVerifier:true,sameOracle:true,sameBudgetInstruments:true,
  humanReviewerMeasured:false},
 proofOfSuperiority:'NOT_ESTABLISHED',
 transition:{base:a.result.status,head:b.result.status,
  oracleAndClaimStatementsPinned:true,
  futureSourceHeadRequiresFreshRequalification:true,
  freshnessAfterFinalSourceRead:'NOT_CHECKED',revocation:'NOT_CHECKED'},
 negativeControls:{changedStatement:'UNKNOWN',forgedOracle:'UNKNOWN',
  staleSourceReceipt:'UNKNOWN',missingRunnerQualifiedReceipt:'UNKNOWN'},
 releaseAuthority:'NONE',action:'ADVISORY_ONLY'
}
writeFileSync(directory+'/audit.json',JSON.stringify(outcome,null,2)+'\n')
writeFileSync(directory+'/report.html',renderIntentReport(b.result))
process.stdout.write('MATHGRAPH_REAL_YAML733_AUDIT='+headVerdict+
  ';base_fail='+base.fail+';head_fail='+head.fail+
  ';total='+head.total+';baseline_tie=true;owner_intent=UNKNOWN;release=ADVISORY_ONLY\n')
