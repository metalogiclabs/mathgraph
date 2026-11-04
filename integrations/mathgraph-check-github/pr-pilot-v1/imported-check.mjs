import {authorizeImport,admitUpstream} from './upstream-intake.mjs';
import {admitRequest} from './policy.mjs';
const ensure=(b,c)=>{if(!b)throw Error(c);};
export function publicGitHub({fetcher=fetch,token}={}){return async path=>{ensure(/^\/repos\/(?:nasa-jpl|metalogiclabs)\/L4YAML\/(?:pulls\/[1-9][0-9]*|git\/commits\/[a-f0-9]{40})$/.test(path),'UPSTREAM_PATH_FORBIDDEN');const r=await fetcher('https://api.github.com'+path,{redirect:'manual',headers:{Accept:'application/vnd.github+json','User-Agent':'MathGraph-Check',...(token?{Authorization:'Bearer '+token}:{})},signal:AbortSignal.timeout(20000)});ensure(r.ok,'UPSTREAM_HTTP_'+r.status);return r.json();};}
export async function authenticateImported(item,api,{pilotOperators=[],publicAPI=publicGitHub()}={}){
 const o=item.origin;ensure(o&&Number.isSafeInteger(o.number)&&Number.isSafeInteger(o.comment_id)&&Number.isSafeInteger(o.upstream_number)&&['nasa-jpl/L4YAML','metalogiclabs/L4YAML'].includes(o.upstream_repository),'IMPORT_ORIGIN_INVALID');
 const actor=await authorizeImport({repository:item.repository,number:o.number,comment_id:o.comment_id},api,pilotOperators);
 ensure(!actor.stop&&actor.upstream_number===o.upstream_number&&actor.upstream_repository===o.upstream_repository&&actor.actor_id===item.actor_id,'IMPORT_AUTHORITY_CHANGED');
 const source=admitUpstream(await publicAPI('/repos/'+o.upstream_repository+'/pulls/'+o.upstream_number),o.upstream_number,o.upstream_repository);
 ensure(source.head===item.upstream_head&&source.base===item.upstream_base,'UPSTREAM_CHANGED_RETRY_REQUIRED');
 const root='/repos/'+item.repository,pr=await api(root+'/pulls/'+item.number),commit=await api(root+'/git/commits/'+pr.head.sha),original=await publicAPI('/repos/'+o.upstream_repository+'/git/commits/'+source.head);
 const branch=`pilot/import-${o.upstream_repository.split('/')[0]}-${o.upstream_number}-${source.head.slice(0,12)}-${source.base.slice(0,12)}${item.watch_generation?'-g'+item.watch_generation:''}`;
 ensure(pr.head.ref===branch&&pr.base.sha===source.base&&commit.parents?.length===1&&commit.parents[0].sha===source.head&&commit.tree?.sha===original.tree?.sha,'IMPORTED_SNAPSHOT_LINEAGE_INVALID');
 const files=[];for(let page=1;page<=3;page++){const rows=await api(root+'/pulls/'+item.number+'/files?per_page=100&page='+page);ensure(Array.isArray(rows),'INVALID_FILE_LIST');files.push(...rows);if(rows.length<100)break;}
 // The real URL command authorizes checking its frozen snapshot; no human comment on that snapshot is invented.
 const request=admitRequest({repository:item.repository,pr,comment:{id:actor.comment_id,body:'@MathGraph -check',user:{id:actor.actor_id,login:actor.actor_login,type:'User'}},permission:actor.actor_authorization==='REPOSITORY_MAINTAINER'?'write':'read',pilotOperators,files,filesComplete:true});
 if(pr.changed_files!==files.length)request.support={supported:false,reason:'INCOMPLETE_CHANGED_FILES'};
 return {...request,watch_generation:item.watch_generation??0,origin:{...o,watch:actor.watch,requested_at:actor.requested_at,watch_generation:item.watch_generation??0},upstream_state:source.state,upstream_head:source.head,upstream_base:source.base,command_origin:'AUTHENTIC_UPSTREAM_URL_REQUEST'};
}
