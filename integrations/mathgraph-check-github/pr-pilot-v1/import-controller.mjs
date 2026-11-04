// Metadata-only orchestration. Never checks out or executes imported source.
import {readFile} from 'node:fs/promises';
import {appJWT} from '../cloudflare/worker.mjs';
import {githubClient} from './github.mjs';import {mintScopedToken} from './auth.mjs';import {verifyDispatch} from './transport.mjs';
import {authorizeImport,snapshotUpstream,replyToImport} from './upstream-intake.mjs';
const ensure=(b,c)=>{if(!b)throw Error(c);};
const event=JSON.parse(await readFile(process.env.GITHUB_EVENT_PATH,'utf8'));ensure(event.action==='mathgraph-pr-import-v1','WRONG_EVENT');
const signed=verifyDispatch(event.client_payload,process.env.APP_PRIVATE_KEY);ensure(signed.command==='import','WRONG_COMMAND');
const app=githubClient(appJWT(process.env.APP_PRIVATE_KEY),{repository:signed.repository}),installation=await app('/repos/'+signed.repository+'/installation');ensure(installation.id===signed.installation_id,'INSTALLATION_CHANGED');
const token=await mintScopedToken(app,installation.id,signed.repository,{contents:'write',pull_requests:'write',issues:'write'}),api=githubClient(token,{repository:signed.repository});
try{
 const request=await authorizeImport(signed,api,signed.actor_authorization==='PILOT_OPERATOR'?[signed.actor_id]:[]);
 ensure(['actor_id','actor_login','actor_authorization','upstream_number','upstream_url'].every(k=>request[k]===signed[k]),'IMPORT_AUTHORITY_CHANGED');
 const publicAPI=async path=>{ensure(/^\/repos\/nasa-jpl\/L4YAML\/(pulls\/[1-9][0-9]*|git\/commits\/[a-f0-9]{40})$/.test(path),'UPSTREAM_PATH_FORBIDDEN');const r=await fetch('https://api.github.com'+path,{redirect:'manual',headers:{Accept:'application/vnd.github+json','User-Agent':'MathGraph-Check'},signal:AbortSignal.timeout(20000)});ensure(r.ok,'UPSTREAM_HTTP_'+r.status);return r.json();};
 try{const result=await snapshotUpstream(request,api,publicAPI);await replyToImport(request,api,result);console.log(JSON.stringify(result));}
 catch(e){await replyToImport(request,api,{reason:['UPSTREAM_CHANGED_RETRY_REQUIRED','UPSTREAM_PUBLIC_SAME_REPO_PR_REQUIRED','IMPORT_SNAPSHOT_CLOSED','IMPORT_BRANCH_COLLISION'].includes(e.message)?e.message:'IMPORT_INCOMPLETE'});throw e;}
}finally{await api('/installation/token',{method:'DELETE'});}
