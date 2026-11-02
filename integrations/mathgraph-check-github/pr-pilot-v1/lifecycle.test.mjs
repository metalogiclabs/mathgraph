import test from 'node:test';import assert from 'node:assert/strict';
import {authenticate,startCheck,finishCheck,withdrawChecks} from './lifecycle.mjs';
const repository='metalogiclabs/L4YAML',head='a'.repeat(40),base='b'.repeat(40),root='/repos/'+repository;
function harness({moved=false,permission='write',wrongIssue=false}={}){
 const writes=[],checks=[];let reads=0;
 const pr={number:2,state:'open',changed_files:1,head:{sha:head,ref:'feature',repo:{full_name:repository,private:false}},base:{sha:base,repo:{full_name:repository,private:false}}};
 const comment={id:7,body:'@MathGraph -check',issue_url:'https://api.github.com'+root+'/issues/'+(wrongIssue?3:2),user:{id:99,login:'maintainer',type:'User'}};
 const api=async(path,opts={})=>{if(opts.method){writes.push({path,...opts});if(path===root+'/check-runs'){const c={...opts.body,id:10+checks.length,app:{id:5308912}};checks.push(c);return c;}if(/check-runs\/\d+$/.test(path)){const c=checks.find(c=>path.endsWith('/'+c.id));Object.assign(c,opts.body);return c;}throw Error('UNEXPECTED_WRITE');}
 if(path===root+'/pulls/2'){reads++;return moved&&reads>1?{...pr,head:{...pr.head,sha:'c'.repeat(40)}}:pr;}
 if(path===root+'/issues/comments/7')return comment;
 if(path===root+'/collaborators/maintainer/permission')return {permission};
 if(path===root+'/pulls/2/files?per_page=100&page=1')return [{filename:'Scripts/Ledger.lean',status:'modified'}];
 if(path===root+'/commits/'+head+'/check-runs?per_page=100&filter=all&page=1')return {total_count:checks.length,check_runs:checks};
 if(/check-runs\/\d+$/.test(path))return checks.find(c=>path.endsWith('/'+c.id));throw Error('UNEXPECTED_READ:'+path);};
 return {api,writes,checks,pr};
}
const payload={repository,number:2,comment_id:7,command:'check'};
test('authenticates actual comment ownership and collaborator permission',async()=>{const h=harness();const r=await authenticate(payload,h.api);assert.equal(r.actor_id,99);for(const opts of [{permission:'read'},{wrongIssue:true}])await assert.rejects(()=>authenticate(payload,harness(opts).api));});
test('same-head duplicate does not reserve another execution',async()=>{const h=harness(),r=await authenticate(payload,h.api);const a=await startCheck(r,h.api,'https://github.com/metalogiclabs/mathgraph/actions/runs/1');const b=await startCheck(r,h.api,'https://github.com/metalogiclabs/mathgraph/actions/runs/2');assert.equal(a.state,'STARTED');assert.equal(b.state,'DUPLICATE');assert.equal(h.writes.length,1);});
test('fresh result updates original registered Check with finite-scope message',async()=>{const h=harness(),r=await authenticate(payload,h.api),p=await startCheck(r,h.api,'https://github.com/metalogiclabs/mathgraph/actions/runs/1');const f=await finishCheck(r,p,{status:'NO_COUNTEREXAMPLE_IN_GENERATED_GUARDS'},h.api);assert.equal(f.state,'PUBLISHED');assert.equal(h.checks[0].head_sha,head);assert.equal(h.checks[0].conclusion,'neutral');assert.match(h.checks[0].output.summary,/not.*correctness/);});
test('moving source withdraws applicability rather than publishing pass',async()=>{const h=harness({moved:true}),r=await authenticate(payload,h.api),p=await startCheck(r,h.api,'https://github.com/metalogiclabs/mathgraph/actions/runs/1');const f=await finishCheck(r,p,{status:'NO_COUNTEREXAMPLE_IN_GENERATED_GUARDS'},h.api);assert.equal(f.state,'STALE');assert.match(h.checks[0].output.title,/Source changed/);});
test('missing assessment settles UNKNOWN',async()=>{const h=harness(),r=await authenticate(payload,h.api),p=await startCheck(r,h.api,'https://github.com/metalogiclabs/mathgraph/actions/runs/1');await finishCheck(r,p,null,h.api);assert.match(h.checks[0].output.title,/incomplete/);});
test('foreign publisher cannot be updated and historical results remain',async()=>{const h=harness(),r=await authenticate(payload,h.api),p=await startCheck(r,h.api,'https://github.com/metalogiclabs/mathgraph/actions/runs/1');h.checks[0].app.id=1;await assert.rejects(()=>finishCheck(r,p,{status:'NO_COUNTEREXAMPLE_IN_GENERATED_GUARDS'},h.api));});
test('withdrawal updates only this PR and this App, preserving historical summary',async()=>{const checks=[{id:1,app:{id:5308912},external_id:`mg-pr-v1:${repository}#2@${base}:check`,head_sha:base,output:{summary:'historical evidence'}},{id:2,app:{id:5308912},external_id:`mg-pr-v1:${repository}#3@${base}:check`,head_sha:base,output:{summary:'other PR'}}];const writes=[];const api=async(path,o)=>{writes.push(o.body);return {...checks[0],...o.body}};assert.equal(await withdrawChecks({repository,number:2,head_sha:head},checks,api),1);assert.match(writes[0].output.summary,/historical evidence/);});
test('base-only changes require distinct evidence identity',async()=>{const h=harness(),r=await authenticate(payload,h.api);const a=await startCheck(r,h.api,'https://github.com/metalogiclabs/mathgraph/actions/runs/1'),b=await startCheck({...r,base_sha:'d'.repeat(40)},h.api,'https://github.com/metalogiclabs/mathgraph/actions/runs/2');assert.equal(a.state,'STARTED');assert.equal(b.state,'STARTED');});
test('new authorized command may retry a terminal UNKNOWN without duplicating same attempt',async()=>{const h=harness(),r=await authenticate(payload,h.api);const a=await startCheck(r,h.api,'https://github.com/metalogiclabs/mathgraph/actions/runs/1');await finishCheck(r,a,null,h.api);const same=await startCheck(r,h.api,'https://github.com/metalogiclabs/mathgraph/actions/runs/2');assert.equal(same.state,'DUPLICATE');const next=await startCheck({...r,comment_id:8},h.api,'https://github.com/metalogiclabs/mathgraph/actions/runs/3');assert.equal(next.state,'STARTED');});
import {queueCheck} from './lifecycle.mjs';
test('queued registered Check is claimed once by its authenticated dispatch',async()=>{const h=harness(),r=await authenticate(payload,h.api),q=await queueCheck(r,h.api);assert.equal(q.state,'QUEUED');const request={...r,queued_check_id:q.check_id};const a=await startCheck(request,h.api,'https://github.com/metalogiclabs/mathgraph/actions/runs/1'),b=await startCheck(request,h.api,'https://github.com/metalogiclabs/mathgraph/actions/runs/2');assert.equal(a.state,'STARTED');assert.equal(b.state,'DUPLICATE');assert.equal(h.checks.length,1);});

test('completed fix Check title describes the qualified repair rather than the old failure',async()=>{
 const h=harness(),r={...await authenticate(payload,h.api),command:'fix'},p=await startCheck(r,h.api,'https://github.com/metalogiclabs/mathgraph/actions/runs/1');
 await finishCheck(r,p,{status:'CANDIDATE_ASSERTION_FAILURE',repair:{status:'PATCH_PASSES_FROZEN_GUARDS_AND_REPOSITORY_GATE'},repair_pr:'https://github.com/metalogiclabs/L4YAML/pull/3'},h.api);
 assert.match(h.checks[0].output.title,/Candidate repair verified/);
});

test('same commit on different PRs has distinct visible Check names',async()=>{
 const h=harness(),r=await authenticate(payload,h.api);
 await startCheck(r,h.api,'https://github.com/metalogiclabs/mathgraph/actions/runs/1');
 await startCheck({...r,number:3},h.api,'https://github.com/metalogiclabs/mathgraph/actions/runs/2');
 assert.notEqual(h.checks[0].name,h.checks[1].name);assert.match(h.checks[0].name,/#2/);assert.match(h.checks[1].name,/#3/);
});

test('new command after reopening same source does not reuse withdrawn applicability',async()=>{
 const h=harness(),r=await authenticate(payload,h.api),p=await startCheck(r,h.api,'https://github.com/metalogiclabs/mathgraph/actions/runs/1');
 h.pr.state='closed';await finishCheck(r,p,{status:'NO_COUNTEREXAMPLE_IN_GENERATED_GUARDS'},h.api);assert.match(h.checks[0].output.title,/Source changed/);
 h.pr.state='open';
 const same=await queueCheck(r,h.api);assert.equal(same.state,'DUPLICATE');
 const next=await queueCheck({...r,comment_id:8},h.api);assert.equal(next.state,'QUEUED');assert.equal(h.checks.length,2);
});
