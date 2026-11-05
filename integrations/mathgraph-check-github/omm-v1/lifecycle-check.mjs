// First-party OMM App-transport lifecycle probe. This intentionally does NOT
// admit a mathematical claim or execute Lean. It independently tests that a
// registered App's neutral, UNKNOWN observation is bound to one live PR SHA
// and that a predecessor is explicitly superseded after an owned push.
import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';

const REPO='metalogiclabs/mathgraph';
const BRANCH='feature/check-omm-claim-bridge-v1-20261105';
const NUMBER=270,APP_ID=5308912;
const NAME='MathGraph Check / OMM intake (advisory)';
const SHA40=/^[a-f0-9]{40}$/;
const RUN_URL=/^https:\/\/github\.com\/metalogiclabs\/mathgraph\/actions\/runs\/[1-9][0-9]*$/;
const assert=(x,reason)=>{if(!x)throw Error(reason);};
const root='/repos/'+REPO;
const external=head=>`mathgraph-omm-intake-v1:${REPO}:${NUMBER}:${head}`;
const marker=head=>`<!-- mathgraph-omm-superseded:${head} -->`;

export function buildOmmIntakeCheck({head,runUrl}={}){
 assert(SHA40.test(head??'')&&RUN_URL.test(runUrl??''),'INVALID_OMM_LIFECYCLE_SOURCE');
 return {name:NAME,head_sha:head,external_id:external(head),status:'completed',conclusion:'neutral',
  output:{title:'OMM claim intake: evidence not admitted (UNKNOWN)',
   summary:[`Revision: \`${head}\``,`Source: [controlled owned draft PR #270](https://github.com/${REPO}/pull/${NUMBER}).`,
    '| Question | Result |','|---|---|',
    '| Claim-owner authority | NOT_ADMITTED |','| Native original-target replay | UNKNOWN |',
    '| Mathematical intent | UNKNOWN |','| Independent evidence warrant | UNKNOWN |',
    '',`[Controlled lifecycle run](${runUrl}). This is an App transport and stale-source control only; no Lean claim was checked, no proof repaired, and no community input was executed.`].join('\n')}
 };
}

function withdrawnOutput(previous,newHead,runUrl){
 const oldHead=previous.head_sha;
 return {title:'OMM intake: previous revision superseded (UNKNOWN)',
  summary:[marker(newHead),`SUPERSEDED: the observation for \`${oldHead}\` is withdrawn for the current PR revision \`${newHead}\`.`,
    'It never established a mathematical claim. Do not apply its evidence or conclusion to the newer source.',
    `[Withdrawal run](${runUrl}).`,`<details><summary>Original bounded observation</summary>\n\n${previous.output?.summary??'No prior summary'}\n\n</details>`].join('\n\n').slice(0,60000)};
}

export function admitOmmLifecyclePush(event,env={}){
 const ref='refs/heads/'+BRANCH;
 assert(env.GITHUB_EVENT_NAME==='push'&&env.GITHUB_REPOSITORY===REPO&&
  env.GITHUB_REF===ref&&event?.ref===ref&&event.repository?.full_name===REPO&&
  env.GITHUB_ACTOR_ID==='32909488'&&event.sender?.id===32909488&&
  SHA40.test(event.before??'')&&SHA40.test(event.after??'')&&
  env.GITHUB_SHA===event.after&&/^[1-9][0-9]*$/.test(env.GITHUB_RUN_ID??''),
  'OWNED_EVENT_REQUIRED');
 return {head:event.after,before:event.before,runId:env.GITHUB_RUN_ID};
}

/** The App token is limited to checks:write, pull_requests:read on our repo. */
export async function reconcileOwnedOmmLifecycle({number,head,before,runUrl,api,write=false}={}){
 assert(number===NUMBER&&SHA40.test(head??'')&&SHA40.test(before??'')&&
  before!==head&&typeof api==='function'&&RUN_URL.test(runUrl??''),'OWNED_LIFECYCLE_ONLY');
 const live=async()=>{
  const pr=await api(root+'/pulls/'+NUMBER);
  assert(pr?.number===NUMBER&&pr.state==='open'&&pr.head?.sha===head&&
   pr.head?.ref===BRANCH&&pr.head?.repo?.full_name===REPO&&
   pr.base?.repo?.full_name===REPO,'STALE_PR_HEAD');
 };
 const owned=async sha=>{
  const path=root+'/commits/'+sha+'/check-runs?check_name='+encodeURIComponent(NAME)+'&filter=all&per_page=100';
  const d=await api(path);
  assert(Array.isArray(d?.check_runs)&&Number.isSafeInteger(d.total_count)&&
   d.total_count>=0&&d.total_count<=100&&d.total_count===d.check_runs.length,'CHECK_VISIBILITY_INCOMPLETE');
  const matching=d.check_runs.filter(x=>x.name===NAME);
  assert(matching.every(x=>x.app?.id===APP_ID),'FOREIGN_APP_CHECK_NAME_COLLISION');
  assert(matching.every(x=>x.external_id===external(sha)&&x.head_sha===sha&&
   Number.isSafeInteger(x.id))&&matching.length<=1,'CHECK_IDENTITY_COLLISION');
  return matching[0]??null;
 };
 await live();
 const prior=await owned(before),current=await owned(head);
 const payload=buildOmmIntakeCheck({head,runUrl});
 await live();
 if(!write)return {current:{mode:current?'EXISTS':'ABSENT'},previous:{mode:prior?'EXISTS':'ABSENT'},head,before};
 let previous={mode:'ABSENT'};
 if(prior){
  const output=withdrawnOutput(prior,head,runUrl);
  const isWithdrawn=prior.output?.summary?.includes(marker(head))&&
   prior.status==='completed'&&prior.conclusion==='neutral';
  let patched=prior;
  if(!isWithdrawn){
   patched=await api(root+'/check-runs/'+prior.id,{method:'PATCH',body:{status:'completed',
    conclusion:'neutral',external_id:external(before),output}});
  }
  const reread=await api(root+'/check-runs/'+prior.id);
  assert(patched?.id===prior.id&&reread?.id===prior.id&&reread.app?.id===APP_ID&&
   reread.head_sha===before&&reread.name===NAME&&reread.external_id===external(before)&&
   reread.status==='completed'&&reread.conclusion==='neutral'&&
   reread.output?.summary?.includes(marker(head)),'APP_WITHDRAWAL_READBACK_MISMATCH');
  previous={mode:isWithdrawn?'ALREADY_WITHDRAWN':'WITHDRAWN',check_run_id:prior.id,head:before};
 }
 await live();
 let result,mode;
 if(current){
  if(current.status==='completed'&&current.conclusion==='neutral'&&
     current.output?.summary===payload.output.summary){result=current;mode='UNCHANGED';}
  else{result=await api(root+'/check-runs/'+current.id,{method:'PATCH',body:{status:'completed',
   conclusion:'neutral',external_id:external(head),output:payload.output}});mode='UPDATED';}
 }else{result=await api(root+'/check-runs',{method:'POST',body:payload});mode='CREATED';}
 assert(Number.isSafeInteger(result?.id),'APP_CHECK_WRITE_UNCONFIRMED');
 const reread=await api(root+'/check-runs/'+result.id);
 assert(reread?.app?.id===APP_ID&&reread.name===NAME&&reread.head_sha===head&&
  reread.external_id===external(head)&&reread.status==='completed'&&
  reread.conclusion==='neutral'&&reread.output?.summary===payload.output.summary,
  'APP_CHECK_READBACK_MISMATCH');
 await live();
 return {current:{mode,check_run_id:result.id,head},previous,app_id:APP_ID,number,repository:REPO};
}

if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
 try{
  const event=JSON.parse(await readFile(process.env.GITHUB_EVENT_PATH,'utf8'));
  const {head,before,runId}=admitOmmLifecyclePush(event,process.env);
  const token=process.env.MATHGRAPH_APP_INSTALLATION_TOKEN;
  assert(process.argv.length===2&&typeof token==='string'&&token.length>10,'APP_CONTEXT_MISSING');
  const api=async(path,{method='GET',body}={})=>{
   assert(path.startsWith(root+'/'),'APP_API_SURFACE_REFUSED');
   const response=await fetch('https://api.github.com'+path,{method,redirect:'error',
    headers:{Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28',
     Authorization:'Bearer '+token,'Content-Type':'application/json'},
    body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(20000)});
   assert(response.ok,'GITHUB_APP_HTTP_'+response.status);return response.json();
  };
  const result=await reconcileOwnedOmmLifecycle({number:NUMBER,head,before,
   runUrl:`https://github.com/${REPO}/actions/runs/${runId}`,api,write:true});
  console.log('OMM_OWNED_LIFECYCLE_READBACK '+JSON.stringify(result));
 }catch(e){console.error('OMM_OWNED_LIFECYCLE_UNKNOWN:'+String(e.message));process.exitCode=1;}
}
