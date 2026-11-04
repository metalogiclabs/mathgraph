import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtemp,writeFile,readFile,rm} from 'node:fs/promises';import {tmpdir} from 'node:os';import {join} from 'node:path';import {spawnSync} from 'node:child_process';import {createHash} from 'node:crypto';
test('an incomplete stage preserves the acquired subject and reason',async()=>{
 const dir=await mkdtemp(join(tmpdir(),'mg-unknown-'));
 try{
 const context={verifier_sha:'a'.repeat(40),run_id:123,attempt:1};
 const objects={'state.json':{context,state:'UNKNOWN',stage:'native-initial',reason:'DEPENDENCY_SETUP_FAILED'},'snapshot.json':{repository:'metalogiclabs/gnss_lib_py',source_repository:'Stanford-NavLab/gnss_lib_py',pr:1,base_sha:'b'.repeat(40),head_sha:'c'.repeat(40)}};
 const hashes={};for(const [name,data]of Object.entries(objects)){const text=JSON.stringify(data);await writeFile(join(dir,name),text);hashes[name]=createHash('sha256').update(text).digest('hex');}
 await writeFile(join(dir,'manifest.json'),JSON.stringify({context,hashes}));
 const p=spawnSync(process.execPath,[new URL('./driver.mjs',import.meta.url).pathname,'assess',dir],{encoding:'utf8',env:{...process.env,GITHUB_SHA:context.verifier_sha,GITHUB_RUN_ID:'123',GITHUB_RUN_ATTEMPT:'1'}});assert.equal(p.status,0,p.stderr);
 const r=JSON.parse(await readFile(join(dir,'assessment.json'),'utf8'));assert.equal(r.status,'UNKNOWN');assert.equal(r.stage,'native-initial');assert.equal(r.subject.head_sha,'c'.repeat(40));assert.equal(r.reason,'DEPENDENCY_SETUP_FAILED');
 }finally{await rm(dir,{recursive:true,force:true});}
});

test('a failure already present on base cannot purchase a head-regression repair',async()=>{
 const dir=await mkdtemp(join(tmpdir(),'mg-matched-failures-'));
 try{
  const sha='a'.repeat(40),baseSha='b'.repeat(40),context={verifier_sha:'c'.repeat(40),run_id:124,attempt:1};
  const code='def test_before_and_after():\n    assert 2 + 2 == 5\n';
  const hash=x=>createHash('sha256').update(typeof x==='string'?x:JSON.stringify(x)).digest('hex');
  const plan={summary:'An unverified assertion',tests:[{id:'before_and_after',hypothesis:'Both revisions fail',contract:'Proposed only',source_path:'gnss_lib_py/utils/coordinates.py',code}]};
  const testDigest=hash(plan.tests),fileDigest=hash(code);
  const snapshot={repository:'metalogiclabs/gnss_lib_py',base_sha:baseSha,head_sha:sha,files:[{path:plan.tests[0].source_path,base:'pass\n',head:'pass\n'}]};
  const receipt=subject=>({id:plan.tests[0].id,subject_sha:subject,test_digest:testDigest,test_file_sha256:fileDigest,exit_code:1,tests:1,failures:1,errors:0,skipped:0,timeout:false,cases:[{id:'test_before_and_after',status:'failed',exception:'AssertionError',assertions_reached:1,subject_lines_reached:1}]});
  const protectedReceipt=subject=>({subject_sha:subject,test_digest:'e'.repeat(64),exit_code:0,tests:1,failures:0,errors:0,skipped:0,timeout:false,cases:[{id:'test_protected',status:'passed',exception:null,assertions_reached:1}]});
  const native={verifier_sha:context.verifier_sha,head_sha:sha,test_digest:testDigest,arms:{base:{probes:[receipt(baseSha)],protected:protectedReceipt(baseSha)},head:{probes:[receipt(sha)],protected:protectedReceipt(sha)}}};
  const objects={'state.json':{context,state:'PROBES_PROPOSED',test_digest:testDigest},'snapshot.json':snapshot,'plan.json':plan,'native.json':native};
  const hashes={};for(const [name,data]of Object.entries(objects)){const json=JSON.stringify(data);await writeFile(join(dir,name),json);hashes[name]=hash(json);}
  await writeFile(join(dir,'manifest.json'),JSON.stringify({context,hashes}));
  const readOnly=spawnSync(process.execPath,[new URL('./driver.mjs',import.meta.url).pathname,'assess',dir],{encoding:'utf8',env:{...process.env,GITHUB_SHA:context.verifier_sha,GITHUB_RUN_ID:'124',GITHUB_RUN_ATTEMPT:'1'}});
  assert.equal(readOnly.status,0,readOnly.stderr);
  const initialReport=JSON.parse(await readFile(join(dir,'assessment.json'),'utf8'));
  assert.equal(initialReport.repair.status,'NOT_REQUESTED');
  assert.equal(initialReport.counts.shared_failures,1);
  const p=spawnSync(process.execPath,[new URL('./driver.mjs',import.meta.url).pathname,'repair',dir],{encoding:'utf8',env:{...process.env,OPENAI_API_KEY:'',GITHUB_SHA:context.verifier_sha,GITHUB_RUN_ID:'124',GITHUB_RUN_ATTEMPT:'1'}});
  assert.equal(p.status,0,p.stderr);
  const outcome=JSON.parse(await readFile(join(dir,'repair-state.json'),'utf8'));
  assert.equal(outcome.state,'NO_HEAD_ONLY_FAILURE');
  assert.equal(outcome.model_calls,0);
  assert.equal(outcome.deltas[0].status,'SHARED_FAILURE');
  const assess=spawnSync(process.execPath,[new URL('./driver.mjs',import.meta.url).pathname,'assess',dir],{encoding:'utf8',env:{...process.env,GITHUB_SHA:context.verifier_sha,GITHUB_RUN_ID:'124',GITHUB_RUN_ATTEMPT:'1'}});
  assert.equal(assess.status,0,assess.stderr);
  const report=JSON.parse(await readFile(join(dir,'assessment.json'),'utf8'));
  assert.equal(report.status,'SHARED_FAILURE_NOT_ATTRIBUTED');
  assert.equal(report.counts.head_only_failures,0);
  assert.equal(report.counts.shared_failures,1);
  assert.equal(report.repair.status,'NO_HEAD_ONLY_FAILURE');
  assert.equal(report.meaning,'UNVERIFIED');
 }finally{await rm(dir,{recursive:true,force:true});}
});
