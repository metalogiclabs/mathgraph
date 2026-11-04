// Trusted orchestration; never imports, builds or executes subject source.
import {readFile,writeFile,mkdir,readdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {requestJSON,reservationCents} from './model.mjs';
import {subjectPolicy} from './policy.mjs';
import {admitPlan,admitPatch,assessProbe,assessProbeDelta,assessRepair,compareProtectedSuites} from './contracts.mjs';
const phase=process.argv[2],dir=process.argv[3]??'investigation';
const config=subjectPolicy(process.env);
const digest=x=>createHash('sha256').update(typeof x==='string'?x:JSON.stringify(x)).digest('hex');
const ensure=(x,code)=>{if(!x)throw Error(code);};
const context={verifier_sha:process.env.GITHUB_SHA,run_id:Number(process.env.GITHUB_RUN_ID),attempt:Number(process.env.GITHUB_RUN_ATTEMPT)};
ensure(/^[a-f0-9]{40}$/.test(context.verifier_sha??'')&&Number.isSafeInteger(context.run_id)&&context.attempt===1,'INVALID_WORKFLOW_CONTEXT');
const save=async(name,data)=>writeFile(`${dir}/${name}.json`,JSON.stringify(data,null,2)+'\n');
const load=async name=>JSON.parse(await readFile(`${dir}/${name}.json`,'utf8'));
async function seal(){const files=(await readdir(dir)).filter(x=>x.endsWith('.json')&&x!=='manifest.json').sort();const hashes={};for(const f of files)hashes[f]=digest(await readFile(`${dir}/${f}`,'utf8'));await save('manifest',{context,hashes});}
async function verify(){const m=await load('manifest');ensure(JSON.stringify(m.context)===JSON.stringify(context),'STALE_WORKFLOW_ARTIFACT');for(const [f,h]of Object.entries(m.hashes)){ensure(/^[a-z][a-z0-9_-]*\.json$/.test(f)&&digest(await readFile(`${dir}/${f}`,'utf8'))===h,'ARTIFACT_BYTES_CHANGED');}return m;}
async function api(path){ensure(path.startsWith(`/repos/${config.source_repository}/`),'READ_SCOPE_REFUSED');const r=await fetch('https://api.github.com'+path,{headers:{Accept:'application/vnd.github+json',...(process.env.GITHUB_TOKEN?{Authorization:`Bearer ${process.env.GITHUB_TOKEN}`}:{})},signal:AbortSignal.timeout(20000)});ensure(r.ok,'SOURCE_HTTP_'+r.status);return r.json();}
async function raw(path,sha){ensure(/^[a-f0-9]{40}$/.test(sha)&&/^[A-Za-z0-9_./-]+$/.test(path)&&!path.split('/').includes('..'),'INVALID_SOURCE_PATH');const r=await fetch(`https://raw.githubusercontent.com/${config.source_repository}/${sha}/${path}`,{signal:AbortSignal.timeout(20000)});if(r.status===404)return null;ensure(r.ok,'SOURCE_BYTES_HTTP_'+r.status);const text=await r.text();ensure(Buffer.byteLength(text)<=200000,'SOURCE_FILE_LIMIT');return text;}
await mkdir(dir,{recursive:true});
try {
if(phase==='prepare'){
 ensure(reservationCents()*2<=100,'BUDGET_POLICY_INVALID');
 // This acquisition happens only after the investigator implementation is frozen.
 const prs=config.requested_pr?[await api('/repos/'+config.source_repository+'/pulls/'+config.requested_pr)]:await api('/repos/'+config.source_repository+'/pulls?state=open&sort=created&direction=desc&per_page=10');
 let snapshot;
 for(const pr of prs.slice(0,config.max_prs)){
  if(!config.requested_pr&&config.source_repository!==config.repository&&(pr.user?.login==='heathsanchez'||pr.draft))continue;
  const changed=await api(`/repos/${config.source_repository}/pulls/${pr.number}/files?per_page=100`);
  if(changed.length>=100)continue;
  const selected=changed.filter(f=>f.status==='modified'&&f.filename.startsWith(config.implementation_prefix)&&f.filename.endsWith('.py')).slice(0,2);
  if(!selected.length)continue;
  const files=[];let bytes=0;
  for(const f of selected){const head=await raw(f.filename,pr.head.sha),base=await raw(f.filename,pr.base.sha);if(head===null||base===null||Buffer.byteLength(head)>24000||Buffer.byteLength(base)>24000)continue;if(bytes+Buffer.byteLength(head)+Buffer.byteLength(base)>42000)continue;bytes+=Buffer.byteLength(head)+Buffer.byteLength(base);files.push({path:f.filename,head,base,head_sha256:digest(head),base_sha256:digest(base),patch:String(f.patch??'').slice(0,6000)});}
  if(!files.length)continue;
  const tests=[];for(const f of changed.filter(f=>f.filename.startsWith('tests/')&&f.filename.endsWith('.py')).slice(0,2)){const text=await raw(f.filename,pr.head.sha);if(text&&Buffer.byteLength(text)<=6000)tests.push({path:f.filename,content:text});}
  snapshot={...config,pr:pr.number,url:pr.html_url,base_sha:pr.base.sha,head_sha:pr.head.sha,claim:{title:String(pr.title).slice(0,500),body:String(pr.body??'').slice(0,2500),authority:'AUTHOR_TEXT_NOT_VERIFIED_REQUIREMENT'},files,existing_test_context:tests,changed_file_count:changed.length,source_window:'At most two implementation files <=24KB each; combined base/head <=42KB; up to two changed test files <=6KB each',selection:'Newest-created open non-draft non-founder PR with eligible modified Python source; no bug labels acquired'};break;
 }
 if(!snapshot){await save('state',{context,state:'UNKNOWN',reason:'NO_ELIGIBLE_PYTHON_PR'});await seal();process.exit(0);}
 while(Buffer.byteLength(JSON.stringify({snapshot}))>62000&&snapshot.existing_test_context.length)snapshot.existing_test_context.pop();
 while(Buffer.byteLength(JSON.stringify({snapshot}))>62000&&snapshot.files.length>1)snapshot.files.pop();
 ensure(Buffer.byteLength(JSON.stringify({snapshot}))<=62000,'SOURCE_PACKET_LIMIT');
 await save('snapshot',snapshot);
 const response=await requestJSON({apiKey:process.env.OPENAI_API_KEY,stage:'investigate',packet:{snapshot}});
 await save('model-investigate',response);const plan=admitPlan(response.proposal,snapshot);await save('plan',plan);
 await save('state',{context,state:'PROBES_PROPOSED',model_calls:1,reserved_cents:reservationCents(),test_digest:digest(plan.tests)});await seal();
}else if(phase==='repair'){
 await verify();const state=await load('state');if(state.state!=='PROBES_PROPOSED'){await seal();process.exit(0);}
 const snapshot=await load('snapshot'),plan=admitPlan(await load('plan'),snapshot),native=await load('native');
 ensure(native.verifier_sha===context.verifier_sha&&native.head_sha===snapshot.head_sha&&native.test_digest===state.test_digest,'NATIVE_RECEIPT_MISMATCH');
 const deltas=plan.tests.map(t=>({id:t.id,...assessProbeDelta({
   base:native.arms?.base?.probes?.find(p=>p.id===t.id),
   head:native.arms?.head?.probes?.find(p=>p.id===t.id)
  },{baseSha:snapshot.base_sha,headSha:snapshot.head_sha,testDigest:state.test_digest,testFileDigest:digest(t.code),requireReviewedSourceUse:true})}));
 const failing=deltas.some(d=>d.status==='HEAD_ONLY_FAILURE');
 if(!failing){await save('repair-state',{state:deltas.some(d=>d.status==='UNKNOWN')?'ATTRIBUTION_UNKNOWN':'NO_HEAD_ONLY_FAILURE',model_calls:0,deltas});await seal();process.exit(0);}
 const response=await requestJSON({apiKey:process.env.OPENAI_API_KEY,stage:'repair',packet:{subject:{...snapshot,files:snapshot.files.map(({base,patch,...f})=>f),existing_test_context:[]},frozen_probes:plan.tests,native:{runtime:native.runtime,arms:Object.fromEntries(Object.entries(native.arms).map(([k,v])=>[k,{probes:v.probes.map(({cases,...p})=>p),protected:{exit_code:v.protected.exit_code,tests:v.protected.tests,failures:v.protected.failures,errors:v.protected.errors,timeout:v.protected.timeout}}]))}}});
 await save('model-repair',response);
 if(!response.proposal.files?.length){await save('repair-state',{state:'NO_CANDIDATE_PATCH',model_calls:1});await seal();process.exit(0);}
 const patch=admitPatch(response.proposal,snapshot);await save('patch',patch);await save('repair-state',{state:'PATCH_PROPOSED',model_calls:1,patch_digest:digest(patch)});await seal();
}else if(phase==='assess'){
 await verify();const state=await load('state');let report;
 if(state.state!=='PROBES_PROPOSED'){
 let snapshot;try{snapshot=await load('snapshot');}catch{}
 report={status:'UNKNOWN',reason:state.reason,stage:state.stage,context,subject:snapshot?{repository:snapshot.repository,source_repository:snapshot.source_repository,pr:snapshot.pr,base_sha:snapshot.base_sha,head_sha:snapshot.head_sha}:undefined};
 }
 else{
 const snapshot=await load('snapshot'),plan=admitPlan(await load('plan'),snapshot),native=await load('native');
 ensure(digest(plan.tests)===state.test_digest&&native.verifier_sha===context.verifier_sha&&native.head_sha===snapshot.head_sha&&native.test_digest===state.test_digest,'NATIVE_RECEIPT_MISMATCH');
 const expectedIds=plan.tests.map(t=>t.id).sort();
 const exactProbes=arm=>Array.isArray(arm?.probes)&&JSON.stringify(arm.probes.map(p=>p.id).sort())===JSON.stringify(expectedIds);
 ensure(exactProbes(native.arms?.base)&&exactProbes(native.arms?.head),'INCOMPLETE_PROBE_SET');
 const rows=plan.tests.map(t=>{const head=native.arms.head.probes.find(x=>x.id===t.id),base=native.arms.base.probes.find(x=>x.id===t.id);const testFileDigest=digest(t.code),requireReviewedSourceUse=true;return {id:t.id,hypothesis:t.hypothesis,contract:t.contract,head:assessProbe(head,{subjectSha:snapshot.head_sha,testDigest:state.test_digest,testFileDigest,requireReviewedSourceUse}),base:assessProbe(base,{subjectSha:snapshot.base_sha,testDigest:state.test_digest,testFileDigest,requireReviewedSourceUse}),delta:assessProbeDelta({base,head},{baseSha:snapshot.base_sha,headSha:snapshot.head_sha,testDigest:state.test_digest,testFileDigest,requireReviewedSourceUse})};});
 let repair={status:'NOT_PROPOSED'};
 let rs={state:'NOT_REQUESTED',model_calls:0};
 try{rs=await load('repair-state');}catch(e){if(e.code!=='ENOENT')throw e;}
 if(rs.state==='PATCH_PROPOSED'){
 const patch=admitPatch(await load('patch'),snapshot),fixed=await load('native-repair');
 ensure(digest(patch)===rs.patch_digest&&fixed.patch_digest===rs.patch_digest&&fixed.head_sha===snapshot.head_sha&&fixed.test_digest===state.test_digest&&fixed.verifier_sha===context.verifier_sha,'REPAIR_RECEIPT_MISMATCH');
 ensure(exactProbes(fixed.arm)&&exactProbes(fixed.original_arm),'INCOMPLETE_REPAIR_PROBE_SET');
 const results=plan.tests.map(t=>assessRepair({original:fixed.original_arm.probes.find(p=>p.id===t.id),fixed:fixed.arm.probes.find(p=>p.id===t.id),protectedBefore:fixed.original_arm.protected,protectedAfter:fixed.arm.protected},{subjectSha:snapshot.head_sha,testDigest:state.test_digest,testFileDigest:digest(t.code),requireReviewedSourceUse:true}));
 // All probes must pass after repair; at least one original failure must be fixed.
 const allFixed=plan.tests.every(t=>assessProbe(fixed.arm.probes.find(p=>p.id===t.id),{subjectSha:snapshot.head_sha,testDigest:state.test_digest,testFileDigest:digest(t.code),requireReviewedSourceUse:true}).execution==='PROBE_PASSED');
 const attributable=rows.some(r=>r.delta.status==='HEAD_ONLY_FAILURE');
 repair={status:attributable&&allFixed&&results.some(r=>r.status==='REPAIR_VERIFIED_FOR_FROZEN_TESTS')?'REPAIR_VERIFIED_FOR_FROZEN_TESTS':'UNKNOWN',results,patch_digest:rs.patch_digest};
 }else repair={status:rs.state,model_calls:rs.model_calls??null};
 const protectedSuites=Object.fromEntries(['base','head'].map(arm=>{const p=native.arms[arm].protected;return [arm,{...assessProbe(p,{subjectSha:arm==='head'?snapshot.head_sha:snapshot.base_sha,testDigest:p.test_digest,requireAssertions:false}),tests:p.tests,failures:p.failures,errors:p.errors,skipped:p.skipped,exit_code:p.exit_code,timeout:p.timeout}];}));
 const protectedComparison=compareProtectedSuites({base:native.arms.base.protected,head:native.arms.head.protected},{baseSha:snapshot.base_sha,headSha:snapshot.head_sha});
 const protectedIncomplete=Object.values(protectedSuites).some(p=>p.execution!=='PROBE_PASSED');
 const counts={head_failures:rows.filter(r=>r.head.execution==='CANDIDATE_FAILURE_REPRODUCED').length,base_failures:rows.filter(r=>r.base.execution==='CANDIDATE_FAILURE_REPRODUCED').length,head_unknowns:rows.filter(r=>r.head.execution==='UNKNOWN').length,head_only_failures:rows.filter(r=>r.delta.status==='HEAD_ONLY_FAILURE').length,shared_failures:rows.filter(r=>r.delta.status==='SHARED_FAILURE').length,attribution_unknowns:rows.filter(r=>r.delta.status==='UNKNOWN').length};
 report={context,subject:{repository:snapshot.repository,source_repository:snapshot.source_repository,pr:snapshot.pr,base_sha:snapshot.base_sha,head_sha:snapshot.head_sha},status:counts.head_only_failures?'HEAD_ONLY_FAILURE_CANDIDATE':counts.attribution_unknowns||counts.head_unknowns||protectedIncomplete?'UNKNOWN':counts.shared_failures?'SHARED_FAILURE_NOT_ATTRIBUTED':'NO_COUNTEREXAMPLE_IN_GENERATED_PROBES',counts,protected_suites:protectedSuites,protected_comparison:protectedComparison,probes:rows,repair,meaning:'UNVERIFIED',permission:'ADVISORY_ONLY',boundary:'AI-generated finite matched base/head probes, independently executed. A repair attempt requires base-pass/head-assertion-fail, identical frozen case identities and observed use of the reviewed Python source (executed lines or exact-file imported export reads in reached assertions). The protected comparison is observational only and existing failures do not become green. This does not independently certify the model-selected requirement or exclude nondeterminism. No automatic merge or general correctness claim.'};
 }
 await save('assessment',report);console.log(JSON.stringify(report));await seal();
}else throw Error('UNKNOWN_PHASE');

} catch(e) {
 const reason=/^[A-Z0-9_]+$/.test(e.message)?e.message:'STAGE_EXECUTION_INCOMPLETE';
 await save('stage-error',{context,stage:phase,reason});
 await save('state',{context,state:'UNKNOWN',stage:phase,reason});
 await seal();console.error(JSON.stringify({status:'UNKNOWN',stage:phase,reason}));
}
