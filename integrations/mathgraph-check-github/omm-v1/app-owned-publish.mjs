// One explicitly owned Artin cohort only. The publish job receives an App
// installation token, never a Lean executable or source from an arbitrary PR.
import {createHash} from 'node:crypto';
import {readFile,writeFile} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {artinStrongSource,artinRepairSource,bindPublishedArtin} from '../mention-artin-control-v1.mjs';
import {assessOmmClaim} from './claim-admission.mjs';
import {buildOmmAppCheckPreview} from './app-check.mjs';

const SHA40=/^[a-f0-9]{40}$/;
const digest=s=>createHash('sha256').update(s).digest('hex');
const REPO='metalogiclabs/mathgraph',APP_ID=5308912;
const NAME='MathGraph Check / OMM claim (advisory)';
const PROFILES={
  239:{head:'2f6aaba0d71f1c0b4c0db58618a8981ccd59dc17',base:'dfd87d1e921953badedcfae21ade76bb38f5c04a',source:artinStrongSource,expected:'NOT_ESTABLISHED_IN_THIS_REPLAY'},
  240:{head:'06f09cd5aaa866365ceb6540cd06389bd37a727c',base:'2f6aaba0d71f1c0b4c0db58618a8981ccd59dc17',source:artinRepairSource,expected:'CONSUMER_ACCEPTED'}
};
const artifactNames=['claim-contract.json','native-receipt.json','assessment.json','native-trace.json','report.md','app-check-preview.json'];
const requirePin=(condition,why)=>{if(!condition)throw Error(why);};

/** Reconstruct the Check payload independently of PR-authored claims and the saved preview. */
export async function loadFrozenArtinPreview({directory,number,runId}={}){
 const p=PROFILES[number];
 if(!p||typeof directory!=='string'||!directory.startsWith('/')||
  !/^[1-9][0-9]*$/.test(String(runId??'')))throw Error('UNREGISTERED_RELEASE_INPUT');
 const dir=resolve(directory);
 const read=async name=>{const bytes=await readFile(join(dir,name),'utf8');
  if(bytes.length>2_000_000)throw Error('ARTIFACT_TOO_LARGE');return bytes;};
 const [requestRaw,source,published,manifestRaw]=await Promise.all([
  read('request.json'),read('candidate.lean.txt'),read('published-exercise.lean.txt'),read('output/manifest.json')]);
 const request=JSON.parse(requestRaw),manifest=JSON.parse(manifestRaw);
 const original=bindPublishedArtin(published);
 requirePin(request.schema==='mathgraph.omm.request.v1'&&request.repository===REPO&&
  request.number===number&&request.command==='check'&&request.head_sha===p.head&&
  request.base_sha===p.base&&request.candidate_source_sha256===digest(source)&&
  source===p.source,'FROZEN_SOURCE_IDENTITY_MISMATCH');
 const runUrl=`https://github.com/${REPO}/actions/runs/${runId}`;
 requirePin(manifest.schema==='mathgraph.omm.artin-qualification-manifest.v1'&&
  manifest.repository===REPO&&manifest.number===number&&manifest.source_head===p.head&&
  manifest.base_sha===p.base&&manifest.candidate_source_sha256===digest(source)&&
  manifest.published_source_sha256===original.source_sha256&&manifest.run_url===runUrl&&
  manifest.release==='QUALIFICATION_ONLY'&&manifest.evidence_warrant==='UNKNOWN',
  'ARTIFACT_PIN_MISMATCH');
 const actualNames=Object.keys(manifest.artifact_sha256??{});
 requirePin(actualNames.length===artifactNames.length&&
  actualNames.slice().sort().join('|')===artifactNames.slice().sort().join('|'),
  'ARTIFACT_PIN_MISMATCH');
 const artifactPairs=await Promise.all(artifactNames.map(async name=>[name,await read('output/'+name)]));
 for(const [name,bytes] of artifactPairs)requirePin(manifest.artifact_sha256[name]===digest(bytes),'ARTIFACT_PIN_MISMATCH');
 const files=Object.fromEntries(artifactPairs);
 requirePin(manifest.claim_contract_sha256===digest(files['claim-contract.json'])&&
  manifest.native_receipt_sha256===digest(files['native-receipt.json']),
  'ARTIFACT_PIN_MISMATCH');
 const inputs={request,contractBytes:files['claim-contract.json'],
  expectedContractSha256:manifest.claim_contract_sha256,receiptBytes:files['native-receipt.json'],
  expectedReceiptSha256:manifest.native_receipt_sha256};
 const assessment=assessOmmClaim(inputs);
 requirePin(assessment.status==='NATIVE_RECEIPT_BOUND'&&
  assessment.original_target===p.expected&&assessment.intent_fidelity==='UNKNOWN'&&
  assessment.evidence_warrant==='UNKNOWN'&&
  JSON.stringify(assessment)===files['assessment.json'],'NATIVE_RECEIPT_REQUALIFICATION_FAILED');
 const trace=JSON.parse(files['native-trace.json']);
 const receipt=JSON.parse(files['native-receipt.json']);
 requirePin(Array.isArray(trace)&&trace.length===receipt.native.trace.length&&
  trace.every((e,i)=>e.unit===receipt.native.trace[i].unit&&
   e.exit_code===receipt.native.trace[i].exit_code)&&
  trace[0].source_sha256===digest(source),'NATIVE_TRACE_DIVERGED');
 const preview=buildOmmAppCheckPreview({...inputs,expectedHeadSha:p.head,runUrl});
 requirePin(JSON.stringify(preview.payload)===files['app-check-preview.json']&&
  preview.payload.conclusion==='neutral','APP_PREVIEW_REQUALIFICATION_FAILED');
 return {request,assessment,payload:preview.payload};
}

/** Explicit first-party exact-head transport; `write` defaults to false. */
export async function reconcileOwnedOmmCheck({number,baseSha,payload,api,write=false}={}){
 const p=PROFILES[number];
 const external=`mathgraph-omm-claim-v1:${REPO}:${number}:${p?.head??''}`;
 if(!p||baseSha!==p.base||typeof api!=='function'||
  payload?.name!==NAME||payload.head_sha!==p.head||!SHA40.test(payload.head_sha)||
  payload.external_id!==external||payload.status!=='completed'||
  payload.conclusion!=='neutral'||
  typeof payload.output?.summary!=='string'||
  !payload.output.summary.includes('Human mathematical intent | UNKNOWN')||
  !payload.output.summary.includes('Independent evidence warrant | UNKNOWN'))
  throw Error('UNQUALIFIED_OMM_APP_PAYLOAD');
 const root='/repos/'+REPO;
 const exactHead=async()=>{
  const observed=await api(root+'/pulls/'+number);
  if(observed.number!==number||observed.state!=='open'||
    observed.head?.sha!==p.head||observed.base?.sha!==p.base||
    observed.head?.repo?.full_name!==REPO||observed.base?.repo?.full_name!==REPO)
   throw Error('STALE_PR_HEAD');
 };
 await exactHead();
 const list=await api(root+'/commits/'+p.head+'/check-runs?check_name='+
  encodeURIComponent(NAME)+'&filter=all&per_page=100');
 if(!Array.isArray(list?.check_runs)||!Number.isSafeInteger(list.total_count)||
  list.total_count>100||list.total_count>list.check_runs.length)
  throw Error('APP_CHECK_RECONCILIATION_INCOMPLETE');
 const own=list.check_runs.filter(x=>x.app?.id===APP_ID&&x.name===NAME&&x.external_id===external);
 if(own.length>1)throw Error('DUPLICATE_OWNED_OMM_CHECKS');
 if(own.length===1&&(!Number.isSafeInteger(own[0].id)||own[0].head_sha!==p.head))
  throw Error('OWNED_OMM_CHECK_IDENTITY_MISMATCH');
 await exactHead();
 if(!write)return {mode:'PREVIEW',existing:own.length};
 let result,mode;
 if(own.length===1){
  const old=own[0];
  if(old.status==='completed'&&old.conclusion==='neutral'&&old.output?.summary===payload.output.summary){
   result=old;mode='UNCHANGED';
  }else{
   result=await api(root+'/check-runs/'+old.id,{method:'PATCH',body:{status:'completed',
    conclusion:'neutral',external_id:external,output:payload.output}});mode='UPDATED';
  }
 }else{
  result=await api(root+'/check-runs',{method:'POST',body:payload});mode='CREATED';
 }
 if(!Number.isSafeInteger(result?.id))throw Error('APP_WRITE_IDENTITY_MISMATCH');
 const verified=await api(root+'/check-runs/'+result.id);
 if(verified?.app?.id!==APP_ID||verified.head_sha!==p.head||
   verified.name!==NAME||verified.external_id!==external||verified.status!=='completed'||
   verified.conclusion!=='neutral'||verified.output?.summary!==payload.output.summary)
  throw Error('APP_INDEPENDENT_READBACK_MISMATCH');
 await exactHead();
 return {mode,check_run_id:result.id,app_id:APP_ID,repository:REPO,number,head_sha:p.head};
}

if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
 try{
  const number=Number(process.argv[2]),directory=process.argv[3],runId=process.env.GITHUB_RUN_ID;
  const token=process.env.MATHGRAPH_APP_INSTALLATION_TOKEN;
  if(process.argv.length!==4||process.env.GITHUB_REPOSITORY!==REPO||
    !runId||!token||token.length<10)throw Error('QUALIFICATION_RELEASE_CONTEXT_MISSING');
  const {request,payload}=await loadFrozenArtinPreview({number,directory,runId});
  const api=async(path,{method='GET',body}={})=>{
   if(!path.startsWith('/repos/'+REPO+'/'))throw Error('APP_API_SURFACE_REFUSED');
   const response=await fetch('https://api.github.com'+path,{method,
    headers:{Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28',
     Authorization:'Bearer '+token,'Content-Type':'application/json'},
    body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(20000)});
   if(!response.ok)throw Error('GITHUB_APP_HTTP_'+response.status);
   return response.json();
  };
  const result=await reconcileOwnedOmmCheck({number,baseSha:request.base_sha,payload,api,write:true});
  await writeFile(join(resolve(directory),'output','app-publish-receipt.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
  console.log('OMM_OWNED_APP_CHECK_READBACK '+JSON.stringify(result));
 }catch(e){console.error('OMM_OWNED_APP_CHECK_UNKNOWN:'+String(e.message));process.exitCode=1;}
}
