import {executionContext} from '../pr-pilot-v1/context.mjs';
import {expectationSubject,reviewedPlan,admitExpectations} from '../pr-pilot-v1/expectations.mjs';
import {resolveProducer} from '../pr-pilot-v1/producer-transport.mjs';
// Source audit orchestration. Repository data never selects commands or credentials.
import {readFile,writeFile,readdir,mkdir} from 'node:fs/promises';import {createHash} from 'node:crypto';
import {modelSnapshot,validatePilotSnapshot,compareProbeRows} from '../pr-pilot-v1/engine.mjs';
import {requestJSON,reservationCents} from '../investigator-v1/model.mjs';
import {admitLeanPlan,admitLeanPatch,assessGuard,guardBlocks,inspectArm} from './contracts.mjs';
const phase=process.argv[2],dir=process.argv[3]??'lean-investigation';
let profile={repository:'metalogiclabs/L4YAML',head_sha:'219f133cc93172fea46b08d09edf9b3b6441c0a4',path:'Scripts/Ledger.lean',module:'Scripts.Ledger',namespace:'Scripts.Ledger',cli_path:'Scripts/Main/CheckScriptsLedger.lean',cli_module:'Scripts.Main.CheckScriptsLedger',toolchain:'leanprover/lean4:v4.35.0',mode:'OWNER_SELECTED_RETROSPECTIVE_SOURCE_AUDIT'};
const context=executionContext();
const hash=x=>createHash('sha256').update(typeof x==='string'?x:JSON.stringify(x)).digest('hex');
const requireFact=(b,r)=>{if(!b)throw Error(r);};
requireFact(/^[a-f0-9]{40}$/.test(context.verifier_sha??'')&&Number.isSafeInteger(context.run_id)&&context.attempt===1,'INVALID_CONTEXT');
await mkdir(dir,{recursive:true});
const save=async(n,x)=>writeFile(`${dir}/${n}.json`,JSON.stringify(x,null,2)+'\n');
const load=async n=>JSON.parse(await readFile(`${dir}/${n}.json`,'utf8'));
async function producerToken(){let request;try{request=await load('request');}catch{}return request?.profile.expectation_candidate?resolveProducer(await load('producer-envelope'),request,context).token:undefined;}
async function seal(){const files=(await readdir(dir)).filter(n=>n.endsWith('.json')&&n!=='manifest.json').sort(),hashes={};for(const n of files)hashes[n]=hash(await readFile(`${dir}/${n}`,'utf8'));await save('manifest',{context,hashes});}
async function verify(){const m=await load('manifest');requireFact(JSON.stringify(m.context)===JSON.stringify(context),'STALE_ARTIFACT');requireFact(JSON.stringify((await readdir(dir)).filter(n=>n.endsWith('.json')&&n!=='manifest.json').sort())===JSON.stringify(Object.keys(m.hashes).sort()),'UNMANIFESTED_INPUT');for(const[n,h]of Object.entries(m.hashes))requireFact(/^[a-z][a-z0-9_-]*\.json$/.test(n)&&hash(await readFile(`${dir}/${n}`,'utf8'))===h,'ARTIFACT_CHANGED');}
function nativeIdentity(native,state,snapshot,plan){requireFact(JSON.stringify(native?.context)===JSON.stringify(context)&&native.source_sha===snapshot.head_sha&&native.test_digest===state.test_digest&&state.test_digest===hash(plan.tests)&&snapshot.source_sha256===hash(snapshot.source),'NATIVE_SOURCE_MISMATCH');}
async function source(path,revision=profile.head_sha){const r=await fetch(`https://raw.githubusercontent.com/${profile.repository}/${revision}/${path}`,{signal:AbortSignal.timeout(30000)});requireFact(r.ok,'SOURCE_HTTP_'+r.status);return r.text();}
try{
 if(phase==='prepare'){
  requireFact(reservationCents()*2<=100,'BUDGET_INVALID');
  let request;try{request=await load('request');}catch{}
  if(request){profile={...request.profile,number:request.number,head_sha:request.head_sha,base_sha:request.base_sha,command:request.command,comment_id:request.comment_id};requireFact(request.support?.supported===true,'UNSUPPORTED_CHANGED_FILE_SCOPE');}
  const snapshot={...profile,source:await source(profile.path),cli_source:await source(profile.cli_path),scope:'Audit this source against its own documented public behavior. No previous findings, fixes or counterexamples are supplied.'};
  if(request){snapshot.base_source=await source(profile.path,profile.base_sha);snapshot.base_cli_source=await source(profile.cli_path,profile.base_sha);validatePilotSnapshot(snapshot);requireFact(hash(snapshot.cli_source)==='64bb20331484ef711b6a752af1770959164c82308fd9ae79fbf954678ebbdbcf','CLI_NOT_REVIEWED');}
  snapshot.source_sha256=hash(snapshot.source);snapshot.cli_sha256=hash(snapshot.cli_source);
  await save('snapshot',snapshot);
  let plan,modelCalls=0;
  if(profile.expectation_profile){const fixed=reviewedPlan(expectationSubject(snapshot),await producerToken());requireFact(fixed,'EXPECTATION_SOURCE_NOT_QUALIFIED');plan=admitLeanPlan(fixed);}
  else{const response=await requestJSON({apiKey:process.env.OPENAI_API_KEY,stage:'lean-investigate',packet:{snapshot:modelSnapshot(snapshot)}});await save('model-investigate',response);plan=admitLeanPlan(response.proposal);modelCalls=1;}
  await save('plan',plan);await save('state',{context,state:'PROBES_PROPOSED',test_digest:hash(plan.tests),model_calls:modelCalls,expectation_origin:profile.expectation_profile??'MODEL_HYPOTHESIS'});await seal();
 }else if(phase==='repair'){
  await verify();const state=await load('state');if(state.state!=='PROBES_PROPOSED'){await seal();process.exit(0);}
  const snapshot=await load('snapshot');if(snapshot.command==='check'){await save('repair-state',{state:'CHECK_ONLY',model_calls:0});await seal();process.exit(0);}
  const plan=admitLeanPlan(await load('plan')),native=await load('native');
  nativeIdentity(native,state,snapshot,plan);const initial=inspectArm(native.arm,{profile:snapshot,plan,source:snapshot.source});
  if(!initial.complete){await save('repair-state',{state:'BASELINE_OR_PROBES_INCOMPLETE',model_calls:0});await seal();process.exit(0);}
  if(snapshot.mode==='OWNED_FORK_PR_PILOT'){
   let reference;try{reference=await load('expectation-reference');}catch{}
   const admission=admitExpectations(expectationSubject(snapshot),plan,reference,context,await producerToken());await save('expectation-admission',admission);
   if(!admission.repair_eligible){await save('repair-state',{state:'EXPECTATION_NOT_ADMITTED',model_calls:0});await seal();process.exit(0);}
  }
  const failed=initial.rows.some(p=>p.execution==='CANDIDATE_ASSERTION_FAILURE');
  if(!failed){await save('repair-state',{state:'NO_REPRODUCED_FAILURE',model_calls:0});await seal();process.exit(0);}
  let previous;try{previous=await load('prior-feedback');}catch{}
  const response=await requestJSON({apiKey:process.env.OPENAI_API_KEY,stage:'lean-repair',packet:{snapshot:modelSnapshot(snapshot),plan,previous_candidate_feedback:previous,native:{...native,arm:{...native.arm,probes:native.arm.probes.map(p=>({...p,output:p.output.slice(0,1800)}))}}}});await save('model-repair',response);
  if(!response.proposal.edits?.length){await save('repair-state',{state:'NO_CANDIDATE_PATCH',model_calls:1});await seal();process.exit(0);}
  const patched=admitLeanPatch(response.proposal,snapshot.source);await save('patch',{...response.proposal,path:snapshot.path,original_sha256:snapshot.source_sha256,patched_sha256:hash(patched),content:patched});
  await save('repair-state',{state:'PATCH_PROPOSED',model_calls:1,patched_sha256:hash(patched)});await seal();
 }else if(phase==='assess'){
  await verify();const state=await load('state');let report;
  let snapshot;try{snapshot=await load('snapshot');}catch{}
  const subject=snapshot?{repository:snapshot.repository,head_sha:snapshot.head_sha,path:snapshot.path,source_sha256:snapshot.source_sha256}:undefined;
  if(state.state!=='PROBES_PROPOSED')report={context,status:'UNKNOWN',stage:state.stage,reason:state.reason,subject};
  else{
   const plan=admitLeanPlan(await load('plan')),native=await load('native'),rs=await load('repair-state');
   nativeIdentity(native,state,snapshot,plan);
   const initial=inspectArm(native.arm,{profile:snapshot,plan,source:snapshot.source});
   const original=initial.rows.map(p=>({...p,execution:initial.complete?p.execution:'UNKNOWN',hypothesis:plan.tests.find(t=>t.id===p.id).hypothesis,contract:plan.tests.find(t=>t.id===p.id).contract}));
   let reference,expectations;try{reference=await load('expectation-reference');}catch{}
   if(snapshot.mode==='OWNED_FORK_PR_PILOT')expectations=admitExpectations(expectationSubject(snapshot),plan,reference,context,await producerToken());
   let repair={status:'NOT_PROPOSED'};
   if(rs.state==='PATCH_PROPOSED'){
    const fixed=await load('native-repair'),patch=await load('patch');const patched=admitLeanPatch(patch,snapshot.source);nativeIdentity(fixed,state,snapshot,plan);
    requireFact(hash(patched)===patch.patched_sha256&&fixed.patched_sha256===patch.patched_sha256,'REPAIR_SOURCE_MISMATCH');
    const old=inspectArm(fixed.original,{profile:snapshot,plan,source:snapshot.source}),after=inspectArm(fixed.repaired,{profile:snapshot,plan,source:patched}),withdrawn=inspectArm(fixed.withdrawn,{profile:snapshot,plan,source:snapshot.source});
    const qualified=(!expectations||expectations.repair_eligible)&&initial.complete&&old.complete&&after.complete&&withdrawn.complete&&old.rows.some(p=>p.execution==='CANDIDATE_ASSERTION_FAILURE')&&after.rows.every(p=>p.execution==='GUARD_PASSED')&&JSON.stringify(initial.rows)===JSON.stringify(old.rows)&&JSON.stringify(old.rows)===JSON.stringify(withdrawn.rows);
    repair={status:qualified?'PATCH_PASSES_FROZEN_GUARDS_AND_REPOSITORY_GATE':'UNKNOWN',original:old.rows,repaired:after.rows,withdrawn:withdrawn.rows,protected_guards:guardBlocks(snapshot.source).length,repository_gate_exits:[fixed.original.repository_gate_exit,fixed.repaired.repository_gate_exit,fixed.withdrawn.repository_gate_exit],patched_sha256:patch.patched_sha256};
   }
   let base=[],baseComplete=false;if(snapshot.base_source){requireFact(native.base_sha===snapshot.base_sha,'BASE_SOURCE_MISMATCH');const bs={...snapshot,source:snapshot.base_source};const observation=inspectArm(native.base_arm,{profile:bs,plan,source:snapshot.base_source});baseComplete=observation.complete;base=baseComplete?observation.rows:observation.rows.map(p=>({...p,execution:'UNKNOWN'}));}
   report={context,subject,base,base_complete:baseComplete,head_complete:initial.complete,comparison:compareProbeRows(base,original,{complete:baseComplete}),status:!initial.complete?'UNKNOWN':initial.rows.some(p=>p.execution==='CANDIDATE_ASSERTION_FAILURE')?'CANDIDATE_ASSERTION_FAILURE':'NO_COUNTEREXAMPLE_IN_GENERATED_GUARDS',original,repair,expectations,baseline:initial,source_guard_count:guardBlocks(snapshot.source).length,original_repository_gate_exit:native.arm.repository_gate_exit,meaning:expectations?.status==='ADMITTED'?'FINITE_OPERATOR_ADOPTED_OBLIGATION':'UNVERIFIED',permission:'ADVISORY_ONLY',scope:'Selected module/CLI build, original native guards, finite probes and repository gate. Expectation admission is separate from native execution. Not full L4YAML CI or automatic validation of inferred requirements.'};
  }
  await save('assessment',report);await seal();console.log(JSON.stringify(report));
 }else throw Error('UNKNOWN_PHASE');
}catch(e){const reason=/^[A-Z0-9_]+$/.test(e.message)?e.message:'STAGE_INCOMPLETE';await save('stage-error',{context,stage:phase,reason});await save('state',{context,state:'UNKNOWN',stage:phase,reason});if(phase==='assess'){let snapshot;try{snapshot=await load('snapshot');}catch{}await save('assessment',{context,status:'UNKNOWN',stage:phase,reason,subject:snapshot?{repository:snapshot.repository,head_sha:snapshot.head_sha,path:snapshot.path}:undefined});}await seal();console.error(JSON.stringify({status:'UNKNOWN',stage:phase,reason}));}
