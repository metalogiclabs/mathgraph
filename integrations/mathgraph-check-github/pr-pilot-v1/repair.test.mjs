import test from 'node:test';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';import {createRepair} from './repair.mjs';
const repository='metalogiclabs/L4YAML',head='a'.repeat(40),base='b'.repeat(40),tree='c'.repeat(40),commit='d'.repeat(40),path='Scripts/Ledger.lean',content='def x := true\n';
const request={repository,number:2,head_sha:head,base_sha:base,profile:{path}},patch={content,patched_sha256:createHash('sha256').update(content).digest('hex')};
function h(move=false){let reads=0;const writes=[];const root='/repos/'+repository;const pr={state:'open',head:{sha:head,ref:'feature',repo:{full_name:repository}},base:{sha:base}};const blob=createHash('sha1').update('blob '+Buffer.byteLength(content)+'\0'+content).digest('hex');const api=async(p,o={})=>{if(o.method)writes.push({p,...o});if(p===root+'/pulls/2'){reads++;return move&&reads>=3?{...pr,head:{...pr.head,sha:'f'.repeat(40)}}:pr;}if(p===root+'/git/commits/'+head)return {tree:{sha:tree}};if(p===root+'/git/trees'){assert.equal(o.body.base_tree,tree);return {sha:'e'.repeat(40)};}if(p===root+'/git/commits')return {sha:commit};if(p===root+'/compare/'+head+'...'+commit)return {files:[{filename:path,status:'modified',sha:blob}]};if(p===root+'/git/refs')return {object:{sha:commit}};if(p.includes('/git/ref/heads/'))return {object:{sha:commit}};if(o.method==='DELETE')return {};if(p.includes('/pulls?'))return [];if(p===root+'/pulls')return {draft:true,base:{sha:head},html_url:'https://github.com/'+repository+'/pull/3'};throw Error(p);};return {api,writes};}
test('repair uses real tree SHA and only the verified source path',async()=>{const x=h();assert.equal(await createRepair(request,patch,{run_url:'https://github.com/metalogiclabs/mathgraph/actions/runs/1'},x.api),'https://github.com/metalogiclabs/L4YAML/pull/3');assert.equal(x.writes.find(w=>w.p.endsWith('/pulls')).body.draft,true);});
test('head moving after owned ref creation cleans that exact ref and refuses draft',async()=>{const x=h(true);await assert.rejects(()=>createRepair(request,patch,{run_url:'https://github.com/metalogiclabs/mathgraph/actions/runs/1'},x.api),/STALE_REPAIR/);assert.equal(x.writes.filter(w=>w.method==='DELETE').length,1);assert.equal(x.writes.filter(w=>w.p.endsWith('/pulls')).length,0);});
test('existing exact qualified draft is reused without another branch or PR',async()=>{
 const x=h(),candidate={number:26,draft:true,state:'open',base:{sha:head},head:{sha:'9'.repeat(40),repo:{full_name:repository}},html_url:'https://github.com/'+repository+'/pull/26'};
 const api=async(p,o)=>p.includes('/pulls?state=open&base=')?[candidate]:p.endsWith('/git/commits/'+candidate.head.sha)?{tree:{sha:'e'.repeat(40)},parents:[{sha:head}]}:p.endsWith('/pulls/26')?candidate:x.api(p,o);
 assert.equal(await createRepair(request,patch,{run_url:'https://github.com/metalogiclabs/mathgraph/actions/runs/1'},api),candidate.html_url);
 assert.equal(x.writes.filter(w=>w.p.endsWith('/git/refs')||w.p.endsWith('/pulls')).length,0);
});
test('exact draft beyond the first hundred is reused',async()=>{
 const x=h(),candidate={number:126,draft:true,state:'open',base:{sha:head},head:{sha:'9'.repeat(40),repo:{full_name:repository}},html_url:'https://github.com/'+repository+'/pull/126'};
 const api=async(p,o)=>p.includes('/pulls?state=open&base=')?(p.endsWith('&page=2')?[candidate]:Array.from({length:100},()=>({draft:false}))):p.endsWith('/git/commits/'+candidate.head.sha)?{tree:{sha:'e'.repeat(40)},parents:[{sha:head}]}:p.endsWith('/pulls/126')?candidate:x.api(p,o);
 assert.equal(await createRepair(request,patch,{run_url:'https://github.com/metalogiclabs/mathgraph/actions/runs/1'},api),candidate.html_url);
 assert.equal(x.writes.filter(w=>w.p.endsWith('/git/refs')||w.p.endsWith('/pulls')).length,0);
});
test('incomplete draft history refuses duplicate publication',async()=>{
 const x=h(),api=async(p,o)=>p.includes('/pulls?state=open&base=')?Array.from({length:100},()=>({draft:false})):x.api(p,o);
 await assert.rejects(()=>createRepair(request,patch,{run_url:'https://github.com/metalogiclabs/mathgraph/actions/runs/1'},api),/INCOMPLETE_REPAIR_HISTORY/);
 assert.equal(x.writes.filter(w=>w.p.endsWith('/git/refs')||w.p.endsWith('/pulls')).length,0);
});
