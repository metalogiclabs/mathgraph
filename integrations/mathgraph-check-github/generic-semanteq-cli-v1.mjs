#!/usr/bin/env node
// An explicit local-operator command, not a GitHub webhook handler.
import {readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {runGenericSemantEq} from './generic-semanteq-run-v1.mjs';
import {runGenericLeanConsumer} from './generic-lean-consumer-run-v1.mjs';
import {runGenericProofRelevance} from './generic-proof-relevance-run-v1.mjs';

function argumentsMap(args){
 const accepted=new Set(['--reference','--candidate','--reference-sha','--project','--output','--timeout-ms',
  '--consumer','--consumer-sha','--consumer-name','--proof-fixture','--proof-fixture-sha']);
 const values={};
 if(args.length%2!==0)throw Error('EXPECTED_KEY_VALUE_ARGUMENTS');
 for(let i=0;i<args.length;i+=2){
  if(!accepted.has(args[i])||Object.hasOwn(values,args[i])||!args[i+1])throw Error('INVALID_OR_DUPLICATE_ARGUMENT');
  values[args[i]]=args[i+1];
 }
 for(const key of ['--reference','--candidate','--reference-sha','--project','--output'])
  if(!values[key])throw Error(`MISSING_${key}`);
 return values;
}

async function main(){
 const options=argumentsMap(process.argv.slice(2));
 const referencePath=resolve(options['--reference']);
 const candidatePath=resolve(options['--candidate']);
 const reportPath=resolve(options['--output']);
 if([referencePath,candidatePath].includes(reportPath))throw Error('OUTPUT_MAY_NOT_REPLACE_SOURCE');
 const [referenceSource,candidateSource]=await Promise.all([readFile(referencePath,'utf8'),readFile(candidatePath,'utf8')]);
 const consumerArgs=['--consumer','--consumer-sha','--consumer-name'];
 if(consumerArgs.some(key=>options[key])&&!consumerArgs.every(key=>options[key]))throw Error('INCOMPLETE_CONSUMER_TRUST_ANCHOR');
 if(options['--consumer']&&resolve(options['--consumer'])===reportPath)throw Error('OUTPUT_MAY_NOT_REPLACE_CONSUMER');
 const proofArgs=['--proof-fixture','--proof-fixture-sha'];
 if(proofArgs.some(key=>options[key])&&!proofArgs.every(key=>options[key]))throw Error('INCOMPLETE_PROOF_FIXTURE_TRUST_ANCHOR');
 if(options['--proof-fixture']&&resolve(options['--proof-fixture'])===reportPath)throw Error('OUTPUT_MAY_NOT_REPLACE_PROOF_FIXTURE');
 const timeoutMs=options['--timeout-ms']?Number(options['--timeout-ms']):60000;
 const reference={path:referencePath,source:referenceSource};
 const candidate={path:candidatePath,source:candidateSource};
 const optionsForNative={reference,candidate,
  expectedReferenceSha:options['--reference-sha'],
  projectDir:resolve(options['--project']),timeoutMs};
 let report=await runGenericSemantEq(optionsForNative);
 if(options['--consumer']){
  const consumerSource=await readFile(resolve(options['--consumer']),'utf8');
  const replay=await runGenericLeanConsumer({...optionsForNative,consumerSource,
   expectedConsumerSha:options['--consumer-sha'],consumerName:options['--consumer-name']});
  const sameRun=report.execution_status==='EXECUTED'&&replay.execution_status==='EXECUTED'&&
   report.reference_sha256===replay.reference_sha256&&report.candidate_sha256===replay.candidate_sha256&&
   report.tool_git===replay.tool_git&&report.mathlib_git===replay.mathlib_git&&
   report.semanteq_executable_sha256===replay.semanteq_executable_sha256&&
   report.lake_manifest_sha256===replay.lake_manifest_sha256&&report.lean_toolchain_sha256===replay.lean_toolchain_sha256;
  report={...report,consumer_replay:{...replay,raw_consumer_source:consumerSource},
   same_run_correlation:sameRun?'MATCHING_LOCAL_INVOCATION_AND_PINNED_ENVIRONMENT':'UNKNOWN',
   candidate_source_build:sameRun?replay.candidate_source_build:'NOT_RUN',
   original_target_status:sameRun?replay.original_target_status:'UNKNOWN',
   intent_fidelity:'UNKNOWN',evidence_warrant:'UNKNOWN'};
 }
 if(options['--proof-fixture']){
  const audit=await runGenericProofRelevance({source:options['--proof-fixture'],
   expectedSha:options['--proof-fixture-sha'],projectDir:optionsForNative.projectDir,timeoutMs});
  const matching=report.execution_status==='EXECUTED'&&audit.execution_status==='EXECUTED'&&
   report.tool_git===audit.tool_git&&report.mathlib_git===audit.mathlib_git&&
   report.semanteq_executable_sha256===audit.semanteq_executable_sha256&&
   report.lake_manifest_sha256===audit.lake_manifest_sha256&&
   report.lean_toolchain_sha256===audit.lean_toolchain_sha256&&
   report.lean_version===audit.lean_version&&report.lake_version===audit.lake_version;
  report={...report,proof_fixture_audit:audit,
   proof_same_run_correlation:matching?'MATCHING_LOCAL_INVOCATION_AND_PINNED_ENVIRONMENT':'UNKNOWN',
   // Even a native PASS says nothing about whether this *unbound* fixture
   // corresponds to the current reference/candidate or its source intent.
   intent_fidelity:'UNKNOWN',evidence_warrant:'UNKNOWN'};
 }
 const raw=JSON.stringify(report,null,2)+'\n';
 await writeFile(reportPath,raw,{flag:'wx'});
 console.log(JSON.stringify({case_id:report.case_id,execution_status:report.execution_status,
  formal_statement_relation:report.formal_statement_relation,
  report_sha256:createHash('sha256').update(raw).digest('hex'),report_path:reportPath}));
 if(report.execution_status!=='EXECUTED'||
  (options['--consumer']&&report.consumer_replay.execution_status!=='EXECUTED')||
  (options['--proof-fixture']&&report.proof_fixture_audit.execution_status!=='EXECUTED'))process.exitCode=2;
}
main().catch(error=>{console.error(`GENERIC_SEMANTEQ_CLI_ERROR: ${error.message}`);process.exitCode=2;});
