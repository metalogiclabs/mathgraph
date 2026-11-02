import test from 'node:test';
import assert from 'node:assert/strict';
import {createHmac} from 'node:crypto';
import {mkdtemp,rm,readdir} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
const m=await import('./mention-server-v1.mjs').catch(()=>({}));
const sha='a'.repeat(40);
const policy={repositories:['metalogiclabs/demo'],userIds:[7],handle:'MathGraph',model:'test-model',inputCentsPerMillion:1000,outputCentsPerMillion:3000,maxOutputTokens:500,maxInputBytes:10000,jobCapCents:500,totalCapCents:5000};
const event={action:'created',repository:{full_name:'metalogiclabs/demo'},installation:{id:9},sender:{id:7,type:'User'},issue:{number:1,pull_request:{}},comment:{id:12,body:'@MathGraph -check',user:{id:7,type:'User'}}};
test('webhook HTTP handler validates signatures and persists before ack',async()=>{
 assert.equal(typeof m.createWebhookServer,'function');
 const dir=await mkdtemp(join(tmpdir(),'mg-server-'));let jobs=0,closed=0;
 const server=m.createWebhookServer({secret:'test-secret',stateDir:dir,policy,makeDependencies:async()=>({stateDir:dir,policy,close:async()=>{closed++;},github:{snapshot:async()=>({repository:'metalogiclabs/demo',number:1,sha,files:[],runs:[],files_visibility:'COMPLETE',ci_visibility:'COMPLETE'}),head:async()=>sha,publish:async()=>17},model:async()=>{jobs++;return {summary:'Inspect source',findings:[],next_step:'Replay the theorem.'};}})});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const url='http://127.0.0.1:'+server.address().port;
 async function post(payload,valid=true,eventName='issue_comment'){
  const bytes=JSON.stringify(payload);return fetch(url+'/github/webhook',{method:'POST',headers:{'x-github-event':eventName,'x-hub-signature-256':'sha256='+createHmac('sha256',valid?'test-secret':'wrong').update(bytes).digest('hex')},body:bytes});
 }
 try{
  assert.equal((await fetch(url+'/health')).status,200);
  assert.equal((await post(event,false)).status,401);assert.equal(jobs,0);
  assert.equal((await post({...event,sender:{id:999,type:'User'}})).status,202);assert.equal(jobs,0);
  assert.equal((await post(event,true,'pull_request')).status,202);assert.equal(jobs,0);
  assert.equal((await post(event)).status,202);await server.idle();assert.equal(jobs,1);assert.equal(closed,1);
  assert.equal((await readdir(join(dir,'inbox'))).filter(f=>f.endsWith('.json')).length,1);
  assert.equal((await post(event)).status,202);await server.idle();assert.equal(jobs,1);
 }finally{await new Promise(resolve=>server.close(resolve));await rm(dir,{recursive:true,force:true});}
});
test('source collector binds the PR head and restricts publication',async()=>{
 assert.equal(typeof m.githubClient,'function');const calls=[];
 const api=async(path,opts={})=>{
  calls.push(path);
  if(path==='/repos/metalogiclabs/demo/pulls/1')return {state:'open',head:{sha,repo:{full_name:'metalogiclabs/demo'}},base:{sha:'b'.repeat(40),repo:{full_name:'metalogiclabs/demo'}},body:'Claim: true',title:'A theorem',changed_files:1};
  if(path.includes('/compare/'+ 'b'.repeat(40)+'...'+sha))return {files:[{filename:'Control.lean',patch:'+theorem t : True := by trivial'}]};
  if(path.includes('/actions/runs?'))return {total_count:0,workflow_runs:[]};
  if(path.endsWith('/issues/1/comments'))return {id:19};
  if(path.endsWith('/issues/comments/19'))return {id:19};
  throw Error('UNEXPECTED_PATH');
 };
 const client=m.githubClient({repository:'metalogiclabs/demo',number:1,api});
 const s=await client.snapshot();assert.equal(s.sha,sha);assert.equal(s.base_sha,'b'.repeat(40));assert.ok(calls.some(x=>x.includes('/compare/')));assert.ok(!calls.some(x=>x.includes('/pulls/1/files')));assert.equal(s.claim,'A theorem\n\nClaim: true');assert.equal(s.files_visibility,'COMPLETE');
 assert.equal(await client.publish('result'),19);assert.equal(await client.publish('updated',19),19);
 await assert.rejects(client.publish('attack',20),/COMMENT/);
});
