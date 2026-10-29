#!/usr/bin/env node
// Separate V1 exploratory audit classification, NEVER retroactively label a
// source-inspected post-V0 experiment "blinded holdout".
import assert from 'node:assert/strict'
import {readFileSync,writeFileSync} from 'node:fs'
const dir=process.argv[2]
if(!dir)throw Error('USAGE edge-classify.mjs <artifact-dir>')
const get=x=>JSON.parse(readFileSync(dir+'/'+x,'utf8'))
const base=get('edge-base.json'),head=get('edge-head.json')
const v0=get('audit.json')
const before=get('source-before.json'),after=get('source-after.json')
assert.equal(base.phase,'BASE');assert.equal(head.phase,'HEAD')
assert.equal(base.total,168);assert.equal(head.total,168)
assert.equal(base.casesSha256,head.casesSha256)
assert.equal(before.prHeadSha,after.prHeadSha)
assert.equal(before.prBaseSha,after.prBaseSha)
assert.equal(before.issueBodySha256,after.issueBodySha256)
assert.equal(before.prDescriptionSha256,after.prDescriptionSha256)
assert.equal(v0.sourceNativeResults.head.pass,455)
assert.equal(v0.sourceNativeResults.head.fail,0)
assert.equal(v0.sourceNativeResults.base.fail,389)
assert.equal(base.byWidth['single-digit-control'].total,72)
assert.equal(head.byWidth['single-digit-control'].total,72)
assert.equal(base.byWidth['multi-digit-hypothesis'].total,96)
assert.equal(head.byWidth['multi-digit-hypothesis'].total,96)
const multi=head.counterexamples.filter(x=>x.label==='multi-digit-hypothesis')
const invalid=multi.filter(x=>['UNPARSEABLE_SUCCESSFUL_STRINGIFY','VALUE_MISMATCH'].includes(x.result))
const rejected=multi.filter(x=>x.result==='OPTION_REJECTED_OR_STRINGIFY_ERROR')
const result=invalid.length?'BOUNDED_INVALID_YAML_OR_LOST_VALUE_FOR_10PLUS_OPTION':
 rejected.length?'UNKNOWN_DECLARED_OPTION_SUPPORT_OR_STRINGIFY_ERROR':
 'BOUNDED_PASS_168_EDGE_COHORT'
const conventional=result // same inputs/oracle; not human measured
const out={
 schema:'mathgraph-check-real-yaml733-v1-edge-report',
 source:{repo:'eemeli/yaml',pr:738,issue:733,head:after.prHeadSha,base:after.prBaseSha,
 issueBodySha256:after.issueBodySha256,readbackSame:true},
 v0QualifyingResult:'HEAD_455_OF_455_NO_FAIL_MUST_REMAIN_SEPARATE',
 v1Cohort:{inputSha256:head.casesSha256,head:head.byWidth,base:base.byWidth,
 headInvalidOutput:head.invalidOutput,headOptionRejected:head.optionRejected,
 headCounterexampleCount:head.counterexamples.length,
 firstInvalid:invalid[0]??null,
 sampledFailures:head.counterexamples.slice(0,20)},
 reference:'YAML 1.2.2 §8.1.1.1: indicator production 1-9 only',
 sourceAPIOptionType:'YAML ToStringOptions.indent?: number; no upper bound in option documentation',
 classification:result,
 scope:'NEW_EXPLORATORY_WIDTH_7_TO_16_ONLY_NOT_BLINDED',
 baseline:{sameInformation:true,sameOracle:true,verdict:conventional,humanMeasured:false},
 intentOwnerAuth:'UNKNOWN',
 permission:'ADVISORY_ONLY',release:'NONE',
 superiority:'NOT_ESTABLISHED',
 next:['MAINTAINER_CONFIRM_OPTION_RANGE','DO_NOT_ASCRIBE_ISSUE_692_TO_THIS_PR',
  'FRESH_SOURCE_QUALIFICATION_ON_PR_HEAD_CHANGE']
}
writeFileSync(dir+'/edge-audit.json',JSON.stringify(out,null,2)+'\n')
process.stdout.write('MATHGRAPH_YAML733_V1_EDGE='+result+
 ';source_head='+after.prHeadSha+
 ';head_multi_invalid='+invalid.length+
 ';head_multi_option_rejected='+rejected.length+
 ';total='+head.total+
 ';baseline_tie=true;owner_auth=UNKNOWN;permission=ADVISORY_ONLY\n')
