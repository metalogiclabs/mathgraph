import test from 'node:test';
import assert from 'node:assert/strict';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {mkdtemp,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {buildCandidateProofReferenceAudit,parseCandidateProofReferenceMarker,
 classifyCandidateProofReference} from './generic-candidate-proof-reference-v1.mjs';

const exec=promisify(execFile);
const marker='MATHGRAPH_CANDIDATE_REFERENCE_1234567890abcde';

test('native proof-term marker must be unique and authentic to the current invocation',()=>{
 assert.equal(parseCandidateProofReferenceMarker(`${marker}=true\n`,marker),true);
 assert.equal(parseCandidateProofReferenceMarker(`${marker}=false\n`,marker),false);
 assert.equal(parseCandidateProofReferenceMarker(`${marker}=true\n${marker}=false\n`,marker),null);
 assert.equal(parseCandidateProofReferenceMarker('MATHGRAPH_CANDIDATE_REFERENCE_other=true\n',marker),null);
 assert.equal(parseCandidateProofReferenceMarker(`${marker}=false\n${marker}=true\n`,marker),null);
 assert.equal(parseCandidateProofReferenceMarker('random output',marker),null);
 assert.throws(()=>buildCandidateProofReferenceAudit({candidateName:'target\n#eval IO.println "YES"',consumerName:'final',marker}),/INVALID_DECLARATION_NAME/);
 assert.throws(()=>buildCandidateProofReferenceAudit({candidateName:'target',consumerName:'final',marker:'forged'}),/INVALID_MARKER/);
});

test('a reference in the actual proof term is bounded, never essential semantic dependence',()=>{
 const valid={compiled:true,record:true,candidateAxioms:['propext'],consumerAxioms:['propext']};
 assert.equal(classifyCandidateProofReference(valid),'NATIVE_ZETA_NORMALIZED_DIRECT_REFERENCE');
 for(const bad of [{record:false},{record:null},{compiled:false},{candidateAxioms:['sorryAx']},
  {consumerAxioms:['custom_axiom']},{candidateAxioms:null},{consumerAxioms:null}]){
  assert.equal(classifyCandidateProofReference({...valid,...bad}),'UNKNOWN');
 }
});

test('real Lean proof value survives dependent use but not library bypass or dead have',{skip:!process.env.MATHGRAPH_LEAN_BIN},async()=>{
 const dir=await mkdtemp(join(tmpdir(),'mathgraph-real-candidate-'));
 const candidate=`import Init\ntheorem candidate_target (n : Nat) : n + 0 = n := by simp\n`;
 const consumer=`import Candidate\ntheorem consumer_dependent (n : Nat) : n + 0 = n := candidate_target n\ntheorem consumer_bypass (n : Nat) : n + 0 = n := Nat.add_zero n\ntheorem consumer_dead (n : Nat) : n + 0 = n := by\n  have h := candidate_target n\n  exact Nat.add_zero n\n`;
 try{
  const env={...process.env,LEAN_PATH:dir};
  await writeFile(join(dir,'Candidate.lean'),candidate);
  await writeFile(join(dir,'Consumer.lean'),consumer);
  const run=async(unit,compile)=>{
   const args=[...(compile?['-o',join(dir,`${unit}.olean`)]:[]),join(dir,`${unit}.lean`)];
   return await exec(process.env.MATHGRAPH_LEAN_BIN,args,{env,cwd:dir,timeout:45000,maxBuffer:1048576});
  };
  await run('Candidate',true);
  await run('Consumer',true);
  for(const [name,expected] of [['consumer_dependent',true],['consumer_bypass',false],['consumer_dead',false]]){
   const audit=buildCandidateProofReferenceAudit({candidateName:'candidate_target',consumerName:name,marker});
   await writeFile(join(dir,'Audit.lean'),audit);
   const out=await run('Audit',false);
   assert.equal(parseCandidateProofReferenceMarker(out.stdout,marker),expected,name);
   assert.match(out.stdout,/'candidate_target' depends on axioms: \[propext\]/);
   assert.match(out.stdout,new RegExp(`'${name}'`));
  }
  await writeFile(join(dir,'Audit.lean'),buildCandidateProofReferenceAudit({candidateName:'Nat.add_zero',consumerName:'consumer_dependent',marker}));
  await assert.rejects(run('Audit',false),e=>{
   assert.match(String(e.stdout??'')+'\n'+String(e.stderr??''),/DECLARATION_WRONG_MODULE/);
   return true;
  });
  await writeFile(join(dir,'Candidate.lean'),'import Init\ntheorem candidate_target (n : Nat) : n + 0 = n := by sorry\n');
  await run('Candidate',true);
  await run('Consumer',true);
  await writeFile(join(dir,'Audit.lean'),buildCandidateProofReferenceAudit({candidateName:'candidate_target',consumerName:'consumer_dependent',marker}));
  const sorry=await run('Audit',false);
  assert.equal(parseCandidateProofReferenceMarker(sorry.stdout,marker),true);
  assert.match(sorry.stdout,/'candidate_target' depends on axioms: \[sorryAx\]/);
  assert.equal(classifyCandidateProofReference({compiled:true,record:true,candidateAxioms:['sorryAx'],consumerAxioms:['sorryAx']}),'UNKNOWN');
 }finally{await rm(dir,{recursive:true,force:true});}
});
