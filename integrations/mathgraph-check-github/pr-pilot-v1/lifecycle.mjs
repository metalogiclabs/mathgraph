import {admitRequest,profileFor,formatResult} from './policy.mjs';
export const APP_ID=5308912,CHECK_NAME='MathGraph Check / PR investigation';
const ensure=(b,c)=>{if(!b)throw Error(c);};
export const identity=r=>`mg-pr-v1:${r.repository}#${r.number}@${r.head_sha}:${r.command}`;
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
 const root='/repos/'+request.repository,response=await api(root+'/commits/'+request.head_sha+'/check-runs?per_page=100');
 ensure(Array.isArray(response.check_runs)&&response.total_count===response.check_runs.length,'INCOMPLETE_CHECK_HISTORY');
 const existing=response.check_runs.filter(c=>c.app?.id===APP_ID&&c.head_sha===request.head_sha&&c.external_id===identity(request));
 if(existing.length)return {state:'DUPLICATE',check_id:existing[0].id,run_url:existing[0].details_url};
 const body={name:CHECK_NAME,head_sha:request.head_sha,external_id:identity(request),status:'in_progress',details_url:runURL,output:{title:request.support.supported?'Checking independent probes…':'Unsupported PR scope',summary:`Source: ${request.repository}#${request.number} @ ${request.head_sha}. Selected capability: Scripts.Ledger. Model proposals are advisory; native results will update here.`}};
 const c=await api(root+'/check-runs',{method:'POST',body});ensure(c.app?.id===APP_ID&&c.head_sha===request.head_sha&&c.external_id===identity(request)&&Number.isSafeInteger(c.id),'CHECK_IDENTITY_MISMATCH');
 return {state:'STARTED',check_id:c.id,run_url:runURL};
}
function fresh(pr,r){return pr.state==='open'&&pr.head?.sha===r.head_sha&&pr.base?.sha===r.base_sha&&pr.head?.repo?.full_name===r.repository&&pr.base?.repo?.full_name===r.repository;}
async function ownedCheck(request,publication,api){const c=await api('/repos/'+request.repository+'/check-runs/'+publication.check_id);ensure(c.app?.id===APP_ID&&c.head_sha===request.head_sha&&c.external_id===identity(request),'CHECK_OWNERSHIP_MISMATCH');return c;}
export async function finishCheck(request,publication,report,api){
 const root='/repos/'+request.repository;await ownedCheck(request,publication,api);
 let current=await api(root+'/pulls/'+request.number),result=report??{status:'UNKNOWN',reason:'MISSING_ASSESSMENT'};
 if(!fresh(current,request))result={status:'STALE',reason:'SOURCE_CHANGED',historical_status:result.status};
 const title=result.status==='STALE'?'Source changed — recheck required':result.status==='UNKNOWN'?'Check incomplete':result.status==='CANDIDATE_ASSERTION_FAILURE'?'Generated probe failure reproduced':'No counterexample in generated probes';
 const body={status:'completed',conclusion:'neutral',output:{title,summary:formatResult(result,request,publication.run_url)}};
 const written=await api(root+'/check-runs/'+publication.check_id,{method:'PATCH',body});ensure(written.app?.id===APP_ID&&written.head_sha===request.head_sha&&written.external_id===identity(request)&&written.conclusion==='neutral','CHECK_PUBLISH_MISMATCH');
 // Close the publish race; preserve historical evidence, withdraw applicability.
 current=await api(root+'/pulls/'+request.number);
 if(result.status!=='STALE'&&!fresh(current,request)){await withdrawChecks({...request,head_sha:current.head?.sha??''},[written],api,{force:true});return {state:'STALE',check_id:written.id};}
 return {state:result.status==='STALE'?'STALE':'PUBLISHED',check_id:written.id};
}
export async function withdrawChecks(request,checks,api,{force=false}={}){
 const prefix=`mg-pr-v1:${request.repository}#${request.number}@`;let count=0;
 for(const c of checks){if(c.app?.id!==APP_ID||!c.external_id?.startsWith(prefix)||(!force&&c.head_sha===request.head_sha))continue;
 const body={status:'completed',conclusion:'neutral',output:{title:'Source changed — recheck required',summary:'**Current applicability withdrawn.** Historical evidence follows.\n\n'+(c.output?.summary??'No completed evidence was retained.')}};
 const changed=await api('/repos/'+request.repository+'/check-runs/'+c.id,{method:'PATCH',body});ensure(changed.id===c.id&&changed.app?.id===APP_ID&&changed.head_sha===c.head_sha,'WITHDRAWAL_IDENTITY_MISMATCH');count++;}
 return count;
}
