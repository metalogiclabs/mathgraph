import {createHash} from 'node:crypto';
import {BRAHE_SOURCE_V1} from './brahe-endpoint-v1.mjs';

const NS='events::detection::tests::';
const NEGATIVE=[
  'test_sscan_rejects_decreasing_detector_at_increasing_endpoint',
  'test_sscan_rejects_increasing_detector_at_decreasing_endpoint',
  'test_dscan_rejects_decreasing_detector_at_increasing_endpoint',
  'test_dscan_rejects_increasing_detector_at_decreasing_endpoint'
];
const NEGATIVE_ASSERTIONS=[
  'assertion failed: !static_endpoint_detected(-2.0, 0.0, EventDirection::Decreasing)',
  'assertion failed: !static_endpoint_detected(2.0, 0.0, EventDirection::Increasing)',
  'assertion failed: !dynamic_endpoint_detected(-2.0, 0.0, EventDirection::Decreasing)',
  'assertion failed: !dynamic_endpoint_detected(2.0, 0.0, EventDirection::Increasing)'
];
const POSITIVE=[
  'test_sscan_accepts_direction_matching_endpoint',
  'test_sscan_accepts_any_direction_at_endpoint',
  'test_dscan_accepts_direction_matching_endpoint',
  'test_dscan_accepts_any_direction_at_endpoint'
];
const LEGACY=[
  'test_bisection_search_time_event',
  'test_scan_for_event',
  'test_scan_for_event_backward',
  'test_step_reduction_factor_is_used',
  'test_bracket_termination',
  'test_event_near_bracket_boundary',
  'test_dscan_value_event_position_crossing',
  'test_dscan_value_event_no_crossing',
  'test_dscan_value_event_increasing_direction'
];
const SHA256=/^[a-f0-9]{64}$/;
const SHA=/^[a-f0-9]{40}$/;
const RUN_URL=/^https:\/\/github\.com\/metalogiclabs\/mathgraph\/actions\/runs\/[1-9]\d*$/;
const SETUP_FAILURE=/could not compile|failed to download|linking with .*failed/i;

export function parseBraheNativeV1({exitCode,stdout,stderr,mode}={}) {
  const text=String(stdout??'')+'\n'+String(stderr??'');
  const empty={exitCode,testCount:0,regressionCount:0};
  if (!Number.isSafeInteger(exitCode)||!['base','head'].includes(mode))
    return {...empty,reason:'INVALID_INVOCATION'};
  // Cargo prints `error: test failed, to rerun pass ...` even when the
  // expected negative tests executed. All other compiler/Cargo errors are
  // still setup failures, never evidence of a failed regression assertion.
  const unexpectedError=text.split('\n').some(line=>
    /^error(?:\[[A-Z]\d+\])?:/i.test(line.trim()) &&
    !/^error: test failed, to rerun pass\b/i.test(line.trim()));
  if (SETUP_FAILURE.test(text)||unexpectedError) return {...empty,reason:'SETUP_FAILED'};
  if (/^running 0 tests?$/m.test(text)) return {...empty,reason:'ZERO_TESTS'};
  if (!/^running 17 tests$/m.test(text)) return {...empty,reason:'UNEXPECTED_FAILURE'};

  const matches=[...text.matchAll(/^test (events::detection::tests::[A-Za-z0-9_]+) \.\.\. (ok|FAILED)$/gm)];
  const observed=new Map(matches.map(m=>[m[1].slice(NS.length),m[2]]));
  if (matches.length!==17||observed.size!==17||
      [...NEGATIVE,...POSITIVE,...LEGACY].some(name=>!observed.has(name)))
    return {...empty,reason:'UNEXPECTED_FAILURE'};
  const fails=[...observed].filter(([,outcome])=>outcome==='FAILED').map(([name])=>name);
  const count={...empty,testCount:17,regressionCount:fails.length};
  const summaryHead=/test result: ok\. 17 passed; 0 failed;/.test(text);
  const summaryBase=/test result: FAILED\. 13 passed; 4 failed;/.test(text);
  const knownAssertionFailures=NEGATIVE.every((name,index)=>
    text.includes(`thread '${NS}${name}'`) && text.includes(NEGATIVE_ASSERTIONS[index]));
  if (mode==='base'&&exitCode!==0&&summaryBase&&fails.length===4&&
      NEGATIVE.every(name=>observed.get(name)==='FAILED')&&
      POSITIVE.every(name=>observed.get(name)==='ok')&&knownAssertionFailures)
    return {...count,reason:'EXPECTED_REGRESSION'};
  if (mode==='head'&&exitCode===0&&summaryHead&&fails.length===0)
    return {...count,reason:'PASSED'};
  return {...count,reason:'UNEXPECTED_FAILURE'};
}

export function buildBraheRunReceiptV1({mode,sourceSha,exitCode,stdout,stderr}={}) {
  return {
    ...parseBraheNativeV1({mode,exitCode,stdout,stderr}),
    sourceSha,
    logSha256:createHash('sha256').update(String(stdout??'')+'\n'+String(stderr??'')).digest('hex')
  };
}

export function combineBraheReceiptsV1({base,head,rustc,cargoLockSha256,workflowRunUrl,basePatchedBlobSha}={}) {
  const source={...BRAHE_SOURCE_V1,basePatchedBlobSha};
  const receipt={source,base,head,toolchain:{rustc,cargoLockSha256},runner:{workflowRunUrl}};
  const valid=base?.sourceSha===source.baseSha&&head?.sourceSha===source.headSha&&
    base?.reason==='EXPECTED_REGRESSION'&&base?.exitCode!==0&&base?.testCount===17&&base?.regressionCount===4&&
    head?.reason==='PASSED'&&head?.exitCode===0&&head?.testCount===17&&head?.regressionCount===0&&
    SHA256.test(base?.logSha256??'')&&SHA256.test(head?.logSha256??'')&&
    typeof rustc==='string'&&/^rustc \d/.test(rustc)&&
    SHA256.test(cargoLockSha256??'')&&SHA.test(basePatchedBlobSha??'')&&RUN_URL.test(workflowRunUrl??'');
  return {receipt,verdict:{
    schema:'mathgraph.brahe-endpoint-retrospective.v1',
    status:valid?'CANDIDATE_BOUNDED':'UNKNOWN',authority:'ADVISORY_ONLY',
    scope:'Brahe #608: exactly 17 events::detection unit tests, 4 wrong-direction endpoint negatives; transplanted head tests on pinned buggy base',
    source,
    evidence:valid?{base,head,toolchain:receipt.toolchain,runner:receipt.runner}:null,
    unknowns:['REQUIREMENT_AUTHOR_INTENT_NOT_INDEPENDENTLY_AUTHENTICATED','RECEIPT_AUTHENTICITY_NOT_CHECKED','COMPARATIVE_REVIEW_ADVANTAGE_UNKNOWN','EXTERNAL_CHECK_USE_UNKNOWN',...(valid?[]:['EVIDENCE_INCOMPLETE_OR_MISMATCHED'])]
  }};
}
