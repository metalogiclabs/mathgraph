import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,writeFile,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
const exec=promisify(execFile);
const sha=s=>createHash('sha256').update(s).digest('hex');

test('operator CLI preserves unavailable environment as an exact evidence receipt without overwriting it',async()=>{
 const dir=await mkdtemp(join(tmpdir(),'mathgraph-cli-contract-'));
 try{
  const src='import Init\ntheorem original (n : Nat) : n + 0 = n := by simp\n';
  const ref=join(dir,'Reference.lean'),cand=join(dir,'Candidate.lean'),out=join(dir,'report.json');
  await writeFile(ref,src);await writeFile(cand,src);
  const args=['integrations/mathgraph-check-github/generic-semanteq-cli-v1.mjs',
   '--reference',ref,'--candidate',cand,'--reference-sha',sha(src),
   '--project','/nonexistent-semanteq','--output',out];
  let first;
  try{await exec(process.execPath,args,{cwd:new URL('../..',import.meta.url).pathname});}
  catch(e){first=e;}
  assert.equal(first?.code,2);
  const report=JSON.parse(await readFile(out,'utf8'));
  assert.equal(report.execution_status,'ENVIRONMENT_UNAVAILABLE');
  assert.equal(report.evidence_warrant,'UNKNOWN');
  assert.equal(report.reference_sha256,sha(src));
  let second;
  try{await exec(process.execPath,args,{cwd:new URL('../..',import.meta.url).pathname});}
  catch(e){second=e;}
  assert.equal(second?.code,2);
  assert.equal(JSON.parse(await readFile(out,'utf8')).reference_sha256,sha(src));
 }finally{await rm(dir,{recursive:true,force:true});}
});

test('operator CLI joins optional consumer replay only under separate exact source authorization',async()=>{
 const dir=await mkdtemp(join(tmpdir(),'mathgraph-cli-consumer-'));
 try{
  const src='import Init\ntheorem original (n : Nat) : n + 0 = n := by simp\n';
  const consumer='import Candidate\ntheorem MathGraphConsumer.original_claim (n : Nat) : n + 0 = n := by\n  exact candidate n\n';
  const ref=join(dir,'Reference.lean'),cand=join(dir,'Candidate.lean'),con=join(dir,'Consumer.lean'),out=join(dir,'report.json');
  await writeFile(ref,src);await writeFile(cand,src);await writeFile(con,consumer);
  const args=['integrations/mathgraph-check-github/generic-semanteq-cli-v1.mjs',
   '--reference',ref,'--candidate',cand,'--reference-sha',sha(src),
   '--consumer',con,'--consumer-sha',sha(consumer),'--consumer-name','MathGraphConsumer.original_claim',
   '--project','/nonexistent-semanteq','--output',out];
  await assert.rejects(exec(process.execPath,args,{cwd:new URL('../..',import.meta.url).pathname}),{code:2});
  const report=JSON.parse(await readFile(out,'utf8'));
  assert.equal(report.same_run_correlation,'UNKNOWN');
  assert.equal(report.original_target_status,'UNKNOWN');
  assert.equal(report.consumer_replay.execution_status,'ENVIRONMENT_UNAVAILABLE');
  assert.equal(report.consumer_replay.consumer_sha256,sha(consumer));
  assert.equal(report.evidence_warrant,'UNKNOWN');
 }finally{await rm(dir,{recursive:true,force:true});}
});

test('proof fixture requires both an exact hash and a source path',async()=>{
 const dir=await mkdtemp(join(tmpdir(),'mathgraph-cli-proof-args-'));
 try{
  const src='import Init\ntheorem original (n : Nat) : n + 0 = n := by simp\n';
  const ref=join(dir,'Reference.lean'),cand=join(dir,'Candidate.lean'),proof=join(dir,'Proof.lean'),out=join(dir,'report.json');
  await writeFile(ref,src);await writeFile(cand,src);await writeFile(proof,src);
  const common=['integrations/mathgraph-check-github/generic-semanteq-cli-v1.mjs',
   '--reference',ref,'--candidate',cand,'--reference-sha',sha(src),'--project','/missing','--output',out];
  for(const incomplete of [['--proof-fixture',proof],['--proof-fixture-sha',sha(src)]]){
   await assert.rejects(exec(process.execPath,[...common,...incomplete],
    {cwd:new URL('../..',import.meta.url).pathname}),{code:2});
   await assert.rejects(readFile(out,'utf8'),{code:'ENOENT'});
  }
 }finally{await rm(dir,{recursive:true,force:true});}
});

test('proof fixture is a distinct advisory even without a native environment',async()=>{
 const dir=await mkdtemp(join(tmpdir(),'mathgraph-cli-proof-'));
 try{
  const src='import Init\ntheorem original (n : Nat) : n + 0 = n := by simp\n';
  const proof='import Init\ntheorem candidate_assumed (n : Nat) : n + 0 = n := by sorry\ntheorem original (n : Nat) : n + 0 = n := by exact candidate_assumed n\n';
  const ref=join(dir,'Reference.lean'),cand=join(dir,'Candidate.lean'),fixture=join(dir,'Proof.lean'),out=join(dir,'report.json');
  await writeFile(ref,src);await writeFile(cand,src);await writeFile(fixture,proof);
  const args=['integrations/mathgraph-check-github/generic-semanteq-cli-v1.mjs',
   '--reference',ref,'--candidate',cand,'--reference-sha',sha(src),
   '--proof-fixture',fixture,'--proof-fixture-sha',sha(proof),
   '--project','/nonexistent-semanteq','--output',out];
  await assert.rejects(exec(process.execPath,args,{cwd:new URL('../..',import.meta.url).pathname}),{code:2});
  const report=JSON.parse(await readFile(out,'utf8'));
  assert.equal(report.proof_fixture_audit.source_sha256,sha(proof));
  assert.equal(report.proof_fixture_audit.execution_status,'ENVIRONMENT_UNAVAILABLE');
  assert.equal(report.proof_fixture_audit.verdict,'UNKNOWN');
  assert.equal(report.proof_fixture_audit.proof_binding,'UNBOUND_ADVISORY');
  assert.equal(report.proof_same_run_correlation,'UNKNOWN');
  assert.equal(report.intent_fidelity,'UNKNOWN');
  assert.equal(report.evidence_warrant,'UNKNOWN');
 }finally{await rm(dir,{recursive:true,force:true});}
});

test('native CLI joins a genuine PASS or bypass FAIL without treating either as intent or warrant',{
 skip:!process.env.MATHGRAPH_SEMANTEQ_PROJECT
},async()=>{
 const dir=await mkdtemp(join(tmpdir(),'mathgraph-cli-proof-native-'));
 try{
  const reference='import Init\ntheorem trusted (n : Nat) : n + 0 = n := by simp\n';
  const candidate='import Init\ntheorem candidate (n : Nat) : n = n := by rfl\n';
  const dependent='import Init\ntheorem assumed (n : Nat) : n + 0 = n := by sorry\ntheorem goal (n : Nat) : n + 0 = n := by exact assumed n\n';
  const bypass='import Init\ntheorem assumed (n : Nat) : n + 0 = n := by sorry\ntheorem goal (n : Nat) : n + 0 = n := by simp\n';
  const ref=join(dir,'Reference.lean'),cand=join(dir,'Candidate.lean');
  await writeFile(ref,reference);await writeFile(cand,candidate);
  for(const [name,source,expected] of [['Dependent',dependent,'PASS'],['Bypass',bypass,'FAIL']]){
   const fixture=join(dir,`${name}.lean`),out=join(dir,`${name}.json`);
   await writeFile(fixture,source);
   const args=['integrations/mathgraph-check-github/generic-semanteq-cli-v1.mjs',
    '--reference',ref,'--candidate',cand,'--reference-sha',sha(reference),
    '--proof-fixture',fixture,'--proof-fixture-sha',sha(source),
    '--project',process.env.MATHGRAPH_SEMANTEQ_PROJECT,'--timeout-ms','90000','--output',out];
   await exec(process.execPath,args,{cwd:new URL('../..',import.meta.url).pathname,timeout:120000});
   const report=JSON.parse(await readFile(out,'utf8'));
   assert.equal(report.proof_fixture_audit.verdict,expected,name);
   assert.equal(report.proof_fixture_audit.execution_status,'EXECUTED');
   assert.equal(report.proof_same_run_correlation,'MATCHING_LOCAL_INVOCATION_AND_PINNED_ENVIRONMENT');
   assert.equal(report.proof_fixture_audit.proof_binding,'UNBOUND_ADVISORY');
   assert.equal(report.intent_fidelity,'UNKNOWN');
   assert.equal(report.evidence_warrant,'UNKNOWN');
  }
 }finally{await rm(dir,{recursive:true,force:true});}
});
