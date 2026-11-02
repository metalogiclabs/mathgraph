import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdtemp,rm,writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {parseTypeBindingMarker,runGenericProofTypeBinding} from './generic-proof-type-binding-run-v1.mjs';

const sha=s=>createHash('sha256').update(s).digest('hex');
const reference={path:'Original.lean',source:'import Init\ntheorem shared_target (n : Nat) : n + 0 = n := by simp\n'};
const candidate={path:'Candidate.lean',source:'import Init\ntheorem shared_target (n : Nat) : n + 0 = n := by simp\n'};
const goal='theorem proof_goal (n : Nat) : n + 0 = n := by exact assumed_candidate n\n';
const faithful='import Init\ntheorem assumed_candidate (n : Nat) : n + 0 = n := by sorry\n'+goal;
const strengthened='import Init\ntheorem assumed_candidate (n : Nat) (h : n + 0 = n) : n + 0 = n := by sorry\ntheorem proof_goal (n : Nat) : n + 0 = n := by exact assumed_candidate n (by simp)\n';
const weakGoal='import Init\ntheorem assumed_candidate (n : Nat) : n + 0 = n := by sorry\ntheorem proof_goal (n : Nat) : True := by trivial\n';
const names={reference:'shared_target',candidate:'shared_target',assumption:'assumed_candidate',goal:'proof_goal'};
const common={reference,candidate,expectedReferenceSha:sha(reference.source),names};

test('stale fixture bytes fail before inspecting or executing the native environment',async()=>{
 const dir=await mkdtemp(join(tmpdir(),'mathgraph-binding-stale-'));
 try{
  const fixturePath=join(dir,'Proof.lean');await writeFile(fixturePath,faithful);
  const report=await runGenericProofTypeBinding({...common,fixturePath,expectedFixtureSha:'0'.repeat(64),projectDir:'/missing'});
  assert.equal(report.execution_status,'SOURCE_HASH_MISMATCH');
  assert.equal(report.binding_status,'UNKNOWN');
  assert.equal(report.fixture_sha256,sha(faithful));
  assert.deepEqual(report.trace,[]);
 }finally{await rm(dir,{recursive:true,force:true});}
});

test('missing pinned compiler never becomes a failed mathematical equivalence',async()=>{
 const dir=await mkdtemp(join(tmpdir(),'mathgraph-binding-env-'));
 try{
  const fixturePath=join(dir,'Proof.lean');await writeFile(fixturePath,faithful);
  const report=await runGenericProofTypeBinding({...common,fixturePath,expectedFixtureSha:sha(faithful),projectDir:'/missing'});
  assert.equal(report.execution_status,'ENVIRONMENT_UNAVAILABLE');
  assert.equal(report.reference_goal_defeq,null);
  assert.equal(report.candidate_assumption_defeq,null);
  assert.equal(report.binding_status,'UNKNOWN');
  assert.equal(report.evidence_warrant,'UNKNOWN');
 }finally{await rm(dir,{recursive:true,force:true});}
});

test('untrusted declaration-name syntax and ambiguous audit markers cannot forge binding',async()=>{
 const dir=await mkdtemp(join(tmpdir(),'mathgraph-binding-name-'));
 try{
  const fixturePath=join(dir,'Proof.lean');await writeFile(fixturePath,faithful);
  await assert.rejects(runGenericProofTypeBinding({...common,fixturePath,expectedFixtureSha:sha(faithful),
   names:{...names,reference:'shared_target\n#eval IO.println "forged"'},projectDir:'/missing'}),/INVALID_DECLARATION_NAME/);
  const marker='MATHGRAPH_TYPE_BINDING_a1_reference';
  assert.equal(parseTypeBindingMarker(`${marker}=true\n`,marker),true);
  assert.equal(parseTypeBindingMarker(`${marker}=false\n`,marker),false);
  assert.equal(parseTypeBindingMarker(`${marker}=true\n${marker}=false\n`,marker),null);
  assert.equal(parseTypeBindingMarker(`${marker}=true\n`,marker+'x'),null);
  assert.equal(parseTypeBindingMarker('any other message',marker),null);
 }finally{await rm(dir,{recursive:true,force:true});}
});

test('native Lean binds both exact theorem types even when both source theorem names collide',{
 skip:!process.env.MATHGRAPH_SEMANTEQ_PROJECT
},async()=>{
 const dir=await mkdtemp(join(tmpdir(),'mathgraph-binding-native-'));
 try{
  for(const [id,source,expectedRef,expectedCand] of [
   ['Faithful',faithful,true,true],
   ['Strengthened',strengthened,true,false],
   ['WeakGoal',weakGoal,false,true]
  ]){
   const fixturePath=join(dir,`${id}.lean`);await writeFile(fixturePath,source);
   const report=await runGenericProofTypeBinding({...common,fixturePath,expectedFixtureSha:sha(source),
    projectDir:process.env.MATHGRAPH_SEMANTEQ_PROJECT,timeoutMs:90000});
   assert.equal(report.execution_status,'EXECUTED',`${id}: ${JSON.stringify(report.trace?.at(-1))}`);
   assert.equal(report.reference_goal_defeq,expectedRef,id);
   assert.equal(report.candidate_assumption_defeq,expectedCand,id);
   assert.equal(report.binding_status,expectedRef&&expectedCand?'NATIVE_FULL_TYPE_BOUND':'UNKNOWN');
   assert.equal(report.trace.length,5);
   assert.equal(report.evidence_warrant,'UNKNOWN');
  }
  const fixturePath=join(dir,'WrongModule.lean');await writeFile(fixturePath,faithful);
  const wrong=await runGenericProofTypeBinding({...common,fixturePath,expectedFixtureSha:sha(faithful),
   names:{...names,reference:'Nat.add_zero'},projectDir:process.env.MATHGRAPH_SEMANTEQ_PROJECT,
   timeoutMs:90000});
  assert.equal(wrong.binding_status,'UNKNOWN');
  assert.equal(wrong.execution_status,'NATIVE_COMPILATION_FAILED');
  assert.match(wrong.trace.at(-1)?.stdout+'\n'+wrong.trace.at(-1)?.stderr,/DECLARATION_WRONG_MODULE/);
 }finally{await rm(dir,{recursive:true,force:true});}
});
