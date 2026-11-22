import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {extractProjection,assessRefusalArm,assessRefusalExecution,observedOutcome} from './refusal.mjs';

const digest=s=>createHash('sha256').update(s).digest('hex');
const minimal='module\npublic import Tests.SuiteRunner.Meta\n-- Unicode byte offset: λ\n'+
 'inductive Backend where\n | lean\ninductive TestResult where\n | pass (stdout : String := "")\n'+
 '/-- Run a single test case against our parser (pure computation). -/\n'+
 'def runTestCore := ()\n'+
 'def runTest (tc : TestCase) : IO TestResult := do\n return .pass tc.yaml\n'+
 '/-- Summary statistics for a test run. -/\nstructure TestStats where\n';

test('projection retains exact source bytes and byte offsets, excluding the unrelated pure parser',()=>{
 const result=extractProjection(minimal),bytes=Buffer.from(minimal);
 for(const fragment of Object.values(result.fragments)){
  const exact=bytes.subarray(fragment.start_byte,fragment.end_byte);
  assert.equal(digest(exact),fragment.sha256);
  assert.ok(result.code.includes(exact.toString('utf8')));
 }
 assert.ok(!result.code.includes('def runTestCore'));
 assert.equal(result.sha256,digest(result.code));
});

test('ambiguous extraction and incomplete protocol shapes cannot produce a runnable projection',()=>{
 assert.throws(()=>extractProjection(minimal+'def runTest (tc : TestCase)'),/UNSUPPORTED_SOURCE_SHAPE/);
 assert.throws(()=>extractProjection(minimal.replace('return .pass tc.yaml','return Protocol.classify 1 ""')),/UNSUPPORTED_RESULT_PROTOCOL_SHAPE/);
 assert.throws(()=>extractProjection(minimal.replace('/-- Summary statistics for a test run. -/','')),/UNSUPPORTED_SOURCE_SHAPE/);
});

const source={files:{'Tests/SuiteRunner/Main.lean':{source_sha256:'source'}},projection:{sha256:'projection'}};
const fixture={id:'exit_2',expect_fail:true,behavior:'exit',exit_code:2,stdout:'',stderr:'',expected:'ERROR'};
const observation={id:'exit_2',complete:true,observation:{id:'exit_2',kind:'PASS',stdout:''},process:{exit_code:2}};
const arm=()=>({build_exit:0,source_hashes:{'Tests/SuiteRunner/Main.lean':'source'},projection_sha256:'projection',cases:[observation]});

test('completed original false-positive remains a discrepancy against the fixed refusal contract',()=>{
 const result=assessRefusalArm(arm(),source,[fixture]);
 assert.equal(result.complete,true);
 assert.equal(result.mismatches.length,1);
 assert.equal(result.observations[0].observed.outcome,'PASS');
 assert.equal(result.observations[0].expected.outcome,'ERROR');
});

test('missing native evidence and changed source identity cannot be promoted',()=>{
 const missing=assessRefusalArm({...arm(),cases:[]},source,[fixture]);
 assert.equal(missing.complete,false);
 assert.equal(missing.observations.length,0);
 const incomplete=assessRefusalArm({...arm(),cases:[{...observation,complete:false}]},source,[fixture]);
 assert.equal(incomplete.complete,false);
 const changed=assessRefusalArm({...arm(),projection_sha256:'different'},source,[fixture]);
 assert.equal(changed.complete,false);
 assert.equal(changed.reason,'SOURCE_BINDING_MISMATCH');
});

test('the observed timeout constructor and historical exact timeout reason stay distinct from other failures',()=>{
 assert.equal(observedOutcome({kind:'TIMEOUT'}),'TIMEOUT');
 assert.equal(observedOutcome({kind:'FAIL',reason:'timeout (possible infinite loop)'}),'TIMEOUT');
 assert.equal(observedOutcome({kind:'FAIL',reason:'a diagnostic mentioning timeout'}),'FAIL');
 assert.throws(()=>observedOutcome({kind:'new-constructor'}),/UNRECOGNIZED_NATIVE_RESULT/);
});

test('a post-observation apparatus failure withdraws an otherwise complete agreement',()=>{
 const successful={...arm(),cases:[{...observation,observation:{id:'exit_2',kind:'ERROR',reason:'backend error'}}]};
 const result=assessRefusalExecution({base:successful,head:successful,reason:'APPARATUS_EXECUTABLE_CHANGED'},
  {base:source,head:source},[fixture]);
 assert.equal(result.base.complete,true);
 assert.equal(result.head.complete,true);
 assert.equal(result.head.mismatches.length,0);
 assert.equal(result.status,'UNKNOWN');
 assert.equal(result.reason,'APPARATUS_EXECUTABLE_CHANGED');
});
