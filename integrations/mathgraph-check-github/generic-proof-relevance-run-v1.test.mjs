import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdtemp,readFile,rm,writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {parseNativeProofVerdict,runGenericProofRelevance} from './generic-proof-relevance-run-v1.mjs';

const hash=source=>createHash('sha256').update(source).digest('hex');
const dependent='import Init\ntheorem candidate_assumed (n : Nat) : n + 0 = n := by sorry\ntheorem original (n : Nat) : n + 0 = n := by exact candidate_assumed n\n';
const bypass='import Init\ntheorem candidate_assumed (n : Nat) : n + 0 = n := by sorry\ntheorem original (n : Nat) : n + 0 = n := by simp\n';
const deadTouch='import Init\ntheorem candidate_assumed (n : Nat) : n + 0 = n := by sorry\ntheorem original (n : Nat) : n + 0 = n := by\n  have unused := candidate_assumed n\n  simp\n';

test('fixture source cannot enter native evaluation when its trusted SHA mismatches',async()=>{
 const dir=await mkdtemp(join(tmpdir(),'mathgraph-proof-pin-'));
 try{
  const source=join(dir,'Proof.lean');await writeFile(source,dependent);
  const report=await runGenericProofRelevance({source,expectedSha:'0'.repeat(64),projectDir:'/missing'});
  assert.equal(report.execution_status,'SOURCE_HASH_MISMATCH');
  assert.equal(report.source_sha256,hash(dependent));
  assert.equal(report.verdict,'UNKNOWN');
  assert.equal(report.proof_binding,'UNBOUND_ADVISORY');
  assert.equal(report.native_exit_code,null);
  assert.equal(report.command,null);
 }finally{await rm(dir,{recursive:true,force:true});}
});

test('pinned source with missing native tool has explicit unavailable provenance',async()=>{
 const dir=await mkdtemp(join(tmpdir(),'mathgraph-proof-env-'));
 try{
  const source=join(dir,'Proof.lean');await writeFile(source,dependent);
  const report=await runGenericProofRelevance({source,expectedSha:hash(dependent),projectDir:'/missing'});
  assert.equal(report.execution_status,'ENVIRONMENT_UNAVAILABLE');
  assert.match(report.reason,/NATIVE_TOOL_NOT_AVAILABLE/);
  assert.equal(report.verdict,'UNKNOWN');
  assert.equal(report.source_sha256,hash(dependent));
  assert.equal(report.proof_binding,'UNBOUND_ADVISORY');
 }finally{await rm(dir,{recursive:true,force:true});}
});

test('native checker raw output must be one exact, well-formed verdict for the staged file',()=>{
 const source='/tmp/mathgraph-private-fixture/Proof.lean';
 const pass=JSON.stringify({ante:'candidate_assumed',goal:'original',file:source,verdict:'PASS',flags:0,flagDetails:[],reasons:[]});
 const fail=JSON.stringify({ante:'candidate_assumed',goal:'original',file:source,verdict:'FAIL',flags:0,flagDetails:[],reasons:['not used']});
 assert.equal(parseNativeProofVerdict(pass,source).verdict,'PASS');
 assert.equal(parseNativeProofVerdict(fail,source).verdict,'FAIL');
 assert.equal(parseNativeProofVerdict(pass+'\n'+fail,source),null);
 assert.equal(parseNativeProofVerdict(pass,'/another/source.lean'),null);
 assert.equal(parseNativeProofVerdict('{"verdict":"PASS"}',source),null);
 assert.equal(parseNativeProofVerdict(JSON.stringify({ante:'a',goal:'b',file:source,verdict:'PASS',flags:1}),source),null);
 assert.equal(parseNativeProofVerdict('not json',source),null);
});

test('pinned native ProofChecker distinguishes dependent proof, library bypass and dead touch',{
 skip:!process.env.MATHGRAPH_SEMANTEQ_PROJECT
},async()=>{
 const dir=await mkdtemp(join(tmpdir(),'mathgraph-proof-native-'));
 try{
  for(const [name,sourceText,verdict] of [
   ['Dependent',dependent,'PASS'],['Bypass',bypass,'FAIL'],['DeadTouch',deadTouch,'FAIL']
  ]){
   const source=join(dir,`${name}.lean`);await writeFile(source,sourceText);
   const report=await runGenericProofRelevance({source,expectedSha:hash(await readFile(source)),
    projectDir:process.env.MATHGRAPH_SEMANTEQ_PROJECT,timeoutMs:90000});
   assert.equal(report.execution_status,'EXECUTED',`${name}: ${report.reason??report.stderr}`);
   assert.equal(report.native_exit_code,0,name);
   assert.equal(report.verdict,verdict,`${name}: ${report.stdout}`);
   assert.equal(report.proof_binding,'UNBOUND_ADVISORY');
   assert.ok(report.tool_git&&report.mathlib_git&&report.semanteq_executable_sha256);
   assert.equal(report.source_sha256,hash(sourceText));
   assert.ok(report.stdout.includes('"verdict"'));
  }
 }finally{await rm(dir,{recursive:true,force:true});}
});
