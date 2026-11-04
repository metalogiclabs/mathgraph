import fs from 'node:fs/promises';import {createHash} from 'node:crypto';import assert from 'node:assert/strict';
import {admitRequest} from './policy.mjs';import {executionContext} from './context.mjs';import {admitProfilePatch} from './traceof-comments.mjs';import {reportView} from './report-view.mjs';
const [phase,dir='selfserve',number='6']=process.argv.slice(2),context=executionContext(),hash=s=>createHash('sha256').update(s).digest('hex');
const get=async n=>JSON.parse(await fs.readFile(dir+'/'+n+'.json','utf8')),put=async(n,v)=>fs.writeFile(dir+'/'+n+'.json',JSON.stringify(v,null,2)+'\n');
async function seal(){const hashes={};for(const n of(await fs.readdir(dir)).filter(n=>n.endsWith('.json')&&n!=='manifest.json').sort())hashes[n]=hash(await fs.readFile(dir+'/'+n));await put('manifest',{context,hashes});}
async function api(path){const r=await fetch('https://api.github.com'+path,{headers:{Accept:'application/vnd.github+json',...(process.env.GITHUB_TOKEN?{Authorization:'Bearer '+process.env.GITHUB_TOKEN}:{})}});assert(r.ok,'READ_ONLY_ACQUISITION_HTTP_'+r.status);return r.json();}
if(phase==='prepare'){
 assert(['6','34','37'].includes(number));const repository='metalogiclabs/L4YAML',root='/repos/'+repository,pr=await api(root+'/pulls/'+number),files=await api(root+'/pulls/'+number+'/files?per_page=100');
 // Explicit adapter qualification, never an authenticated human command.
 const request=admitRequest({repository,pr,files,filesComplete:files.length===pr.changed_files,permission:'read',pilotOperators:[707],comment:{id:context.run_id,body:'@MathGraph -check',user:{id:707,login:'invited-reader',type:'User'}}});request.qualification_only=true;
 await fs.mkdir(dir,{recursive:true});await put('request',request);await put('publication',{state:'QUALIFICATION_ONLY',context});await seal();
}else if(phase==='patch'){
 const snapshot=await get('snapshot'),request=await get('request');assert([6,37].includes(request.number));snapshot.command='fix';request.command='fix';await put('snapshot',snapshot);await put('request',request);await seal();
}else if(phase==='require'){
 const a=await get('assessment'),r=await get('request'),state=await get('state');assert.equal(state.state,'PROBES_PROPOSED');assert.equal(state.model_calls,0);assert.equal(a.head_complete,true);assert.equal(a.expectations.status,'ADMITTED');assert.equal(a.expectations.input_count,number==='37'?19:20);assert.equal(a.expectations.requirement_count,3);assert.equal(a.baseline.source_ok,true);assert.equal(a.baseline.controls_ok,true);assert.match(reportView(a,r).scope,/not the repository test suite/);
 if(['6','37'].includes(number)){assert.equal((await get('repair-state')).model_calls,0);assert.equal((await get('patch')).producer,'QUALIFIED_CANDIDATE_REUSE');assert.equal(a.repair.status,'PATCH_PASSES_FROZEN_GUARDS_AND_REPOSITORY_GATE');assert.equal(a.repair.protected_guards,number==='37'?23:22);assert.deepEqual(a.repair.repository_gate_exits,[0,0,0]);assert.equal(reportView(a,r).title,number==='37'?'Report repair verified':'Candidate repair verified on frozen probes');}else assert.equal(a.status,'NO_COUNTEREXAMPLE_IN_GENERATED_GUARDS');
 console.log(JSON.stringify({qualification_only:true,pr:r.number,status:a.status,requirements:3,inputs:20,repair:a.repair.status,scope:a.scope}));
}else throw Error('UNKNOWN_PHASE');
