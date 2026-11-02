import test from 'node:test';import assert from 'node:assert/strict';import {generateKeyPairSync} from 'node:crypto';import {processPilotDelivery} from './worker-handler.mjs';import {verifyDispatch} from './transport.mjs';
const key=generateKeyPairSync('rsa',{modulusLength:2048}).privateKey.export({format:'pem',type:'pkcs8'}).toString();
const repo='metalogiclabs/L4YAML',root='/repos/'+repo,sha='a'.repeat(40),base='b'.repeat(40);
const item={schema:'mathgraph.pr-pilot.delivery.v1',repository:repo,number:2,comment_id:7,command:'check',installationID:3,action:'command'};
function harness({failDispatch=false,budget='RESERVED',permission='write'}={}){
 const checks=[],sent=[],revoked=[],storage=new Map();let reservations=0;
 const pr={number:2,state:'open',changed_files:1,head:{sha,repo:{full_name:repo,private:false}},base:{sha:base,repo:{full_name:repo,private:false}}};
 const fetcher=async(url,o={})=>{const p=new URL(url).pathname,q=new URL(url).search,method=o.method??'GET',body=o.body?JSON.parse(o.body):null;
 if(p===root+'/installation')return Response.json({id:3});if(p==='/repos/metalogiclabs/mathgraph/installation')return Response.json({id:9});
 if(p.match(/^\/app\/installations\/(3|9)\/access_tokens$/)){assert.ok(body.repositories);assert.equal(body.repository_names,undefined);return Response.json({token:p.includes('/3/')?'source':'central',permissions:{...body.permissions,metadata:'read'}});}
 if(p==='/installation/repositories')return Response.json({total_count:1,repositories:[{full_name:o.headers.Authorization==='Bearer source'?repo:'metalogiclabs/mathgraph'}]});
 if(p==='/installation/token'){revoked.push(o.headers.Authorization);return new Response(null,{status:204});}
 if(p===root+'/pulls/2')return Response.json(pr);
 if(p===root+'/issues/comments/7')return Response.json({id:7,body:'@MathGraph -check',issue_url:'https://api.github.com'+root+'/issues/2',user:{id:99,login:'maintainer',type:'User'}});
 if(p===root+'/collaborators/maintainer/permission')return Response.json({permission});
 if(p===root+'/pulls/2/files')return Response.json([{filename:'Scripts/Ledger.lean',status:'modified'}]);
 if(p.startsWith(root+'/commits/')&&p.endsWith('/check-runs')){const head=p.split('/').at(-2),matching=checks.filter(c=>c.head_sha===head);return Response.json({total_count:matching.length,check_runs:matching});}
 if(p===root+'/check-runs'&&method==='POST'){const c={...body,id:10+checks.length,app:{id:5308912}};checks.push(c);return Response.json(c);}
 if(p.match(/\/check-runs\/\d+$/)){const c=checks.find(c=>p.endsWith('/'+c.id));if(method==='PATCH')Object.assign(c,body);return Response.json(c);}
 if(p==='/repos/metalogiclabs/mathgraph/dispatches'){sent.push(body);return new Response(null,{status:failDispatch?503:204});}
 throw Error('UNEXPECTED_HTTP:'+method+':'+p+q);
 };
 const env={PR_PILOT_ENABLED:'true',GITHUB_APP_PRIVATE_KEY:key,PR_PILOT_BUDGET:{idFromName:x=>x,get:()=>({fetch:async()=>{reservations++;return Response.json({status:budget,reserved_cents:49});}})},PILOT_SUBSCRIPTIONS:{get:async k=>storage.has(k)?{json:async()=>JSON.parse(storage.get(k))}:null,put:async(k,v)=>storage.set(k,v),delete:async k=>storage.delete(k)}};
 return {env,fetcher,checks,sent,revoked,pr,storage,get reservations(){return reservations;}};
}
test('authenticated command queues one Check and dispatches one signed source-bound request',async()=>{const h=harness();assert.equal((await processPilotDelivery(item,h.env,{jwt:'test',fetcher:h.fetcher})).state,'DISPATCHED');assert.equal(h.checks.length,1);assert.equal(h.sent.length,1);const r=verifyDispatch(h.sent[0].client_payload,key);assert.equal(r.queued_check_id,10);assert.equal(r.base_sha,base);assert.equal(r.head_sha,sha);assert.equal(h.revoked.length,2);assert.equal((await processPilotDelivery(item,h.env,{jwt:'test',fetcher:h.fetcher})).state,'DUPLICATE');assert.equal(h.sent.length,1);assert.equal(h.reservations,1);});
test('failed dispatch settles UNKNOWN and does not redispatch the same attempt',async()=>{const h=harness({failDispatch:true});await assert.rejects(()=>processPilotDelivery(item,h.env,{jwt:'test',fetcher:h.fetcher}));assert.equal(h.checks[0].status,'completed');assert.equal(h.checks[0].output.title,'Check incomplete');assert.equal((await processPilotDelivery(item,h.env,{jwt:'test',fetcher:h.fetcher})).state,'DUPLICATE');assert.equal(h.sent.length,1);});
test('exhausted budget has visible UNKNOWN and no model dispatch',async()=>{const h=harness({budget:'BUDGET_EXHAUSTED'});assert.equal((await processPilotDelivery(item,h.env,{jwt:'test',fetcher:h.fetcher})).state,'BUDGET_EXHAUSTED');assert.equal(h.checks[0].status,'completed');assert.equal(h.sent.length,0);});
test('read-only caller cannot create a Check, reserve spend or dispatch',async()=>{const h=harness({permission:'read'});await assert.rejects(()=>processPilotDelivery(item,h.env,{jwt:'test',fetcher:h.fetcher}),/MAINTAINER_REQUIRED/);assert.equal(h.checks.length,0);assert.equal(h.sent.length,0);assert.equal(h.reservations,0);});
import {receiveWebhook} from '../cloudflare/worker.mjs';
test('pilot readiness refuses missing durable bindings',async()=>{const r=await receiveWebhook(new Request('https://worker/ready'),{GITHUB_WEBHOOK_SECRET:'present',GITHUB_APP_PRIVATE_KEY:key,PR_EVENTS:{},GITHUB_APP_CLIENT_ID:'Iv23lioiUs5KfHD7mkkw',GITHUB_APP_ID:'5308912',PR_PILOT_ENABLED:'true'});assert.equal(r.status,503);});

test('source change withdraws old applicability and dispatches only one check for the new head',async()=>{
 const h=harness();await processPilotDelivery(item,h.env,{jwt:'test',fetcher:h.fetcher});
 h.pr.head.sha='c'.repeat(40);
 const event={...item,action:'synchronize',head_sha:h.pr.head.sha,previous_sha:sha};
 assert.equal((await processPilotDelivery(event,h.env,{jwt:'test',fetcher:h.fetcher})).state,'DISPATCHED');
 assert.equal(h.checks[0].output.title,'Source changed — recheck required');
 assert.match(h.checks[0].output.summary,/Current applicability withdrawn/);
 assert.equal(h.checks[1].head_sha,h.pr.head.sha);assert.equal(h.sent.length,2);assert.equal(h.reservations,2);
 assert.equal((await processPilotDelivery(event,h.env,{jwt:'test',fetcher:h.fetcher})).state,'SOURCE_UNCHANGED');
 assert.equal(h.sent.length,2);assert.equal(h.reservations,2);
});
test('closing opted-in PR withdraws current Check and removes automatic subscription',async()=>{
 const h=harness();await processPilotDelivery(item,h.env,{jwt:'test',fetcher:h.fetcher});h.pr.state='closed';
 assert.equal((await processPilotDelivery({...item,action:'closed'},h.env,{jwt:'test',fetcher:h.fetcher})).state,'CLOSED_WITHDRAWN');
 assert.equal(h.checks[0].output.title,'Source changed — recheck required');assert.equal(h.storage.size,0);
 assert.equal((await processPilotDelivery({...item,action:'synchronize'},h.env,{jwt:'test',fetcher:h.fetcher})).state,'NOT_OPTED_IN');assert.equal(h.sent.length,1);
});
test('completed applicable check absorbs later commands without more reservation or dispatch',async()=>{
 const h=harness();await processPilotDelivery(item,h.env,{jwt:'test',fetcher:h.fetcher});
 Object.assign(h.checks[0],{status:'completed',conclusion:'neutral',output:{title:'No counterexample in generated probes',summary:'Finite evidence'}});
 assert.equal((await processPilotDelivery(item,h.env,{jwt:'test',fetcher:h.fetcher})).state,'DUPLICATE');
 assert.equal(h.sent.length,1);assert.equal(h.reservations,1);
});
