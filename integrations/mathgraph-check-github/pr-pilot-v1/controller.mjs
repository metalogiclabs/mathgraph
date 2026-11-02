// Trusted hosted orchestration. No repository source executes in this process.
import {readFile,writeFile,readdir,mkdir,appendFile} from 'node:fs/promises';import {createHash} from 'node:crypto';
import {appJWT} from '../cloudflare/worker.mjs';import {githubClient} from './github.mjs';import {verifyDispatch} from './transport.mjs';import {authenticate,startCheck,finishCheck,identity} from './lifecycle.mjs';import {admitRequest} from './policy.mjs';import {rebindFrozenPlan} from './reuse.mjs';
import {admitLeanPatch} from '../lean-investigator-v1/contracts.mjs';
const phase=process.argv[2],dir=process.argv[3]??'pr-investigation';
const context={verifier_sha:process.env.GITHUB_SHA,run_id:Number(process.env.GITHUB_RUN_ID),attempt:Number(process.env.GITHUB_RUN_ATTEMPT)};
const hash=x=>createHash('sha256').update(x).digest('hex'),ensure=(b,c)=>{if(!b)throw Error(c);};
ensure(/^[a-f0-9]{40}$/.test(context.verifier_sha??'')&&context.attempt===1&&Number.isSafeInteger(context.run_id),'INVALID_WORKFLOW_CONTEXT');
await mkdir(dir,{recursive:true});
const get=async n=>JSON.parse(await readFile(`${dir}/${n}.json`,'utf8')),save=async(n,v)=>writeFile(`${dir}/${n}.json`,JSON.stringify(v,null,2)+'\n');
async function seal(){const hashes={};for(const n of(await readdir(dir)).filter(n=>n.endsWith('.json')&&n!=='manifest.json').sort())hashes[n]=hash(await readFile(`${dir}/${n}`));await save('manifest',{context,hashes});}
async function verifyManifest(folder=dir){const m=JSON.parse(await readFile(`${folder}/manifest.json`));for(const [n,h]of Object.entries(m.hashes)){ensure(/^[a-z][a-z0-9_-]*\.json$/.test(n)&&hash(await readFile(`${folder}/${n}`))===h,'ARTIFACT_CHANGED');}ensure(JSON.stringify((await readdir(folder)).filter(n=>n.endsWith('.json')&&n!=='manifest.json').sort())===JSON.stringify(Object.keys(m.hashes).sort()),'UNMANIFESTED_ARTIFACT');return m;}
async function outputs(values){if(process.env.GITHUB_OUTPUT)await appendFile(process.env.GITHUB_OUTPUT,Object.entries(values).map(([k,v])=>`${k}=${v}`).join('\n')+'\n');}
async function sourceToken(repository,write=false){
 const app=githubClient(appJWT(process.env.APP_PRIVATE_KEY),{repository});const i=await app('/repos/'+repository+'/installation');
 const minted=await app(`/app/installations/${i.id}/access_tokens`,{method:'POST',body:{repository_names:[repository.split('/')[1]],permissions:{contents:write?'write':'read',pull_requests:write?'write':'read',checks:'write',issues:'read'}}});
 return {api:githubClient(minted.token,{repository}),installation_id:i.id};
}
try{
 if(phase==='intake'||phase==='qualify-intake'){
  const runURL=`https://github.com/metalogiclabs/mathgraph/actions/runs/${context.run_id}`;
  let request,publication;
  if(phase==='qualify-intake'){
   ensure(process.env.GITHUB_REF==='refs/heads/pilot/check-pr-qualify-v1','QUALIFICATION_BRANCH_REQUIRED');
   // Read-only adapter qualification, explicitly not a maintainer command or App install.
   const repository='metalogiclabs/L4YAML',number=2,api=githubClient(process.env.GITHUB_TOKEN,{repository});
   const pr=await api(`/repos/${repository}/pulls/${number}`),files=await api(`/repos/${repository}/pulls/${number}/files?per_page=100&page=1`);
   request=admitRequest({repository,pr,files,permission:'admin',comment:{id:context.run_id,body:'@MathGraph -check',user:{id:32909488,login:'heathsanchez',type:'User'}},filesComplete:pr.changed_files===files.length});request.qualification_only=true;
   publication={state:'QUALIFICATION_ONLY',run_url:runURL};
  }else{
   const event=JSON.parse(await readFile(process.env.GITHUB_EVENT_PATH,'utf8'));ensure(event.action==='mathgraph-pr-pilot-v1','WRONG_DISPATCH_EVENT');
   const signed=verifyDispatch(event.client_payload,process.env.APP_PRIVATE_KEY),scoped=await sourceToken(signed.repository);
   try{ensure(scoped.installation_id===signed.installation_id,'INSTALLATION_CHANGED');request=await authenticate(signed,scoped.api);ensure(request.head_sha===signed.head_sha&&request.base_sha===signed.base_sha,'SOURCE_CHANGED_BEFORE_START');
    ensure(signed.reserved_cents>=(request.support.supported?(request.command==='check'?49:98):0),'MISSING_SPEND_RESERVATION');
    publication=await startCheck(request,scoped.api,runURL);await save('request',request);await save('publication',{...publication,context});
    if(request.command==='fix'&&publication.state==='STARTED'){
     const cs=await scoped.api(`/repos/${request.repository}/commits/${request.head_sha}/check-runs?per_page=100`);ensure(cs.total_count===cs.check_runs.length,'INCOMPLETE_CHECK_HISTORY');
     const original=cs.check_runs.find(c=>c.app?.id===5308912&&c.external_id===identity({...request,command:'check'})&&c.status==='completed'&&c.conclusion==='neutral');
     const match=original?.details_url?.match(/^https:\/\/github.com\/metalogiclabs\/mathgraph\/actions\/runs\/([1-9][0-9]*)$/);ensure(match,'RUN_CHECK_BEFORE_FIX');publication.prior_run=Number(match[1]);
    }
   }finally{await scoped.api('/installation/token',{method:'DELETE'});}
  }
  await save('request',request);await save('publication',{...publication,context});
  const ready=request.support.supported&&publication.state!=='DUPLICATE';await outputs({ready:String(ready),command:request.command,prior_run:publication.prior_run??'',source_head:request.head_sha});
  if(!request.support.supported)await save('assessment',{context,subject:request,status:'UNKNOWN',reason:request.support.reason});await seal();
 }else if(phase==='reuse'){
  await verifyManifest();const request=await get('request'),publication=await get('publication'),priorDir=process.argv[4]??'prior-investigation';
  ensure(Number.isSafeInteger(publication.prior_run),'NO_PRIOR_CHECK');const prior=await verifyManifest(priorDir);ensure(prior.context.run_id===publication.prior_run,'PRIOR_RUN_MISMATCH');
  const central=githubClient(process.env.GITHUB_TOKEN,{repository:request.repository}),run=await central(`/repos/metalogiclabs/mathgraph/actions/runs/${publication.prior_run}`);
  ensure(run.path==='.github/workflows/check-pr-pilot.yml'&&run.event==='repository_dispatch'&&run.head_sha===prior.context.verifier_sha&&run.repository?.full_name==='metalogiclabs/mathgraph'&&run.run_attempt===1,'UNTRUSTED_PRIOR_WORKFLOW');
  const read=async n=>JSON.parse(await readFile(`${priorDir}/${n}.json`));const data=rebindFrozenPlan({context:prior.context,snapshot:await read('snapshot'),plan:await read('plan'),state:await read('state'),assessment:await read('assessment')},request,context);
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
  let report;try{report=await get('assessment');ensure(JSON.stringify(report.context)===JSON.stringify(context),'STALE_ASSESSMENT');if(report.subject)ensure(report.subject.head_sha===request.head_sha&&report.subject.repository===request.repository,'ASSESSMENT_SUBJECT_MISMATCH');}catch{report={context,status:'UNKNOWN',reason:'ASSESSMENT_INCOMPLETE'};}
  if(request.qualification_only){await save('qualification-result',{request,report,scope:'READ_ONLY_ADAPTER_QUALIFICATION_NO_SOURCE_REPOSITORY_APP_CHECK'});await seal();process.exit(0);}
  const scoped=await sourceToken(request.repository,request.command==='fix');
  try{
   if(request.command==='fix'&&report.repair?.status==='PATCH_PASSES_FROZEN_GUARDS_AND_REPOSITORY_GATE'){
    const snapshot=await get('snapshot'),patch=await get('patch');ensure(hash(admitLeanPatch(patch,snapshot.source))===report.repair.patched_sha256,'UNVERIFIED_PATCH');
    report.repair_pr=await createRepair(request,patch,publication,scoped.api);
   }
   await save('publication-result',await finishCheck(request,publication,report,scoped.api));
  }finally{await scoped.api('/installation/token',{method:'DELETE'});}await seal();
 }else throw Error('UNKNOWN_CONTROLLER_PHASE');
}catch(e){
 const reason=/^[A-Z0-9_]+$/.test(e.message)?e.message:'CONTROLLER_INCOMPLETE';await save('controller-error',{context,phase,reason});await outputs({ready:'false',revision:'false'});await seal();console.error(JSON.stringify({status:'UNKNOWN',phase,reason}));
 if(phase==='settle')process.exitCode=1;
}
async function createRepair(request,patch,publication,api){
 const root='/repos/'+request.repository,pr=await api(root+'/pulls/'+request.number);ensure(pr.state==='open'&&pr.head.sha===request.head_sha&&pr.base.sha===request.base_sha&&pr.head.repo.full_name===request.repository,'STALE_REPAIR');
 const name=`mathgraph/pr-${request.number}-${request.head_sha.slice(0,10)}-${patch.patched_sha256.slice(0,10)}`;
 const tree=await api(root+'/git/trees',{method:'POST',body:{base_tree:request.head_sha,tree:[{path:request.profile.path,mode:'100644',type:'blob',content:patch.content}]}});
 const commit=await api(root+'/git/commits',{method:'POST',body:{message:'fix: satisfy frozen independent ledger probes',tree:tree.sha,parents:[request.head_sha]}});
 try{await api(root+'/git/refs',{method:'POST',body:{ref:'refs/heads/'+name,sha:commit.sha}});}catch(e){
  if(e.message!=='GITHUB_HTTP_422')throw e;const existing=await api(root+'/git/ref/heads/'+name),c=await api(root+'/git/commits/'+existing.object.sha);ensure(c.tree.sha===tree.sha&&c.parents.length===1&&c.parents[0].sha===request.head_sha,'REPAIR_BRANCH_COLLISION');
 }
 const candidates=await api(root+'/pulls?state=open&head='+encodeURIComponent(request.repository.split('/')[0]+':'+name)+'&base='+encodeURIComponent(pr.head.ref));
 if(candidates.length){ensure(candidates.length===1&&candidates[0].draft===true,'REPAIR_PR_COLLISION');return candidates[0].html_url;}
 const fresh=await api(root+'/pulls/'+request.number);ensure(fresh.head.sha===request.head_sha&&fresh.base.sha===request.base_sha&&fresh.state==='open','STALE_REPAIR');
 const repair=await api(root+'/pulls',{method:'POST',body:{title:'Repair independently reproduced ledger probe failures',head:name,base:pr.head.ref,draft:true,body:`Candidate repair for #${request.number}, source ${request.head_sha}.\n\nThe model-generated patch passes the unchanged generated probes, protected original guards and repository gate in the recorded finite scope. Withdrawal reproduces the observed failures. Model-inferred requirements remain unverified; this is not full-library correctness or merge approval.\n\nEvidence: ${publication.run_url}`}});ensure(repair.draft===true&&repair.base.sha===request.head_sha,'REPAIR_READBACK_MISMATCH');return repair.html_url;
}
