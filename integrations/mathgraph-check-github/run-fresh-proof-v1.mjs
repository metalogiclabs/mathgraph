// One paid epoch; all model output remains untrusted until native acceptance.
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {createHash} from 'node:crypto';

import {freezeTheorem,renderCandidate,originalConsumer,verifyFresh,runFreshComparison,authorizeProspectiveRun,repairWithNativePortfolio} from './mention-fresh-proof-v1.mjs';
import {freshNativeRunner} from './fresh-native-runner-v1.mjs';
const ensure=(ok,code)=>{if(!ok)throw Error(code);};
const protocol=JSON.parse(await readFile(new URL('./fixtures/fresh-proof-protocol-v1.json',import.meta.url),'utf8'));
const output=resolve(process.env.RUNNER_TEMP??'/tmp','mathgraph-fresh-proof');await mkdir(output,{recursive:true});
const source=await readFile(new URL('./fixtures/proofnet-heldout-2.lean',import.meta.url),'utf8');
ensure(createHash('sha256').update(source).digest('hex')===protocol.source.sha256,'PUBLISHED_SOURCE_CHANGED');
const frozen=freezeTheorem(source,protocol.source);
await writeFile(join(output,'frozen-target.json'),JSON.stringify({protocol,frozen},null,2),{mode:0o600});
if(process.argv.includes('--freeze-only')){console.log(JSON.stringify({status:'TARGET_FROZEN',source_sha256:frozen.source_sha256,target_sha256:frozen.target_sha256,registered_repair:false}));process.exit(0);}
const trace=[];
const runnerFor=async label=>{
 const directory=join(output,'native-'+label);await mkdir(directory,{recursive:true});
 const execute=await freshNativeRunner({directory,dependencyDirectory:process.env.MATHGRAPH_NATIVE_DEPS});
 return async(name,text,options)=>{const r=await execute(name,text,options);trace.push({attempt:label,unit:name,strict:options?.strict===true,code:r.code,output:r.output.slice(-16000)});await writeFile(join(output,'native-trace.json'),JSON.stringify(trace,null,2),{mode:0o600});return r;};
};
const run=await runnerFor('controls');
const positive=await run('Sanity','import Mathlib\nexample : True := by trivial\n'),negative=await run('Negative','import Mathlib\nexample : False := by trivial\n');ensure(positive.code===0&&negative.code===1,'NATIVE_CONTROLS_FAILED');
const baselineRun=await runnerFor('baseline');const plain=await baselineRun('Candidate',source),strict=await baselineRun('Candidate',source,{strict:true}),consumer=await baselineRun('Consumer',originalConsumer(frozen));
ensure(plain.code===0&&strict.code===1&&consumer.code===0&&/sorryAx/.test(consumer.output),'PLACEHOLDER_CONTROLS_FAILED');
const baseline={ordinary_lean_compilation:'ACCEPTS_PLACEHOLDER_WITH_WARNING',strict_lean_ci:'REJECTS_PLACEHOLDER',axiom_audit:'REJECTS_SORRY_AXIOM'};
await writeFile(join(output,'baseline.json'),JSON.stringify(baseline,null,2));
if(process.argv.includes('--native-preflight-only')){console.log(JSON.stringify({status:'NATIVE_PREFLIGHT_PASSED',...baseline}));process.exit(0);}
if(process.argv.includes('--native-portfolio-only')){
 const origin=JSON.parse(await readFile(new URL('./fixtures/fresh-native-followup-v1.json',import.meta.url),'utf8'));
 const bytes=await readFile(new URL('./fixtures/fresh-failed-proposals-v1.json',import.meta.url));
 ensure(createHash('sha256').update(bytes).digest('hex')===origin.proposals_sha256&&origin.source_sha256===frozen.source_sha256&&origin.target_sha256===frozen.target_sha256,'FOLLOWUP_BINDING_MISMATCH');
 const proposals=JSON.parse(bytes),attempts=[];let n=0;
 const result=await repairWithNativePortfolio({frozen,proposals,diagnostic:origin.diagnostic,maxAttempts:2,verify:async proof=>verifyFresh({frozen,proof,run:await runnerFor('portfolio-'+(++n))}),onAttempt:async item=>{attempts.push(item);await writeFile(join(output,'portfolio-attempts.json'),JSON.stringify(attempts,null,2));}});
 await writeFile(join(output,'native-followup.json'),JSON.stringify({origin,frozen,...result},null,2));
 if(result.status==='ORIGINAL_TARGET_VERIFIED')await writeFile(join(output,'verified-native-portfolio.lean'),renderCandidate(frozen,result.proof_body));
 console.log(JSON.stringify({status:result.status,post_hoc:true,api_calls:0,native_attempts:result.native_attempts,original_comparison:origin.original_comparison}));
 if(result.status!=='ORIGINAL_TARGET_VERIFIED')process.exitCode=1;process.exit();
}
ensure(process.env.GITHUB_REPOSITORY==='metalogiclabs/mathgraph'&&process.env.GITHUB_EVENT_NAME==='push'&&process.env.GITHUB_RUN_ATTEMPT==='1','ACTION_CONTEXT_REFUSED');
const runId=Number(process.env.GITHUB_RUN_ID);ensure(Number.isSafeInteger(runId)&&runId>0,'RUN_ID_REFUSED');
const github=async path=>{const r=await fetch('https://api.github.com/repos/metalogiclabs/mathgraph'+path,{redirect:'error',headers:{Authorization:'Bearer '+process.env.GITHUB_TOKEN,Accept:'application/vnd.github+json'},signal:AbortSignal.timeout(20000)});ensure(r.ok,'EPOCH_READ_FAILED');return r.json();};
const current=await github('/actions/runs/'+runId),history=await github('/actions/workflows/'+current.workflow_id+'/runs?event=push&actor=heathsanchez&per_page=100');authorizeProspectiveRun(current,history);ensure(current.head_sha===process.env.GITHUB_SHA,'SOURCE_HEAD_MISMATCH');
ensure(process.env.OPENAI_API_KEY&&process.env.OPENAI_API_KEY.length>10,'API_KEY_REQUIRED');
let reserved=0,calls=0;const ledger=[];
const generate=async context=>{
 const input=JSON.stringify(context);ensure(Buffer.byteLength(input)<=protocol.max_input_bytes&&calls<protocol.max_unique_requests&&reserved+25<=protocol.total_cap_cents,'EXPERIMENT_BUDGET_REFUSED');
 calls++;reserved+=25;ledger.push({request:calls,arm:context.arm,reserved_cents:25,status:'RESERVED_BEFORE_REQUEST'});await writeFile(join(output,'budget.json'),JSON.stringify({calls,reserved_cents:reserved,ledger},null,2),{mode:0o600});
 const r=await fetch('https://api.openai.com/v1/responses',{method:'POST',redirect:'error',headers:{Authorization:'Bearer '+process.env.OPENAI_API_KEY,'Content-Type':'application/json'},signal:AbortSignal.timeout(120000),body:JSON.stringify({model:protocol.model,service_tier:'default',store:false,max_output_tokens:4096,instructions:'Produce only a Lean 4 proof body beginning with by for the exact supplied theorem. Mathlib 4.28.0 is available. Do not change the theorem, add assumptions, use sorry/admit/axioms, alter options or define commands. No reference proof or registered solution is supplied. Return strict JSON. A separate native verifier will evaluate the result.',input,text:{format:{type:'json_schema',name:'fresh_lean_proof',strict:true,schema:{type:'object',properties:{proof_body:{type:'string'}},required:['proof_body'],additionalProperties:false}}}})});
 ensure(r.ok,'MODEL_REQUEST_FAILED');const d=await r.json();ensure(d.status==='completed','MODEL_INCOMPLETE');const texts=(d.output??[]).filter(x=>x.type==='message').flatMap(x=>x.content??[]).filter(x=>x.type==='output_text');ensure(texts.length===1,'MODEL_OUTPUT_REFUSED');const answer=JSON.parse(texts[0].text);ensure(Object.keys(answer).length===1&&typeof answer.proof_body==='string'&&Buffer.byteLength(answer.proof_body)<=12000,'MODEL_OUTPUT_REFUSED');
 ledger.at(-1).status='RESPONSE_RECEIVED';ledger.at(-1).usage=d.usage;await writeFile(join(output,'budget.json'),JSON.stringify({calls,reserved_cents:reserved,ledger},null,2),{mode:0o600});return {proof_body:answer.proof_body,usage:d.usage,response_id:d.id};
};
let attempt=0;
try{
 const result=await runFreshComparison({frozen,generate,verify:async proof=>{attempt++;const attemptRun=await runnerFor('attempt-'+attempt);const r=await verifyFresh({frozen,proof,run:attemptRun});await writeFile(join(output,'attempt-'+attempt+'.json'),JSON.stringify(r,null,2));if(r.status==='ORIGINAL_TARGET_VERIFIED')await writeFile(join(output,'verified-attempt-'+attempt+'.lean'),renderCandidate(frozen,proof));return r;},onProposal:async proposals=>writeFile(join(output,'proposals.json'),JSON.stringify(proposals,null,2),{mode:0o600})});
 await writeFile(join(output,'comparison.json'),JSON.stringify({protocol,frozen,baseline,...result,reserved_cents:reserved,native_run_id:runId},null,2),{mode:0o600});console.log(JSON.stringify({comparison:result.comparison,unique_api_calls:result.unique_api_calls,reserved_cents:reserved,llm_alone:result.llm_alone.status,mathgraph:result.mathgraph.status,registered_repair_used:false}));
}catch(e){await writeFile(join(output,'incomplete.json'),JSON.stringify({status:'UNKNOWN',error:/^[A-Z0-9_]+$/.test(e.message)?e.message:'EXPERIMENT_INCOMPLETE',calls,reserved_cents:reserved},null,2),{mode:0o600});throw Error('EXPERIMENT_INCOMPLETE_EVIDENCE_PRESERVED');}
