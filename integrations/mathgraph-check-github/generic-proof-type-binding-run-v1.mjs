// First-party operator-only audit of elaborated Lean theorem types.
// Do not compile arbitrary PR-provided Lean outside an isolated sandbox.
import {createHash} from 'node:crypto';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {mkdtemp,readFile,rm,writeFile} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {bindFormalPair} from './generic-claim-audit-v1.mjs';
import {inspectPinnedLeanEnvironment} from './generic-lean-environment-v1.mjs';

const exec=promisify(execFile);
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const SAFE_NAME=/^[A-Za-z_][A-Za-z0-9_'.]{0,150}$/;
const MAX_TIMEOUT_MS=180000;

export function parseTypeBindingMarker(stdout,marker){
 if(typeof stdout!=='string'||typeof marker!=='string'||!marker)return null;
 const records=stdout.split(/\r?\n/).map(x=>x.trim()).filter(x=>x.includes('MATHGRAPH_TYPE_BINDING_'));
 if(records.length!==1)return null;
 if(records[0]===`${marker}=true`)return true;
 if(records[0]===`${marker}=false`)return false;
 return null;
}

function auditSource({side,sourceName,fixtureName,marker}){
 const sourceModule=side==='reference'?'Reference':'Candidate';
 const sourceQuote='`'+sourceName,fixtureQuote='`'+fixtureName;
 // Names are syntax-whitelisted by the caller. Both declarations must be
 // theorems originating in the exact byte-staged module, not inherited Mathlib.
 return `import Lean
import ${sourceModule}
import ProofFixture
open Lean Elab Command Meta
run_cmd do
  let env ← getEnv
  let some sourceInfo := env.find? ${sourceQuote} | throwError "SOURCE_DECLARATION_MISSING"
  let some fixtureInfo := env.find? ${fixtureQuote} | throwError "FIXTURE_DECLARATION_MISSING"
  unless sourceInfo.isTheorem && fixtureInfo.isTheorem do throwError "DECLARATION_NOT_THEOREM"
  let some sourceIdx := env.getModuleIdxFor? ${sourceQuote} | throwError "DECLARATION_WRONG_MODULE"
  let some fixtureIdx := env.getModuleIdxFor? ${fixtureQuote} | throwError "DECLARATION_WRONG_MODULE"
  let some sourceModule := env.header.modules[sourceIdx]? | throwError "DECLARATION_WRONG_MODULE"
  let some fixtureModule := env.header.modules[fixtureIdx]? | throwError "DECLARATION_WRONG_MODULE"
  unless sourceModule.module == ${'`'+sourceModule} && fixtureModule.module == ${'`ProofFixture'} do
    throwError "DECLARATION_WRONG_MODULE"
  let canonical (info : ConstantInfo) : Expr :=
    info.type.instantiateLevelParams info.levelParams
      (info.levelParams.mapIdx fun i _ => mkLevelParam (Name.mkSimple s!"u_{i}"))
  let matching ← liftTermElabM do
    Meta.withNewMCtxDepth do Meta.isDefEq (canonical sourceInfo) (canonical fixtureInfo)
  logInfo m!"${marker}={matching}"
`;
}

export async function runGenericProofTypeBinding({reference,candidate,expectedReferenceSha,
 fixturePath,expectedFixtureSha,names,projectDir,timeoutMs=60000}={}){
 const startedAt=new Date().toISOString(),started=performance.now();
 const pair=bindFormalPair({reference,candidate,expectedReferenceSha});
 if(!names||['reference','candidate','assumption','goal'].some(key=>
  typeof names[key]!=='string'||!SAFE_NAME.test(names[key])))throw Error('INVALID_DECLARATION_NAME');
 const path=typeof fixturePath==='string'&&fixturePath?resolve(fixturePath):null;
 const receipt={...pair,fixture_path:path,fixture_sha256:null,expected_fixture_sha256:expectedFixtureSha??null,
  declaration_names:{...names},reference_goal_defeq:null,candidate_assumption_defeq:null,
  binding_status:'UNKNOWN',execution_status:'ENVIRONMENT_UNAVAILABLE',trace:[],
  candidate_dependence:'UNKNOWN',intent_fidelity:'UNKNOWN',evidence_warrant:'UNKNOWN',
  started_at:startedAt,finished_at:null,wall_clock_ms:null};
 const finish=fields=>({...receipt,...fields,finished_at:new Date().toISOString(),
  wall_clock_ms:Math.round(performance.now()-started)});
 if(!path||typeof expectedFixtureSha!=='string'||!/^[a-f0-9]{64}$/i.test(expectedFixtureSha))
  return finish({execution_status:'INVALID_SOURCE_PIN',reason:'FIXTURE_PATH_AND_SHA_REQUIRED'});
 let fixture;
 try{fixture=await readFile(path);}catch(e){return finish({execution_status:'SOURCE_UNAVAILABLE',reason:`SOURCE_READ_FAILED:${e.code??e.message}`});}
 const fixtureSha=sha(fixture);
 receipt.fixture_sha256=fixtureSha;
 if(fixtureSha!==expectedFixtureSha.toLowerCase())
  return finish({execution_status:'SOURCE_HASH_MISMATCH',reason:'SOURCE_HASH_MISMATCH'});
 if(typeof projectDir!=='string'||!projectDir||!Number.isInteger(timeoutMs)||timeoutMs<1000||timeoutMs>MAX_TIMEOUT_MS)
  return finish({execution_status:'ENVIRONMENT_UNAVAILABLE',reason:'INVALID_PROJECT_OR_TIMEOUT'});
 const environment=await inspectPinnedLeanEnvironment(projectDir);
 if(!environment.ok)return finish({...environment,execution_status:'ENVIRONMENT_UNAVAILABLE',reason:environment.reason});
 let temporary;
 const trace=[];
 try{
  // Ignored build directory: simultaneous SemantEq processes inspect checkout
  // cleanliness, while byte copies avoid hash-vs-execute source-path races.
  temporary=await mkdtemp(join(environment.cwd,'.lake/build/mathgraph-type-binding-'));
  const stage={Reference:Buffer.from(reference.source,'utf8'),Candidate:Buffer.from(candidate.source,'utf8'),
   ProofFixture:fixture};
  for(const [unit,bytes] of Object.entries(stage))await writeFile(join(temporary,`${unit}.lean`),bytes,{flag:'wx',mode:0o400});
  const markerBase=sha(JSON.stringify({reference_sha256:pair.reference_sha256,
   candidate_sha256:pair.candidate_sha256,fixture_sha256:fixtureSha,names})).slice(0,20);
  const markers={reference:`MATHGRAPH_TYPE_BINDING_${markerBase}_reference`,
   candidate:`MATHGRAPH_TYPE_BINDING_${markerBase}_candidate`};
  const generated={BindReference:auditSource({side:'reference',sourceName:names.reference,
   fixtureName:names.goal,marker:markers.reference}),
   BindCandidate:auditSource({side:'candidate',sourceName:names.candidate,
    fixtureName:names.assumption,marker:markers.candidate})};
  for(const [unit,source] of Object.entries(generated))await writeFile(join(temporary,`${unit}.lean`),source,{flag:'wx',mode:0o400});
  const localEnv={...process.env,LEAN_PATH:temporary+(process.env.LEAN_PATH?`:${process.env.LEAN_PATH}`:'')};
  const runUnit=async unit=>{
   const args=['env','lean',...(['Reference','Candidate','ProofFixture'].includes(unit)?
    ['-o',join(temporary,`${unit}.olean`)]:[]),join(temporary,`${unit}.lean`)];
   const began=performance.now();
   try{
    const out=await exec('lake',args,{cwd:environment.cwd,env:localEnv,timeout:timeoutMs,maxBuffer:1048576});
    return {unit,command:['lake',...args],exit_code:0,stdout:out.stdout,stderr:out.stderr,
     wall_clock_ms:Math.round(performance.now()-began)};
   }catch(e){return {unit,command:['lake',...args],exit_code:typeof e.code==='number'?e.code:null,
    stdout:String(e.stdout??''),stderr:String(e.stderr??e.message),
    execution_failed:typeof e.code!=='number',wall_clock_ms:Math.round(performance.now()-began)};}
  };
  for(const unit of ['Reference','Candidate','ProofFixture','BindReference','BindCandidate']){
   const result=await runUnit(unit);trace.push(result);
   if(result.exit_code!==0||result.execution_failed)break;
  }
  const common={...environment,trace,staged_source_sha256:Object.fromEntries(
   Object.entries(stage).map(([unit,bytes])=>[unit,sha(bytes)])),
   generated_audit_sha256:Object.fromEntries(Object.entries(generated).map(([unit,src])=>[unit,sha(src)])),
   generated_audit_source:generated,markers};
  if(trace.length!==5||trace.some(x=>x.exit_code!==0||x.execution_failed))
   return finish({...common,execution_status:trace.some(x=>x.execution_failed)?'RUN_FAILED':'NATIVE_COMPILATION_FAILED',
    reason:'NATIVE_COMPILATION_FAILED'});
  const ref=parseTypeBindingMarker(trace[3].stdout,markers.reference);
  const cand=parseTypeBindingMarker(trace[4].stdout,markers.candidate);
  if(ref===null||cand===null)return finish({...common,execution_status:'INVALID_NATIVE_OUTPUT',reason:'TYPE_BINDING_RECORD_MISSING'});
  return finish({...common,execution_status:'EXECUTED',reference_goal_defeq:ref,
   candidate_assumption_defeq:cand,binding_status:ref&&cand?'NATIVE_FULL_TYPE_BOUND':'UNKNOWN',
   reason:ref&&cand?'NATIVE_TYPE_BOUND':'NOT_DEFINITIONALLY_EQUAL'});
 }catch(e){return finish({...environment,trace,execution_status:'RUN_FAILED',reason:`BINDING_RUN_FAILED:${e.message??e}`});}
 finally{if(temporary)await rm(temporary,{recursive:true,force:true});}
}
