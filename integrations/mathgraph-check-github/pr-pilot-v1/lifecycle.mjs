import {admitRequest,profileFor,formatResult,resultTitle} from './policy.mjs';
export const APP_ID=5308912,CHECK_NAME='MathGraph Check / PR investigation';
const checkName=request=>CHECK_NAME+' #'+request.number;
const RETRYABLE_TITLES=new Set(['Check incomplete','Repair incomplete','Source changed — recheck required']);
const ensure=(b,c)=>{if(!b)throw Error(c);};
export const logicalIdentity=r=>`mg-pr-v1:${r.repository}#${r.number}@${r.head_sha}~${r.base_sha}:${r.command}${r.profile?.claim_profile==='empty-tail-v1'?':cap:empty-tail-v1':''}${['passport-v1','expectations-v1','transport-v1'].includes(r.profile?.report_version)?':report:'+r.profile.report_version:''}`;
export const identity=r=>logicalIdentity(r)+':'+r.comment_id;
export async function listChecks(request,api){const checks=[];let total;for(let page=1;page<=3;page++){const r=await api('/repos/'+request.repository+'/commits/'+request.head_sha+'/check-runs?per_page=100&filter=all&page='+page);ensure(Array.isArray(r.check_runs)&&Number.isSafeInteger(r.total_count),'INVALID_CHECK_HISTORY');total=r.total_count;checks.push(...r.check_runs);if(checks.length===total)return checks;if(r.check_runs.length<100)break;}throw Error('INCOMPLETE_CHECK_HISTORY');}
export async function authenticate(payload,api){
 profileFor(payload.repository);ensure(Number.isSafeInteger(payload.number)&&payload.number>0&&Number.isSafeInteger(payload.comment_id)&&payload.comment_id>0,'INVALID_REQUEST');
 const root='/repos/'+payload.repository,pr=await api(root+'/pulls/'+payload.number),comment=await api(root+'/issues/comments/'+payload.comment_id);
 ensure(comment.issue_url===`https://api.github.com${root}/issues/${payload.number}`,'WRONG_COMMENT_ISSUE');
 ensure(/^[a-zA-Z0-9-]{1,39}$/.test(comment.user?.login??''),'INVALID_ACTOR');
 const {permission}=await api(root+'/collaborators/'+comment.user.login+'/permission');
 const files=[];for(let page=1;page<=3;page++){const batch=await api(root+'/pulls/'+payload.number+'/files?per_page=100&page='+page);ensure(Array.isArray(batch),'INVALID_FILE_LIST');files.push(...batch);if(batch.length<100)break;}
 const request=admitRequest({repository:payload.repository,pr,comment,permission,files,filesComplete:pr.changed_files===files.length});
 ensure(request.command===payload.command,'COMMAND_CHANGED');return request;
}
export async function startCheck(request,api,runURL){
 ensure(/^https:\/\/github.com\/metalogiclabs\/mathgraph\/actions\/runs\/[1-9][0-9]*$/.test(runURL),'INVALID_RUN_URL');
 const root='/repos/'+request.repository,checks=await listChecks(request,api);
 const existing=checks.filter(c=>c.app?.id===APP_ID&&c.head_sha===request.head_sha&&c.external_id?.startsWith(logicalIdentity(request)+':'));
 const queued=existing.find(c=>c.id===request.queued_check_id&&c.status==='in_progress'&&c.output?.title==='Queued for investigation');
 if(queued){const changed=await api(root+'/check-runs/'+queued.id,{method:'PATCH',body:{details_url:runURL,output:{title:['OWNED_FORK_REPOSITORY_CONTRACT','OWNED_FORK_CLI_PARITY'].includes(request.profile.mode)?'Checking compilation and fixed regressions…':'Checking independent probes…',summary:queued.output.summary}}});ensure(changed.app?.id===APP_ID&&changed.head_sha===request.head_sha,'QUEUED_CHECK_CLAIM_MISMATCH');return {state:'STARTED',check_id:queued.id,run_url:runURL};}
 const duplicate=existing.find(c=>c.external_id===identity(request)||c.status==='in_progress'||!RETRYABLE_TITLES.has(c.output?.title));
 if(duplicate)return {state:'DUPLICATE',check_id:duplicate.id,run_url:duplicate.details_url};
 const body={name:checkName(request),head_sha:request.head_sha,external_id:identity(request),status:'in_progress',details_url:runURL,output:{title:request.support.supported?'Checking independent probes…':'Unsupported PR scope',summary:`Source: ${request.repository}#${request.number} @ ${request.head_sha}. Selected scope: ${request.profile.claim_profile??request.profile.cli_profile??request.profile.mode}. Native evidence will update here.`}};
 const c=await api(root+'/check-runs',{method:'POST',body});ensure(c.app?.id===APP_ID&&c.head_sha===request.head_sha&&c.external_id===identity(request)&&Number.isSafeInteger(c.id),'CHECK_IDENTITY_MISMATCH');
 return {state:'STARTED',check_id:c.id,run_url:runURL};
}
function fresh(pr,r){return pr.state==='open'&&pr.head?.sha===r.head_sha&&pr.base?.sha===r.base_sha&&pr.head?.repo?.full_name===r.repository&&pr.base?.repo?.full_name===r.repository;}
async function ownedCheck(request,publication,api){const c=await api('/repos/'+request.repository+'/check-runs/'+publication.check_id);ensure(c.app?.id===APP_ID&&c.head_sha===request.head_sha&&c.external_id===identity(request),'CHECK_OWNERSHIP_MISMATCH');return c;}
export async function finishCheck(request,publication,report,api){
 const root='/repos/'+request.repository;await ownedCheck(request,publication,api);
 let current=await api(root+'/pulls/'+request.number),result=report??{status:'UNKNOWN',reason:'MISSING_ASSESSMENT'};
 if(!fresh(current,request))result={status:'STALE',reason:'SOURCE_CHANGED',historical_status:result.status};
 const title=resultTitle(result,request);
 const body={status:'completed',conclusion:'neutral',output:{title,summary:formatResult(result,request,publication.run_url)}};
 const written=await api(root+'/check-runs/'+publication.check_id,{method:'PATCH',body});ensure(written.app?.id===APP_ID&&written.head_sha===request.head_sha&&written.external_id===identity(request)&&written.conclusion==='neutral','CHECK_PUBLISH_MISMATCH');
 // Close the publish race; preserve historical evidence, withdraw applicability.
 current=await api(root+'/pulls/'+request.number);
 if(result.status!=='STALE'&&!fresh(current,request)){await withdrawChecks({...request,head_sha:current.head?.sha??''},[written],api,{force:true});return {state:'STALE',check_id:written.id};}
 return {state:result.status==='STALE'?'STALE':'PUBLISHED',check_id:written.id};
}
export async function withdrawChecks(request,checks,api,{force=false}={}){
 const prefix=`mg-pr-v1:${request.repository}#${request.number}@`;let count=0;
 for(const c of checks){if(c.app?.id!==APP_ID||!c.external_id?.startsWith(prefix)||(!force&&c.head_sha===request.head_sha&&(!request.base_sha||c.external_id.startsWith(prefix+request.head_sha+'~'+request.base_sha+':'))))continue;
 const body={status:'completed',conclusion:'neutral',output:{title:'Source changed — recheck required',summary:'**Current applicability withdrawn.** Historical evidence follows.\n\n'+(c.output?.summary??'No completed evidence was retained.')}};
 const changed=await api('/repos/'+request.repository+'/check-runs/'+c.id,{method:'PATCH',body});ensure(changed.id===c.id&&changed.app?.id===APP_ID&&changed.head_sha===c.head_sha,'WITHDRAWAL_IDENTITY_MISMATCH');count++;}
 return count;
}

export async function queueCheck(request,api){
 const existing=(await listChecks(request,api)).filter(c=>c.app?.id===APP_ID&&c.head_sha===request.head_sha&&c.external_id?.startsWith(logicalIdentity(request)+':'));
 const duplicate=existing.find(c=>c.external_id===identity(request)||c.status==='in_progress'||!RETRYABLE_TITLES.has(c.output?.title));
 if(duplicate)return {state:'DUPLICATE',check_id:duplicate.id};
 const body={name:checkName(request),head_sha:request.head_sha,external_id:identity(request),status:'in_progress',details_url:'https://github.com/metalogiclabs/mathgraph/actions',output:{title:'Queued for investigation',summary:`Requested by a repository maintainer for ${request.repository}#${request.number}, head ${request.head_sha}, base ${request.base_sha}. Native evidence has not run yet.`}};
 const c=await api('/repos/'+request.repository+'/check-runs',{method:'POST',body});ensure(c.app?.id===APP_ID&&c.head_sha===request.head_sha&&c.external_id===identity(request),'QUEUE_CHECK_IDENTITY_MISMATCH');return {state:'QUEUED',check_id:c.id,run_url:body.details_url};
}
export async function priorCheckRun(request,api){
 if(request.command!=='fix'||!request.support.supported)return null;
 const cs=await listChecks(request,api),original=cs.find(c=>c.app?.id===APP_ID&&c.external_id?.startsWith(logicalIdentity({...request,command:'check'})+':')&&c.status==='completed'&&c.conclusion==='neutral');
 const match=original?.details_url?.match(/^https:\/\/github.com\/metalogiclabs\/mathgraph\/actions\/runs\/([1-9][0-9]*)$/);ensure(match,'RUN_CHECK_BEFORE_FIX');return Number(match[1]);
}
