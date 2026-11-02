// Separate opt-in mention service; the existing go-ethereum Worker is untouched.
import {proofObserver} from './mention-proof-v1.mjs';
import {createServer} from 'node:http';
import {createHmac,timingSafeEqual,createHash,createPrivateKey,sign} from 'node:crypto';
import {mkdir,writeFile,readFile,readdir,rename} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {parseCommand,runMention,openAIModel,reservationCents} from './mention-agent-v1.mjs';
function ensure(ok,code){if(!ok)throw Error(code);}
export function githubClient({repository,number,api,appId,botLogin}){
 const root='/repos/'+repository;let ownedComment=null;
 return {
  async snapshot(){
   const pr=await api(root+'/pulls/'+number);ensure(pr.state==='open','PR_CLOSED');
   ensure(/^[a-f0-9]{40}$/.test(pr.head?.sha)&&/^[a-f0-9]{40}$/.test(pr.base?.sha)&&pr.head.repo?.full_name===repository&&pr.base.repo?.full_name===repository,'FIRST_PARTY_PINNED_SOURCE_REQUIRED');
   const comparison=await api(root+'/compare/'+pr.base.sha+'...'+pr.head.sha);
   const files=comparison.files;ensure(Array.isArray(files),'INVALID_FILES');
   let runs=[],ci_visibility='UNKNOWN';
   try{const r=await api(root+'/actions/runs?head_sha='+pr.head.sha+'&per_page=100');runs=r.workflow_runs;ensure(Array.isArray(runs),'INVALID_RUNS');ci_visibility=Number.isSafeInteger(r.total_count)&&r.total_count===runs.length?'COMPLETE':'INCOMPLETE';}catch{}
   const selected=files.slice(0,30).map(f=>({filename:f.filename,patch:typeof f.patch==='string'?f.patch.slice(0,3000):''}));
   return {repository,number,sha:pr.head.sha,base_sha:pr.base.sha,claim:String(pr.title??'').slice(0,500)+'\n\n'+String(pr.body??'').slice(0,6000),files:selected,runs:runs.map(r=>({id:r.id,name:r.name,status:r.status,conclusion:r.conclusion,head_sha:r.head_sha})),files_visibility:Number.isSafeInteger(pr.changed_files)&&pr.changed_files===files.length&&files.length<=30&&files.every(f=>typeof f.patch==='string'&&f.patch.length<=3000)?'COMPLETE':'INCOMPLETE',ci_visibility};
  },
  async head(){const pr=await api(root+'/pulls/'+number);return pr.state==='open'?pr.head.sha:null;},
  async resumePublish(body,id){
   const comment=await api(root+'/issues/comments/'+id);
   ensure(comment.id===id&&comment.performed_via_github_app?.id===appId&&comment.user?.login===botLogin&&comment.issue_url==='https://api.github.com'+root+'/issues/'+number,'RECOVERY_COMMENT_NOT_OWNED');
   ownedComment=id;return this.publish(body,id);
  },
  async publish(body,id){
   ensure(typeof body==='string'&&body.length<60000,'INVALID_COMMENT');
   if(id!==undefined)ensure(id===ownedComment,'COMMENT_NOT_OWNED');
   const result=await api(id===undefined?root+'/issues/'+number+'/comments':root+'/issues/comments/'+id,{method:id===undefined?'POST':'PATCH',body:{body}});
   ensure(Number.isSafeInteger(result.id)&&result.id>0&&(id===undefined||result.id===id),'COMMENT_READBACK_INVALID');ownedComment=result.id;return result.id;
  }
 };
}
function authorized(e,p){return e?.action==='created'&&e.issue?.pull_request&&Number.isSafeInteger(e.issue.number)&&e.issue.number>0&&Number.isSafeInteger(e.comment?.id)&&e.comment.id>0&&e.sender?.type==='User'&&e.comment.user?.type==='User'&&e.sender.id===e.comment.user.id&&p.userIds.includes(e.sender.id)&&p.repositories.includes(e.repository?.full_name)&&parseCommand(e.comment.body,p.handle);}
export function createWebhookServer({secret,stateDir,policy,makeDependencies}){
 ensure(typeof secret==='string'&&secret.length>0,'WEBHOOK_SECRET_REQUIRED');reservationCents(policy);
 let tail=Promise.resolve();const inflight=new Set();
 const execute=async (file,recover)=>{
  let deps;
  try{const event=JSON.parse(await readFile(file,'utf8'));deps=await makeDependencies(event);await runMention(event,{...deps,recover});await writeFile(file+'.done','done',{mode:0o600});}
  catch{console.error('MATHGRAPH_JOB_INCOMPLETE');}
  finally{if(deps?.close)try{await deps.close();}catch{console.error('MATHGRAPH_TOKEN_REVOCATION_FAILED');}}
 };
 const enqueue=(file,recover=false)=>{if(inflight.has(file))return;inflight.add(file);tail=tail.then(()=>execute(file,recover)).finally(()=>inflight.delete(file));};
 const server=createServer(async(req,res)=>{
  const reply=(status,text)=>{res.writeHead(status,{'content-type':'text/plain'});res.end(text);};
  if(req.method==='GET'&&req.url==='/health')return reply(200,'alive');
  if(req.method!=='POST'||req.url!=='/github/webhook')return reply(404,'not found');
  try{
   const parts=[];let size=0;
   for await(const chunk of req){size+=chunk.length;if(size>1000000)return reply(413,'too large');parts.push(chunk);}
   const bytes=Buffer.concat(parts);const sig=req.headers['x-hub-signature-256'];
   if(typeof sig!=='string'||!/^sha256=[a-f0-9]{64}$/.test(sig))return reply(401,'invalid signature');
   if(!timingSafeEqual(createHmac('sha256',secret).update(bytes).digest(),Buffer.from(sig.slice(7),'hex')))return reply(401,'invalid signature');
   let event;try{event=JSON.parse(bytes.toString('utf8'));}catch{return reply(400,'invalid JSON');}
   if(req.headers['x-github-event']!=='issue_comment'||!authorized(event,policy))return reply(202,'ignored');
   await mkdir(join(stateDir,'inbox'),{recursive:true,mode:0o700});
   const key=createHash('sha256').update(event.repository.full_name+':'+event.comment.id).digest('hex');const file=join(stateDir,'inbox',key+'.json');
   try{await writeFile(file,JSON.stringify(event),{flag:'wx',mode:0o600});}catch(e){if(e.code==='EEXIST')return reply(202,'already queued');throw e;}
   enqueue(file);reply(202,'queued');
  }catch{if(!res.headersSent)reply(503,'unavailable');}
 });
 server.idle=()=>tail;
 server.resume=async()=>{await mkdir(join(stateDir,'inbox'),{recursive:true,mode:0o700});const files=await readdir(join(stateDir,'inbox'));for(const file of files.filter(f=>/^[a-f0-9]{64}\.json$/.test(f)&&!files.includes(f+'.done')))enqueue(join(stateDir,'inbox',file),true);};
 return server;
}
export async function appDependencies(event,{env,policy,stateDir,fetcher=fetch}){
 ensure(policy.repositories.includes(event.repository?.full_name)&&authorized(event,policy),'EVENT_NOT_AUTHORIZED');
 const appId=Number(env.MATHGRAPH_APP_ID);ensure(Number.isSafeInteger(appId)&&appId>0,'APP_ID_REQUIRED');
 const key=createPrivateKey(env.MATHGRAPH_APP_PRIVATE_KEY);ensure(key.asymmetricKeyType==='rsa','APP_KEY_INVALID');
 const now=Math.floor(Date.now()/1000),enc=x=>Buffer.from(JSON.stringify(x)).toString('base64url');
 const unsigned=enc({alg:'RS256',typ:'JWT'})+'.'+enc({iat:now-60,exp:now+540,iss:String(appId)});
 const jwt=unsigned+'.'+sign('RSA-SHA256',Buffer.from(unsigned),key).toString('base64url');
 const repository=event.repository.full_name,root='/repos/'+repository;
 const request=async(path,token,{method='GET',body}={})=>{
  ensure(path==='/installation/token'||path==='/app'||path.startsWith(root+'/')||/^\/app\/installations\/[1-9][0-9]*\/access_tokens$/.test(path),'GITHUB_PATH_REFUSED');
  const r=await fetcher('https://api.github.com'+path,{method,redirect:'error',headers:{Authorization:'Bearer '+token,Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'MathGraph-Mention-Pilot','Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(20000)});
  ensure(r.ok,'GITHUB_REQUEST_FAILED');return r.status===204?{}:r.json();
 };
 const app=await request('/app',jwt);ensure(app.id===appId&&app.owner?.login===env.MATHGRAPH_APP_OWNER,'APP_IDENTITY_MISMATCH');
 const installation=await request(root+'/installation',jwt);ensure(installation.id===event.installation?.id&&installation.app_id===appId&&!installation.suspended_at,'INSTALLATION_MISMATCH');
 const minted=await request('/app/installations/'+installation.id+'/access_tokens',jwt,{method:'POST',body:{repositories:[repository.split('/')[1]],permissions:{contents:'read',pull_requests:'read',issues:'write',actions:'read'}}});
 ensure(typeof minted.token==='string'&&minted.token.length>10,'TOKEN_NOT_ISSUED');
 const close=()=>request('/installation/token',minted.token,{method:'DELETE'});
 let manifests=[];
 try{if(env.MATHGRAPH_PROOF_TRUST_FILE){const raw=await readFile(env.MATHGRAPH_PROOF_TRUST_FILE,'utf8');ensure(Buffer.byteLength(raw)<=65536,'PROOF_TRUST_TOO_LARGE');manifests=JSON.parse(raw);ensure(Array.isArray(manifests)&&manifests.length<=32,'PROOF_TRUST_INVALID');}}catch(e){await close();throw e;}
 try{return {policy,stateDir,observeProof:proofObserver({manifests,token:minted.token,fetcher}),github:githubClient({repository,number:event.issue.number,appId,botLogin:app.slug+'[bot]',api:(path,options)=>request(path,minted.token,options)}),model:openAIModel({apiKey:env.OPENAI_API_KEY,policy,fetcher}),close};}catch(e){await close();throw e;}
}
if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
 const config=process.argv[2];ensure(config,'POLICY_FILE_REQUIRED');const policy=JSON.parse(await readFile(config,'utf8'));
 for(const name of ['OPENAI_API_KEY','MATHGRAPH_WEBHOOK_SECRET','MATHGRAPH_APP_PRIVATE_KEY','MATHGRAPH_APP_ID','MATHGRAPH_APP_OWNER','MATHGRAPH_STATE_DIR'])ensure(process.env[name],'MISSING_'+name);
 const stateDir=process.env.MATHGRAPH_STATE_DIR;ensure(resolve(stateDir)===stateDir,'ABSOLUTE_STATE_DIRECTORY_REQUIRED');
 const server=createWebhookServer({secret:process.env.MATHGRAPH_WEBHOOK_SECRET,stateDir,policy,makeDependencies:e=>appDependencies(e,{env:process.env,policy,stateDir})});await server.resume();
 server.listen(Number(process.env.PORT??8080),'0.0.0.0');console.log('MathGraph mention service started');
}
