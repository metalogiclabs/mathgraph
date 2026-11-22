import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
import {runCatalogue,inspectProfileResult,parseArgs} from './run.mjs';
import {PROFILES} from './catalogue.mjs';

function receipt(id,base,head,status='OBSERVED_AGREEMENT'){
 const ids=PROFILES.find(p=>p.id===id).case_ids;
 const arm=()=>({complete:true,observations:ids.map((caseId,i)=>({id:caseId,passed:status!=='OBSERVED_MISMATCH'||i>0})),
  mismatches:status==='OBSERVED_MISMATCH'?[{id:ids[0],passed:false}]:[]});
 return {profile:id,method:{id},status,subjects:{base:{revision:base},head:{revision:head}},base:arm(),head:arm(),cost:{model_calls:0}};
}
const revisions={base:'1'.repeat(40),head:'2'.repeat(40)};

test('known status is insufficient without exact identities and complete observations',()=>{
 const p=PROFILES[0],good=receipt(p.id,revisions.base,revisions.head);
 assert.equal(inspectProfileResult(p,good,revisions).status,'OBSERVED_AGREEMENT');
 for(const mutate of [r=>{r.subjects.head.revision='3'.repeat(40);},r=>{r.head.complete=false;},
  r=>{r.head.observations=[];},r=>{r.head.observations.pop();},r=>{r.head.observations.push(r.head.observations[0]);},
  r=>{r.head.mismatches.push({id:'lost-discrepancy'});},r=>{r.method.id='other';},
  r=>{r.head.observations[0].passed=false;},
  r=>{r.head.observations=r.head.observations.map((x,i)=>({...x,id:'unrelated-case-'+i}));}]){
  const changed=structuredClone(good);mutate(changed);
  assert.equal(inspectProfileResult(p,changed,revisions).status,'UNKNOWN');
 }
});

test('unknowns preserve supplied reason and any bounded discrepancies separately',()=>{
 const r=receipt(PROFILES[0].id,revisions.base,revisions.head,'OBSERVED_MISMATCH');
 r.status='UNKNOWN';r.reason='base timed out';r.base.complete=false;
 const checked=inspectProfileResult(PROFILES[0],r,revisions);
 assert.equal(checked.status,'UNKNOWN');assert.equal(checked.reason,'base timed out');
 assert.equal(checked.head.mismatches,1);
 const unrelated=structuredClone(r);unrelated.subjects.head.revision='3'.repeat(40);
 const refused=inspectProfileResult(PROFILES[0],unrelated,revisions);
 assert.equal(refused.status,'UNKNOWN');assert.equal(refused.head,null);
 assert.match(refused.reason,/PROFILE_IDENTITY_MISMATCH/);
 const wrongMethod=structuredClone(r);wrongMethod.method.id='wrong-method';
 assert.equal(inspectProfileResult(PROFILES[0],wrongMethod,revisions).head,null);
});

test('all retained profiles run despite a failure or throw; commits freeze once',async()=>{
 const root=await mkdtemp(join(tmpdir(),'mathgraph-catalogue-'));
 try{
  const repo=join(root,'repo');await mkdir(repo);
  const git=(...args)=>{const p=spawnSync('git',['-C',repo,...args],{encoding:'utf8'});assert.equal(p.status,0,p.stderr);return p.stdout.trim();};
  git('init','-q');await writeFile(join(repo,'source.txt'),'source');git('add','.');
  git('-c','user.name=Check','-c','user.email=check@example.invalid','commit','-qm','fixture');
  const rev=git('rev-parse','HEAD'),called=[];
  const runners=Object.fromEntries(PROFILES.map((p,i)=>[p.id,async options=>{
   called.push({id:p.id,base:options.base,head:options.head});
   if(i===1)throw Error('controlled apparatus failure');
   await mkdir(options.out);const result=receipt(p.id,rev,rev,i===0?'OBSERVED_MISMATCH':'OBSERVED_AGREEMENT');
   await writeFile(join(options.out,'result.json'),JSON.stringify(result,null,2)+'\n');
   await writeFile(join(options.out,'report.md'),'bounded fixture\n');
   return {result,exit_code:i===0?1:0};
  }]));
  const out=join(root,'all');
  const run=await runCatalogue({repo,base:'HEAD',head:'HEAD',out,lean:'unused',python:'python3',timeout:120},{runners});
  assert.deepEqual(called.map(x=>x.id),PROFILES.map(p=>p.id));
  assert.ok(called.every(x=>x.base===rev&&x.head===rev));
  assert.equal(run.exit_code,2);assert.equal(run.result.status,'INCOMPLETE');
  assert.equal(run.result.profile_counts.discrepancy,1);assert.equal(run.result.profile_counts.unknown,1);
  assert.equal(run.result.coverage.items.length,104);
  const report=await readFile(join(out,'report.md'),'utf8');
  assert.match(report,/104 candidate prompts accounted for/);assert.match(report,/controlled apparatus failure/);
  assert.match(report,/UNSUPPORTED_BY_THIS_COMMAND/);assert.doesNotMatch(report,/104.*(?:pass|fully covered)/i);
  await assert.rejects(runCatalogue({repo,base:rev,head:rev,out},{runners}),/OUTPUT_ALREADY_EXISTS/);
  called.length=0;
  const partial=await runCatalogue({repo,base:rev,head:rev,out:join(root,'partial'),profiles:[PROFILES[2].id],timeout:120},{runners});
  assert.equal(called.length,1);assert.equal(partial.result.profile_counts.not_run,3);
  assert.equal(partial.result.status,'INCOMPLETE');assert.equal(partial.exit_code,2);
  assert.ok(partial.result.coverage.items.some(x=>x.status==='NOT_RUN'));
 }finally{await rm(root,{recursive:true,force:true});}
});

test('argument errors are explicit and cannot quietly narrow the method set',()=>{
 const common=['--repo','repo','--base','A','--head','B','--out','out'];
 assert.equal(parseArgs(common).profiles.length,4);
 assert.throws(()=>parseArgs([...common,'--profiles','invented']),/UNSUPPORTED_PROFILE/);
 assert.throws(()=>parseArgs([...common,'--profiles',PROFILES[0].id+','+PROFILES[0].id]),/DUPLICATE_PROFILE/);
 assert.throws(()=>parseArgs([...common,'--timeout-seconds','NaN']),/INVALID_TIMEOUT/);
});
