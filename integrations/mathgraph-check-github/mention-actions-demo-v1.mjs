// Repository-local, opt-in Actions pilot. Only the fixed list-reversal demo is
// supported. The actual response author is github-actions[bot], not an App.
import {readFile,writeFile,mkdtemp,rm} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {tmpdir} from 'node:os';
import {pathToFileURL} from 'node:url';
import {openAIModel,reservationCents,parseCommand} from './mention-agent-v1.mjs';
import {brokenSource,repairedSource,nativeDemo,dockerRunner,demoPath,originalTarget} from './mention-native-demo-v1.mjs';
const repository='metalogiclabs/mathgraph',userId=32909488;
const policy={repositories:[repository],userIds:[userId],handle:'MathGraph',model:'gpt-6.1-sol',inputCentsPerMillion:500,outputCentsPerMillion:2000,maxOutputTokens:4096,maxInputBytes:8000,jobCapCents:25,totalCapCents:25};
const ensure=(ok,code)=>{if(!ok)throw Error(code);};
export function demoCommand(e,{attempt}={}){
 if(attempt!==1||e?.action!=='created'||e.repository?.full_name!==repository||e.sender?.id!==userId||e.sender.type!=='User'||e.comment?.user?.id!==userId||e.comment.user.type!=='User'||!e.issue?.pull_request||!Number.isSafeInteger(e.issue.number)||e.issue.number<1||!Number.isSafeInteger(e.comment.id)||e.comment.id<1)return null;
 return parseCommand(e.comment.body,'MathGraph');
}
export function demoComment({command,sha,native,runURL,repairURL,proposal}={}){
 const lines=['### MathGraph Check'];
 if(command==='check'&&native?.status==='CLAIM_NOT_ESTABLISHED')lines.push('**Proof compiles. The original claim is not established.**','The submitted theorem requires the conclusion as an assumption. Lean accepts that theorem; a consumer asking for the original claim rejects it.','| Check | Result |\n|---|---|\n| Submitted proof | Compiles |\n| Original claim | Not established by this proof |\n| Extra assumption | The conclusion itself |','**Next:** `@MathGraph -fix`');
 else if(native?.status==='ORIGINAL_TARGET_VERIFIED')lines.push(command==='fix'?'**Repair verified against the original claim.**':'**The original claim passes its native check.**','Lean accepted the theorem and its unchanged consumer, with no axioms.');
 else lines.push('**Verification is incomplete.**','No verified repair or mathematical conclusion is established.');
 if(repairURL)lines.push('**[Review the repair]('+repairURL+')**');
 else if(command==='fix'&&native?.status==='ORIGINAL_TARGET_VERIFIED')lines.push('The verified patch is available in this run’s artifact. Opening a repair PR was not confirmed.');
 lines.push('<details><summary>Evidence and scope</summary>\n\nRevision: `'+String(sha??'unbound')+'`\n\n'+(runURL?'[Native verification run]('+runURL+')\n\n':'')+'Controlled demo: list reversal. The intended theorem is fixed by the trusted adapter. This is not an upstream defect or general paper-to-proof certification. Model findings are advisory.\n\nExecuted via GitHub Actions.\n\n</details>');
 return lines.join('\n\n');
}
export async function createVerifiedRepair({api,root,pr,sha,sourceFile,repaired,event,runURL}){
 const fresh=async()=>{const live=await api(root+'/pulls/'+event.issue.number);ensure(live.state==='open'&&live.head?.sha===sha,'SOURCE_MOVED');};
 await fresh();
 const branch='mathgraph/repair-'+event.issue.number+'-'+sha.slice(0,10)+'-'+event.comment.id;
 await api(root+'/git/refs',{method:'POST',body:{ref:'refs/heads/'+branch,sha}});
 await api(root+'/contents/'+demoPath,{method:'PUT',body:{branch,sha:sourceFile.sha,message:'fix: prove list reversal length without assuming the conclusion',content:Buffer.from(repaired).toString('base64')}});
 await fresh();
 const opened=await api(root+'/pulls',{method:'POST',body:{head:branch,base:pr.head.ref,title:'Prove the original list-reversal claim without an extra assumption',body:'Removes the conclusion supplied as a hypothesis. Lean 4.28.0 checked the unchanged original target and its consumer with no axioms. Controlled demonstration; no general semantic assurance.\n\nNative verification: '+runURL,draft:true}});
 ensure(Number.isSafeInteger(opened.number)&&typeof opened.html_url==='string','REPAIR_PR_NOT_CONFIRMED');
 try{await fresh();}catch(e){const closed=await api(root+'/pulls/'+opened.number,{method:'PATCH',body:{state:'closed'}});ensure(closed.state==='closed','STALE_REPAIR_WITHDRAWAL_UNCONFIRMED');throw e;}
 return {url:opened.html_url,number:opened.number};
}
async function repairProof(apiKey,source){
 ensure(typeof apiKey==='string'&&apiKey.trim(),'OPENAI_API_KEY_REQUIRED');
 const r=await fetch('https://api.openai.com/v1/responses',{method:'POST',redirect:'error',headers:{Authorization:'Bearer '+apiKey,'Content-Type':'application/json'},signal:AbortSignal.timeout(120000),body:JSON.stringify({model:policy.model,store:false,max_output_tokens:4096,instructions:'Return a proof body for the ORIGINAL theorem. Do not assume the conclusion or change the statement. Select a supported proof constructor. The native checker, not your answer, determines acceptance.',input:JSON.stringify({original_target:originalTarget,submitted_source:source,supported_proof_constructors:['by simp','by simpa','by exact List.length_reverse xs']}),text:{format:{type:'json_schema',name:'mathgraph_repair',strict:true,schema:{type:'object',properties:{proof_body:{type:'string',enum:['by simp','by simpa','by exact List.length_reverse xs']}},required:['proof_body'],additionalProperties:false}}}})});
 ensure(r.ok,'MODEL_REQUEST_FAILED');const d=await r.json();ensure(d.status==='completed'&&Number.isSafeInteger(d.usage?.input_tokens)&&d.usage.input_tokens>=0&&d.usage.input_tokens<=policy.maxInputBytes+8192&&Number.isSafeInteger(d.usage?.output_tokens)&&d.usage.output_tokens>=0&&d.usage.output_tokens<=4096,'MODEL_RESPONSE_INCOMPLETE');
 const texts=(d.output??[]).filter(x=>x.type==='message').flatMap(x=>x.content??[]).filter(x=>x.type==='output_text');ensure(texts.length===1&&texts[0].text.length<1000,'INVALID_REPAIR_OUTPUT');const p=JSON.parse(texts[0].text);ensure(Object.keys(p).length===1,'INVALID_REPAIR_OUTPUT');return repairedSource(p.proof_body);
}
async function main(){
 const event=JSON.parse(await readFile(process.env.GITHUB_EVENT_PATH,'utf8'));const command=demoCommand(event,{attempt:Number(process.env.GITHUB_RUN_ATTEMPT)});if(!command)return;
 ensure(process.env.GITHUB_REPOSITORY===repository&&process.env.GITHUB_EVENT_NAME==='issue_comment','INVALID_ACTION_CONTEXT');
 ensure(reservationCents(policy)<=25,'BUDGET_CONFIGURATION_INVALID');
 const token=process.env.GITHUB_TOKEN;ensure(typeof token==='string'&&token.length>10,'GITHUB_TOKEN_REQUIRED');
 const root='/repos/'+repository;
 const api=async(path,{method='GET',body}={})=>{
  ensure(path.startsWith(root+'/'),'API_SCOPE_REFUSED');const r=await fetch('https://api.github.com'+path,{method,redirect:'error',headers:{Authorization:'Bearer '+token,Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(20000)});ensure(r.ok,'GITHUB_HTTP_'+r.status);return r.status===204?{}:r.json();
 };
 const runId=Number(process.env.GITHUB_RUN_ID);ensure(Number.isSafeInteger(runId)&&runId>0,'INVALID_RUN_ID');
 const current=await api(root+'/actions/runs/'+runId);ensure(current.event==='issue_comment'&&current.run_attempt===1,'REPLAYED_ACTION_REFUSED');
 const history=await api(root+'/actions/workflows/'+current.workflow_id+'/runs?event=issue_comment&per_page=100');ensure(Array.isArray(history.workflow_runs)&&history.total_count===history.workflow_runs.length&&history.workflow_runs.filter(r=>r.id<=runId).length<=20,'PILOT_TOTAL_BUDGET_EXHAUSTED');
 const authentic=await api(root+'/issues/comments/'+event.comment.id);ensure(authentic.user?.id===userId&&authentic.body===event.comment.body&&authentic.issue_url==='https://api.github.com'+root+'/issues/'+event.issue.number,'COMMENT_IDENTITY_MOVED');
 const pr=await api(root+'/pulls/'+event.issue.number);const sha=pr.head?.sha;ensure(pr.state==='open'&&/^[a-f0-9]{40}$/.test(sha??'')&&pr.head.repo?.full_name===repository&&pr.base.repo?.full_name===repository,'FIRST_PARTY_SOURCE_REQUIRED');
 const sourceFile=await api(root+'/contents/'+demoPath+'?ref='+sha);ensure(sourceFile.encoding==='base64'&&sourceFile.size<=4000,'UNSUPPORTED_DEMO_FILE');const source=Buffer.from(sourceFile.content,'base64').toString('utf8');
 ensure(source===brokenSource||['by simp','by simpa','by exact List.length_reverse xs'].some(p=>repairedSource(p)===source),'UNSUPPORTED_DEMO_SOURCE');
 const marker='<!-- mathgraph-actions-demo-v1:'+event.comment.id+' -->';const comments=await api(root+'/issues/'+event.issue.number+'/comments?per_page=100');ensure(Array.isArray(comments)&&comments.length<100,'COMMENT_WINDOW_INCOMPLETE');if(comments.some(c=>c.user?.login==='github-actions[bot]'&&c.body?.startsWith(marker)))return;
 const comment=await api(root+'/issues/'+event.issue.number+'/comments',{method:'POST',body:{body:marker+'\n### MathGraph Check\nChecking the proof against the original claim…'}});ensure(Number.isSafeInteger(comment.id),'COMMENT_NOT_CREATED');
 const runURL='https://github.com/'+repository+'/actions/runs/'+runId;const work=await mkdtemp(join(tmpdir(),'mathgraph-native-'));let receipt,repairURL=null,repairNumber=null,proposal=null,modelCalls=0;
 try{
  const run=await dockerRunner(work);
  const sanity=await run('Sanity','import Std\nexample : 1 + 1 = 2 := by decide\n');const negative=await run('Negative','import Std\nexample : False := by trivial\n');ensure(sanity.code===0&&negative.code===1,'NATIVE_CONTROLS_FAILED');
  receipt=await nativeDemo({source,run});
  if(command==='fix'&&receipt.status==='CLAIM_NOT_ESTABLISHED'){
   modelCalls++;const repaired=await repairProof(process.env.OPENAI_API_KEY,source);receipt=await nativeDemo({source:repaired,run});ensure(receipt.status==='ORIGINAL_TARGET_VERIFIED','REPAIR_NOT_VERIFIED');
   await writeFile(join(process.env.RUNNER_TEMP,'mathgraph-verified-repair.lean'),repaired,{mode:0o600});
   try{
    const repair=await createVerifiedRepair({api,root,pr,sha,sourceFile,repaired,event,runURL});repairURL=repair.url;repairNumber=repair.number;
   }catch(e){if(e.message==='SOURCE_MOVED'||e.message==='STALE_REPAIR_WITHDRAWAL_UNCONFIRMED')throw e;repairURL=null;}
  }else if(command==='check'){
   const snapshot={repository,number:event.issue.number,sha,files:[{filename:demoPath,patch:source.split('\n').map(l=>'+'+l).join('\n')}],runs:[],files_visibility:'COMPLETE',ci_visibility:'COMPLETE'};
   modelCalls++;proposal=await openAIModel({apiKey:process.env.OPENAI_API_KEY,policy})({snapshot,analysis:{native_demo:receipt}});
  }
  const fresh=await api(root+'/pulls/'+event.issue.number);ensure(fresh.head.sha===sha&&fresh.state==='open','SOURCE_MOVED');
  await writeFile(join(process.env.RUNNER_TEMP,'mathgraph-native-receipt.json'),JSON.stringify({schema:'mathgraph.native-list-demo.v1',command,repository,pr:event.issue.number,source_head:sha,run_id:runId,lean:'4.28.0',...receipt,repair_pr:repairURL,model_assessment:proposal},null,2),{mode:0o600});
  await api(root+'/issues/comments/'+comment.id,{method:'PATCH',body:{body:marker+'\n'+demoComment({command,sha,native:receipt,runURL,repairURL,proposal})}});
  console.log(JSON.stringify({status:receipt.status,command,source_head:sha,run_id:runId,repair_pr:repairURL,api_calls:modelCalls,scope:'FIXED_LIST_REVERSAL_DEMO_ONLY'}));
 }catch(e){if(repairNumber){const closed=await api(root+'/pulls/'+repairNumber,{method:'PATCH',body:{state:'closed'}});ensure(closed.state==='closed','STALE_REPAIR_WITHDRAWAL_UNCONFIRMED');}
 await api(root+'/issues/comments/'+comment.id,{method:'PATCH',body:{body:marker+'\n### MathGraph Check\n**Verification is incomplete.**\n\nNo result is promoted. [Inspect this run]('+runURL+').'}});throw e;}
 finally{await rm(work,{recursive:true,force:true});}
}
if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){try{await main();}catch(e){console.error(/^[-A-Z0-9_]+$/.test(e.message)?e.message:'DEMO_CHECK_INCOMPLETE');process.exitCode=1;}}
