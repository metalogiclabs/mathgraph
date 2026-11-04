import {PILOT_INBOX,CONTACT_EMAIL} from './pilot-config.mjs';
const ensure=(b,c)=>{if(!b)throw Error(c);};
const url=x=>typeof x==='string'&&/^https:\/\/github\.com\/(?:metalogiclabs\/(?:L4YAML\/(?:pull\/[1-9][0-9]*(?:\/checks\?check_run_id=[1-9][0-9]*)?|runs\/[1-9][0-9]*)|mathgraph\/actions\/runs\/[1-9][0-9]*))$/.test(x)?x:null;
const text=x=>String(x??'').replace(/[\r\n`<>\[\]@]/g,' ').slice(0,300);
export function requestStatusBody(request,result){
 const origin=request.origin??request,number=origin.number,comment=origin.comment_id;
 ensure(request.repository==='metalogiclabs/L4YAML'&&Number.isSafeInteger(number)&&number>0&&Number.isSafeInteger(comment)&&comment>0,'STATUS_ORIGIN_INVALID');
 const marker=`<!-- mathgraph-pilot-status:${number===PILOT_INBOX?'request-'+comment:'pr-'+number} -->`;
 const messages={RUNNING:'A Check for this revision is already running. Follow the existing Check below.',QUEUED:'Request received. The Check is queued; native execution usually takes a few minutes.',REUSED:'This revision was already checked. Reusing the completed evidence or existing draft; no duplicate run is needed.',PUBLISHED:'Check completed.',UNKNOWN:'Not verified. The available check could not establish a result for this change.',INVITE_REQUIRED:'Invitation required. A GitHub account alone does not enable this pilot.',INPUT_NEEDED:'Add a public L4YAML PR URL, for example `/check https://github.com/nasa-jpl/L4YAML/pull/217`.',ACCESS_READY:'Your account is eligible to use this pilot. This verifies access; it does not run a code check.',WATCHING:'Following this public PR for seven days. New commits are checked on fresh copies on our fork about every ten minutes; scheduling may be delayed.',WATCH_STOPPED:'Following has stopped. Existing revision-specific evidence remains available.',SNAPSHOT_READY:'A frozen copy of the public PR is ready. Its Check will appear below.'};
 const subject=result.snapshot_url?.match(/\/pull\/([1-9][0-9]*)$/)?.[1]??(request.origin?request.number:undefined);const lines=[marker,`<!-- mathgraph-pilot-request:${comment} -->`,subject?`<!-- mathgraph-pilot-subject:${subject} -->`:'','### MathGraph Check',messages[result.state]??'Request status updated.'];
 if(result.title)lines.push('**'+text(result.title)+'**');
 if(result.state==='INVITE_REQUIRED')lines.push(`[Request an invitation](mailto:${CONTACT_EMAIL}). Only public code is accepted here; do not post credentials or private project details.`);
 if(result.reason)lines.push(text(result.reason));
 for(const [key,label]of [['snapshot_url','Open checked snapshot'],['check_url','Open Check and evidence'],['repair_url','Review draft repair']])if(url(result[key]))lines.push(`[${label}](${result[key]})`);
 if(result.expires_at)lines.push('Follow expires: '+new Date(result.expires_at).toISOString()+'. Use `/unwatch PR-URL` in the request inbox to stop sooner.');
 if(result.last_checked_at)lines.push('Upstream last checked: '+new Date(result.last_checked_at).toISOString()+'.');
 return lines.join('\n\n');
}
export async function publishRequestStatus(request,api,result){
 let body=requestStatusBody(request,result),origin=request.origin??request,root='/repos/'+request.repository,marker=body.split('\n')[0];const rows=[];
 for(let page=1;page<=3;page++){const batch=await api(root+'/issues/'+origin.number+'/comments?per_page=100&page='+page);ensure(Array.isArray(batch),'STATUS_HISTORY_INVALID');rows.push(...batch);if(batch.length<100)break;ensure(page<3,'STATUS_HISTORY_INCOMPLETE');}
 const prior=rows.filter(c=>c.user?.id===342263476&&c.user.type==='Bot'&&c.user.login==='mathgraph-check[bot]'&&c.body?.startsWith(marker));ensure(prior.length<=1,'STATUS_REPLY_AMBIGUOUS');
 if(prior.length){const oldComment=Number(prior[0].body.match(/<!-- mathgraph-pilot-request:(\d+) -->/)?.[1]??0),oldSubject=Number(prior[0].body.match(/<!-- mathgraph-pilot-subject:(\d+) -->/)?.[1]??0),newSubject=Number(body.match(/<!-- mathgraph-pilot-subject:(\d+) -->/)?.[1]??0);if(origin.number!==PILOT_INBOX&&oldComment>origin.comment_id||oldSubject&&newSubject&&oldSubject>newSubject)return {state:'SUPERSEDED'};if(oldSubject&&!newSubject)body+='\n\n<!-- mathgraph-pilot-subject:'+oldSubject+' -->';if(prior[0].body===body)return {state:'UNCHANGED'};ensure(Number.isSafeInteger(prior[0].id),'STATUS_REPLY_INVALID');await api(root+'/issues/comments/'+prior[0].id,{method:'PATCH',body:{body}});return {state:'UPDATED'};}
 await api(root+'/issues/'+origin.number+'/comments',{method:'POST',body:{body}});return {state:'CREATED'};
}
export const checkURL=(repository,number,id)=>`https://github.com/${repository}/pull/${number}/checks?check_run_id=${id}`;
export function reuseDetails(check){if(!/repair verified/i.test(check?.output?.title??''))return {};const match=(check.output.summary??'').match(/\[Review (?:the )?draft repair\]\((https:\/\/github\.com\/metalogiclabs\/L4YAML\/pull\/[1-9][0-9]*)\)/i);return {repair_url:match?.[1]};}
