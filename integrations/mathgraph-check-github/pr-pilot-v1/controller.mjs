import {authenticateImported,publicGitHub} from './imported-check.mjs';
import {checkURL} from './request-status.mjs';
import {queuePilotStatus} from './status-queue.mjs';
import {PILOT_RELEASE} from './pilot-config.mjs';
import {isFiniteMethod,admitFinitePatch} from './finite-methods.mjs';
import {REPORT_METHOD,reportReference} from './report-integrity.mjs';
import {GENERATOR_METHOD,generatorReference,admitProfilePatch} from './traceof-comments.mjs';
import {admitClaimResult,captureClaimSnapshot} from './claim.mjs';
import {CLI_MODE} from './cli-profiles.mjs';
import {admitCliResult} from './cli-parity.mjs';
import {spawnSync} from 'node:child_process';
import {admitRepositoryResult,captureRepositorySnapshot} from './repository-contract.mjs';
import {CONTRACT_MODE} from './repository-report.mjs';
import {executionContext} from './context.mjs';
import {createRepair} from './repair.mjs';
import {renderReport,finalPublicationReport} from './report.mjs';
// Trusted hosted orchestration. No repository source executes in this process.
import {readFile,writeFile,readdir,mkdir,appendFile} from 'node:fs/promises';import {createHash} from 'node:crypto';
import {mintScopedToken} from './auth.mjs';
import {appJWT} from '../cloudflare/worker.mjs';import {githubClient} from './github.mjs';import {verifyDispatch} from './transport.mjs';import {authenticate,startCheck,finishCheck,identity,logicalIdentity,listChecks,priorCheckRun} from './lifecycle.mjs';import {admitRequest,modelReservationCents,resultTitle} from './policy.mjs';import {rebindFrozenPlan} from './reuse.mjs';
import {admitLeanPatch} from '../lean-investigator-v1/contracts.mjs';
import {expectationSubject,reviewedPlan,admitExpectations} from './expectations.mjs';
import {captureProducer,resolveProducer,producerIntakeDiagnostic} from './producer-transport.mjs';
const phase=process.argv[2],dir=process.argv[3]??'pr-investigation';
const context=executionContext();
const hash=x=>createHash('sha256').update(x).digest('hex'),ensure=(b,c)=>{if(!b)throw Error(c);};
ensure(/^[a-f0-9]{40}$/.test(context.verifier_sha??'')&&context.attempt===1&&Number.isSafeInteger(context.run_id),'INVALID_WORKFLOW_CONTEXT');
await mkdir(dir,{recursive:true});
const get=async n=>JSON.parse(await readFile(`${dir}/${n}.json`,'utf8')),save=async(n,v)=>writeFile(`${dir}/${n}.json`,JSON.stringify(v,null,2)+'\n');
async function producerToken(){const request=await get('request');return request.profile.expectation_candidate?resolveProducer(await get('producer-envelope'),request,context).token:undefined;}
async function seal(){const hashes={};for(const n of(await readdir(dir)).filter(n=>n.endsWith('.json')&&n!=='manifest.json').sort())hashes[n]=hash(await readFile(`${dir}/${n}`));await save('manifest',{context,hashes});}
async function verifyManifest(folder=dir){const m=JSON.parse(await readFile(`${folder}/manifest.json`));for(const [n,h]of Object.entries(m.hashes)){ensure(/^[a-z][a-z0-9_-]*\.json$/.test(n)&&hash(await readFile(`${folder}/${n}`))===h,'ARTIFACT_CHANGED');}ensure(JSON.stringify((await readdir(folder)).filter(n=>n.endsWith('.json')&&n!=='manifest.json').sort())===JSON.stringify(Object.keys(m.hashes).sort()),'UNMANIFESTED_ARTIFACT');return m;}
async function outputs(values){if(process.env.GITHUB_OUTPUT)await appendFile(process.env.GITHUB_OUTPUT,Object.entries(values).map(([k,v])=>`${k}=${v}`).join('\n')+'\n');}
async function sourceToken(repository,write=false){
 const app=githubClient(appJWT(process.env.APP_PRIVATE_KEY),{repository});const i=await app('/repos/'+repository+'/installation');
 const token=await mintScopedToken(app,i.id,repository,{contents:write?'write':'read',pull_requests:write?'write':'read',checks:'write',issues:'write'});
 return {api:githubClient(token,{repository}),installation_id:i.id};
}
try{
 if(phase==='intake'||phase==='qualify-intake'){
  const runURL=`https://github.com/metalogiclabs/mathgraph/actions/runs/${context.run_id}`;
  let request,publication;
  if(phase==='qualify-intake'){
   ensure(['refs/heads/pilot/check-pr-qualify-v1','refs/heads/pilot/check-pr-fix-qualify-v1'].includes(process.env.GITHUB_REF),'QUALIFICATION_BRANCH_REQUIRED');
   // Read-only adapter qualification, explicitly not a maintainer command or App install.
   const repository='metalogiclabs/L4YAML',number=2,api=githubClient(process.env.GITHUB_TOKEN,{repository});
   const pr=await api(`/repos/${repository}/pulls/${number}`),files=await api(`/repos/${repository}/pulls/${number}/files?per_page=100&page=1`);
   request=admitRequest({repository,pr,files,permission:'admin',comment:{id:context.run_id,body:'@MathGraph -check',user:{id:32909488,login:'heathsanchez',type:'User'}},filesComplete:pr.changed_files===files.length});request.qualification_only=true;request.command=process.env.GITHUB_REF.includes('fix-qualify')?'fix':'check';
   publication={state:'QUALIFICATION_ONLY',run_url:runURL,prior_run:41527964407};
  }else{
   const event=JSON.parse(await readFile(process.env.GITHUB_EVENT_PATH,'utf8'));ensure(['mathgraph-pr-pilot-v1','mathgraph-pr-selfserve-v1','mathgraph-pr-report-v1','mathgraph-pr-selfserve-v2'].includes(event.action),'WRONG_DISPATCH_EVENT');
   const signed=verifyDispatch(event.client_payload,process.env.APP_PRIVATE_KEY),scoped=await sourceToken(signed.repository);
   try{ensure(scoped.installation_id===signed.installation_id,'INSTALLATION_CHANGED');request=signed.origin?await authenticateImported(signed,scoped.api,{pilotOperators:signed.actor_authorization==='PILOT_OPERATOR'?[signed.actor_id]:[],publicAPI:publicGitHub({token:process.env.GITHUB_TOKEN})}):await authenticate(signed,scoped.api,{pilotOperators:signed.actor_authorization==='PILOT_OPERATOR'?[signed.actor_id]:[]});ensure(event.action==='mathgraph-pr-selfserve-v2'&&request.profile.release===PILOT_RELEASE,'METHOD_WORKFLOW_MISMATCH');request.watch_expires_at=signed.watch_expires_at;request.installation_id=scoped.installation_id;request.queued_check_id=signed.queued_check_id;ensure(request.head_sha===signed.head_sha&&request.base_sha===signed.base_sha,'SOURCE_CHANGED_BEFORE_START');
    ensure(signed.reserved_cents>=modelReservationCents(request),'MISSING_SPEND_RESERVATION');
    publication=await startCheck(request,scoped.api,runURL);await save('request',request);await save('publication',{...publication,context});
    if(request.profile.expectation_candidate&&publication.state==='STARTED'){
     try{const envelope=await captureProducer(request,context,scoped.api,githubClient(process.env.GITHUB_TOKEN,{repository:request.repository}),process.env.GITHUB_TOKEN);await save('producer-envelope',envelope);await save('producer-warrant',resolveProducer(envelope,request,context).graph);request.profile.expectation_profile='ledger-shell-v2';}
     catch(e){const diagnostic=producerIntakeDiagnostic(e);await save('producer-intake-error',{context,...diagnostic});request.support={supported:false,reason:'REPAIR_EXPECTATION_REVIEW_REQUIRED',diagnostic:diagnostic.message};}
    }
    if([CONTRACT_MODE,CLI_MODE].includes(request.profile.mode)&&publication.state==='STARTED'&&process.env.CONTRACTS_OK!=='false'){
     let snapshot=await captureRepositorySnapshot(request,scoped.api);
     if(request.profile.claim_profile){try{snapshot=await captureClaimSnapshot(request,snapshot,githubClient(process.env.GITHUB_TOKEN,{repository:'nasa-jpl/L4YAML'}));}catch{await save('claim-intake-error',{context,reason:'CLAIM_INTAKE_INCOMPLETE'});}}
     await save('contract-snapshot',snapshot);
    }
    if(publication.state==='STARTED'){const prior=await priorCheckRun(request,scoped.api);if(prior)publication.prior_run=prior;}
   }finally{await scoped.api('/installation/token',{method:'DELETE'});}
  }
  await save('request',request);await save('publication',{...publication,context});
  const ready=request.support.supported&&publication.state!=='DUPLICATE'&&process.env.CONTRACTS_OK!=='false';await outputs({ready:String(ready),command:request.command,profile:request.profile.mode,prior_run:publication.prior_run??'',source_head:request.head_sha});
  if(!request.support.supported||process.env.CONTRACTS_OK==='false')await save('assessment',{context,subject:request,status:'UNKNOWN',reason:process.env.CONTRACTS_OK==='false'?'CONTROLLER_CONTRACTS_FAILED':request.support.reason,expectation_review_reason:request.support.diagnostic});await seal();
 }else if(phase==='expectation-run'){
  ensure(JSON.stringify((await verifyManifest()).context)===JSON.stringify(context),'STALE_EXPECTATION_CONTEXT');
  const snapshot=await get('snapshot'),subject=expectationSubject(snapshot);let reference;
  if(snapshot.expectation_profile===REPORT_METHOD){const r=spawnSync('python3',['integrations/mathgraph-check-github/pr-pilot-v1/report-reference.py',dir+'/report-observations.json'],{stdio:'inherit',timeout:30000});ensure(r.status===0&&!r.error,'REPORT_REFERENCE_INCOMPLETE');await save('expectation-reference',reportReference(subject,context,await get('report-observations')));await seal();process.exit(0);}
  if(snapshot.expectation_profile===GENERATOR_METHOD){await save('expectation-reference',generatorReference(subject,context));await seal();process.exit(0);}
  if(reviewedPlan(subject,await producerToken(),snapshot.expectation_profile)){
   const run=spawnSync('python3',['experiments/check-expectation-admission-v1/run.py','--output',dir+'/expectation-observations.json'],{stdio:'inherit',timeout:30000});
   if(!run.error&&run.status===0)try{reference=await get('expectation-observations');}catch{}
  }
  let leading_reference;if(snapshot.expectation_profile==='ledger-shell-v2'){const run=spawnSync('python3',['experiments/check-leading-redirection-v1/reference.py','--output',dir+'/leading-observations.json'],{stdio:'inherit',timeout:30000});if(!run.error&&run.status===0)try{leading_reference=await get('leading-observations');}catch{}}
  await save('expectation-reference',{schema:'mathgraph.expectations.reference.v1',context,subject,expectation_set:snapshot.expectation_profile,reference:reference??{records:[]},leading_reference});await seal();
 }else if(phase==='contract-run'){
  ensure(JSON.stringify((await verifyManifest()).context)===JSON.stringify(context),'STALE_CONTRACT_CONTEXT');const request=await get('request');
  ensure(request.command==='check'&&[CONTRACT_MODE,CLI_MODE].includes(request.profile.mode)&&request.support.supported,'CONTRACT_CHECK_ONLY');
  const cli=request.profile.mode===CLI_MODE,folder=dir+(cli?'/cli-native':'/contract-native');
  const command=['integrations/mathgraph-check-github/'+(cli?'cli-parity-v1':'repository-contract-v1')+'/run.py','--pr',String(request.number),'--base',request.base_sha,'--head',request.head_sha,'--snapshot',dir+'/contract-snapshot.json','--output',folder];
  if(cli)command.push('--profile',request.profile.cli_profile);
  const native=spawnSync('python3',command,{stdio:'inherit',timeout:1500000});
  try{await save(cli?'cli-receipt':'contract-receipt',JSON.parse(await readFile(folder+'/result.json','utf8')));}catch{}
  if(cli){for(const name of ['contract','cases'])await writeFile(dir+'/cli-'+name+'.json',await readFile('integrations/mathgraph-check-github/cli-parity-v1/'+name+'.json'));}
  else try{await writeFile(dir+'/contract-corpus.json',await readFile(folder+'/corpus.json'));}catch{}
  if(request.profile.claim_profile){
   const snapshot=await get('contract-snapshot');
   if(snapshot.upstream_claim){
    spawnSync('python3',['experiments/check-l4-claim-consumer-v1/run.py','--pr',String(request.number),'--snapshot',dir+'/contract-snapshot.json','--output',dir+'/claim-native'],{stdio:'inherit',timeout:1500000});
    try{await save('claim-receipt',JSON.parse(await readFile(dir+'/claim-native/receipt.json','utf8')));}catch{}
   }
  }
  await seal();ensure(!native.error&&native.status===0,'CONTRACT_NATIVE_INCOMPLETE');
 }else if(phase==='contract-assess'){
  ensure(JSON.stringify((await verifyManifest()).context)===JSON.stringify(context),'STALE_CONTRACT_CONTEXT');const request=await get('request');let receipt;
  try{receipt=await get(request.profile.mode===CLI_MODE?'cli-receipt':'contract-receipt');}catch{}
  let corpus=null;try{corpus=await readFile(dir+'/contract-corpus.json');}catch{}
  const assessment=request.profile.mode===CLI_MODE?admitCliResult(receipt,request,context):admitRepositoryResult(receipt,request,context,corpus);
  if(request.profile.claim_profile){let claim;try{claim=await get('claim-receipt');}catch{}assessment.claim=admitClaimResult(claim,request,context);if(!claim){try{assessment.claim.reason=(await get('claim-intake-error')).reason;}catch{}}}
  await save('assessment',assessment);await seal();
 }else if(phase==='reuse'){
  await verifyManifest();const request=await get('request'),publication=await get('publication'),priorDir=process.argv[4]??'prior-investigation';
  ensure(Number.isSafeInteger(publication.prior_run),'NO_PRIOR_CHECK');const prior=await verifyManifest(priorDir);ensure(prior.context.run_id===publication.prior_run,'PRIOR_RUN_MISMATCH');
  const central=githubClient(process.env.GITHUB_TOKEN,{repository:request.repository}),run=await central(`/repos/metalogiclabs/mathgraph/actions/runs/${publication.prior_run}`);
  ensure(run.path===(request.profile.release===PILOT_RELEASE?'.github/workflows/check-pr-selfserve-v2.yml':request.profile.method===REPORT_METHOD?'.github/workflows/check-pr-report.yml':isFiniteMethod(request.profile.method)?'.github/workflows/check-pr-selfserve.yml':'.github/workflows/check-pr-pilot.yml')&&(run.event==='repository_dispatch'||request.qualification_only&&run.event==='push'&&run.head_branch==='pilot/check-pr-qualify-v1')&&run.head_sha===(prior.context.scheduler_sha??prior.context.verifier_sha)&&run.repository?.full_name==='metalogiclabs/mathgraph'&&run.run_attempt===1,'UNTRUSTED_PRIOR_WORKFLOW');
  const read=async n=>JSON.parse(await readFile(`${priorDir}/${n}.json`));
  const qualificationReplay=request.qualification_only&&prior.context.run_id===41527964407&&prior.context.verifier_sha==='d8f49afb356d95674e7f6ec92c1d764becdf196f';
  const data=rebindFrozenPlan({context:prior.context,snapshot:await read('snapshot'),plan:await read('plan'),state:await read('state'),assessment:await read('assessment')},{...request,command:'fix'},qualificationReplay?{...context,verifier_sha:prior.context.verifier_sha}:context);
  data.snapshot.command=request.command;data.state.context=context;data.state.proposal_origin=prior.context;
  const current=await fetch(`https://raw.githubusercontent.com/${request.repository}/${request.head_sha}/${request.profile.path}`,{signal:AbortSignal.timeout(20000)});ensure(current.ok&&hash(await current.text())===data.snapshot.source_sha256,'SOURCE_CHANGED');
  for(const[n,v]of Object.entries(data))await save(n,v);await save('origin-receipt',{prior_run:publication.prior_run,prior_context:prior.context,new_model_test_generation:false});await seal();
 }else if(phase==='revision'){
  await verifyManifest();let n;try{n=await get('native-repair');}catch{}
  let patch;try{patch=await get('patch');}catch{}
  const request=await get('request');
  if(request.command!=='fix'||!patch||!n||n.repaired?.build_exit===0){await outputs({revision:'false'});process.exit(0);}
  ensure(!((await readdir(dir)).includes('attempt-one.json')),'REVISION_LIMIT');
  const model=await get('model-repair'),diagnostic=await readFile(`${dir}/native-logs/repair-repaired-build.log`,'utf8');
  await save('attempt-one',{native:n,patch,model});
  await save('prior-feedback',{prior_candidate:model.proposal,compiler_diagnostic:diagnostic.slice(-5000),instruction:'Revise the failed patch using compiler feedback. Original source and frozen probes are unchanged.'});
  await outputs({revision:'true'});await seal();
 }else if(phase==='settle'){
  await verifyManifest();const request=await get('request'),publication=await get('publication');if(publication.state==='DUPLICATE')process.exit(0);
  ensure(JSON.stringify(publication.context)===JSON.stringify(context),'STALE_PUBLICATION');
  let report;try{report=await get('assessment');ensure(JSON.stringify(report.context)===JSON.stringify(context),'STALE_ASSESSMENT');if(report.subject)ensure(report.subject.head_sha===request.head_sha&&report.subject.repository===request.repository,'ASSESSMENT_SUBJECT_MISMATCH');}catch{let error;try{error=await get('controller-error');}catch{}report={context,status:'UNKNOWN',reason:error?.reason??'ASSESSMENT_INCOMPLETE'};}
  if(request.qualification_only){await save('qualification-result',{request,report,scope:'READ_ONLY_ADAPTER_QUALIFICATION_NO_SOURCE_REPOSITORY_APP_CHECK'});await seal();process.exit(0);}
  const scoped=await sourceToken(request.repository,request.command==='fix');
  try{
   ensure(scoped.installation_id===request.installation_id,'INSTALLATION_CHANGED');
   if(request.origin){try{const current=await authenticateImported({...request,actor_id:request.actor_id},scoped.api,{pilotOperators:request.actor_authorization==='PILOT_OPERATOR'?[request.actor_id]:[],publicAPI:publicGitHub({token:process.env.GITHUB_TOKEN})});ensure(current.head_sha===request.head_sha&&current.base_sha===request.base_sha,'IMPORTED_SNAPSHOT_LINEAGE_INVALID');}catch(e){report={...report,status:e.message==='UPSTREAM_CHANGED_RETRY_REQUIRED'?'STALE':'UNKNOWN',reason:e.message==='UPSTREAM_CHANGED_RETRY_REQUIRED'?'UPSTREAM_SOURCE_CHANGED':'ORIGINAL_AUTHORITY_OR_SNAPSHOT_CHANGED',repair:{status:'UNKNOWN'}};}}
   if(request.command==='fix'&&report.status!=='STALE'&&report.status!=='UNKNOWN'&&report.repair?.status==='PATCH_PASSES_FROZEN_GUARDS_AND_REPOSITORY_GATE'){
    const snapshot=await get('snapshot'),patch=await get('patch');
    ensure(snapshot.head_sha===request.head_sha&&snapshot.repository===request.repository,'REPAIR_SUBJECT_MISMATCH');
    const gate=admitExpectations(expectationSubject(snapshot),await get('plan'),await get('expectation-reference'),context,await producerToken(),snapshot.expectation_profile);ensure(gate.repair_eligible,'REPAIR_EXPECTATION_NOT_ADMITTED');
    ensure(hash(admitFinitePatch(patch,snapshot.source,snapshot))===report.repair.patched_sha256,'UNVERIFIED_PATCH');
    try{report.repair_pr=await createRepair(request,patch,publication,scoped.api);}catch(e){await save('repair-publication-error',{context,reason:/^[A-Z0-9_]+$/.test(e.message)?e.message:'REPAIR_PUBLICATION_INCOMPLETE'});report={...report,repair:{...report.repair,verification_status:report.repair.status,status:'UNKNOWN'},reason:'REPAIR_PUBLICATION_INCOMPLETE'};}
   }
   const result=await finishCheck(request,publication,report,scoped.api);await queuePilotStatus(request,{state:['UNKNOWN','STALE'].includes(report.status)||result.state==='STALE'?'UNKNOWN':'PUBLISHED',title:resultTitle(report,request),repair_url:report.status==='STALE'?undefined:report.repair_pr,check_url:checkURL(request.repository,request.number,publication.check_id),snapshot_url:request.origin?`https://github.com/${request.repository}/pull/${request.number}`:undefined},process.env.APP_PRIVATE_KEY);await save('publication-result',result);report=finalPublicationReport(report,result);await save('assessment',report);await seal();
   const [css,brand]=await Promise.all([readFile(new URL('./passport-base.css',import.meta.url),'utf8'),readFile(new URL('./passport-brand.json',import.meta.url),'utf8')]);await writeFile(dir+'/MathGraph-Check.html',renderReport({request,assessment:report,manifest:await get('manifest'),css,logo:JSON.parse(brand).logo}));
  }finally{await scoped.api('/installation/token',{method:'DELETE'});}await seal();
 }else throw Error('UNKNOWN_CONTROLLER_PHASE');
}catch(e){
 const reason=/^[A-Z0-9_]+$/.test(e.message)?e.message:'CONTROLLER_INCOMPLETE';await save('controller-error',{context,phase,reason});await outputs({ready:'false',revision:'false'});await seal();console.error(JSON.stringify({status:'UNKNOWN',phase,reason}));
 if(phase==='settle')process.exitCode=1;
}
