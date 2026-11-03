import test from 'node:test';import assert from 'node:assert/strict';import {mkdtemp,writeFile,readFile,rm} from 'node:fs/promises';import {tmpdir} from 'node:os';import {join} from 'node:path';import {spawnSync} from 'node:child_process';import {createHash} from 'node:crypto';
const hash=x=>createHash('sha256').update(x).digest('hex');
for(const stale of [true,false])test(stale?'foreign native run cannot qualify':'failed build still yields a source-bound UNKNOWN assessment',async()=>{
 const dir=await mkdtemp(join(tmpdir(),'mg-lean-admit-'));try{
 const context={verifier_sha:'a'.repeat(40),run_id:123,attempt:1},source='def x := true\n';
 const plan={summary:'probe',tests:[{id:'case_a',hypothesis:'boundary',contract:'API contract',expression:'true'}]};
 const snapshot={repository:'metalogiclabs/L4YAML',head_sha:'b'.repeat(40),path:'Example.lean',module:'Example',namespace:'Example',source,source_sha256:hash(source)};
 const native={context:stale?{...context,run_id:124}:context,source_sha:snapshot.head_sha,test_digest:hash(JSON.stringify(plan.tests)),arm:{build_exit:1,source_sha256:hash(source),probes:[],repository_gate_exit:null}};
 const objects={'snapshot.json':snapshot,'state.json':{context,state:'PROBES_PROPOSED',test_digest:native.test_digest},'plan.json':plan,'native.json':native,'repair-state.json':{state:'NO_REPRODUCED_FAILURE'}};const hashes={};
 for(const[name,data]of Object.entries(objects)){const raw=JSON.stringify(data);await writeFile(join(dir,name),raw);hashes[name]=hash(raw);}
 await writeFile(join(dir,'manifest.json'),JSON.stringify({context,hashes}));
 const {MATHGRAPH_CONTROLLER_SHA:ambientController,...testEnv}=process.env;
 const p=spawnSync(process.execPath,[new URL('./driver.mjs',import.meta.url).pathname,'assess',dir],{encoding:'utf8',env:{...testEnv,GITHUB_SHA:context.verifier_sha,GITHUB_RUN_ID:'123',GITHUB_RUN_ATTEMPT:'1'}});assert.equal(p.status,0,p.stderr);
 const r=JSON.parse(await readFile(join(dir,'assessment.json'),'utf8'));assert.equal(r.status,'UNKNOWN');assert.equal(r.subject.head_sha,snapshot.head_sha);if(stale)assert.equal(r.reason,'NATIVE_SOURCE_MISMATCH');
 }finally{await rm(dir,{recursive:true,force:true});}
});

import {renderProbe} from './contracts.mjs';
test('hosted unreviewed expectation cannot call the repair model',async()=>{
 const dir=await mkdtemp(join(tmpdir(),'mg-expectation-gate-'));try{
 const context={verifier_sha:'a'.repeat(40),run_id:123,attempt:1},source='def x := true\n';
 const snapshot={repository:'metalogiclabs/L4YAML',head_sha:'b'.repeat(40),path:'Scripts/Ledger.lean',module:'Example',namespace:'Example',source,source_sha256:hash(source),cli_source:'cli',toolchain:'leanprover/lean4:v4.35.0',mode:'OWNED_FORK_PR_PILOT',command:'fix'};
 const plan={summary:'hypothesis',tests:[{id:'hypothesis',hypothesis:'unverified',contract:'model claim',expression:'false'}]};
 const pass={exit_code:0,guard_false:false,other_errors:false},fail={exit_code:1,guard_false:true,other_errors:false};
 const native={context,source_sha:snapshot.head_sha,test_digest:hash(JSON.stringify(plan.tests)),arm:{build_exit:0,repository_gate_exit:0,source_sha256:hash(source),controls:{pass,fail},probes:[{id:'hypothesis',...fail,test_file_sha256:hash(renderProbe(snapshot,'false'))}]}};
 const values={'snapshot.json':snapshot,'state.json':{context,state:'PROBES_PROPOSED',test_digest:native.test_digest},'plan.json':plan,'native.json':native},hashes={};
 for(const[n,v]of Object.entries(values)){const raw=JSON.stringify(v);await writeFile(join(dir,n),raw);hashes[n]=hash(raw);}await writeFile(join(dir,'manifest.json'),JSON.stringify({context,hashes}));
 const {MATHGRAPH_CONTROLLER_SHA:ambient,OPENAI_API_KEY:unused,...env}=process.env;
 const r=spawnSync(process.execPath,[new URL('./driver.mjs',import.meta.url).pathname,'repair',dir],{encoding:'utf8',env:{...env,GITHUB_SHA:context.verifier_sha,GITHUB_RUN_ID:'123',GITHUB_RUN_ATTEMPT:'1'}});
 assert.equal(r.status,0,r.stderr);const rs=JSON.parse(await readFile(join(dir,'repair-state.json'),'utf8'));assert.equal(rs.state,'EXPECTATION_NOT_ADMITTED');assert.equal(rs.model_calls,0);await assert.rejects(readFile(join(dir,'model-repair.json')),{code:'ENOENT'});
 }finally{await rm(dir,{recursive:true,force:true});}
});
for(const failure of ['controls','gate','source'])test(`unqualified head ${failure} cannot authorize a new-regression label`,async()=>{
 const dir=await mkdtemp(join(tmpdir(),'mg-head-qualified-'));try{
 const context={verifier_sha:'a'.repeat(40),run_id:123,attempt:1},source='def x := true\n';
 const snapshot={repository:'metalogiclabs/L4YAML',head_sha:'b'.repeat(40),base_sha:'c'.repeat(40),base_source:source,path:'Example.lean',module:'Example',namespace:'Example',source,source_sha256:hash(source)};
 const plan={summary:'probe',tests:[{id:'case_a',hypothesis:'boundary',contract:'API contract',expression:'true'}]};
 const pass={exit_code:0,guard_false:false,other_errors:false},fail={exit_code:1,guard_false:true,other_errors:false};
 const arm={build_exit:0,repository_gate_exit:0,source_sha256:hash(source),controls:{pass,fail},probes:[{id:'case_a',...pass,test_file_sha256:hash(renderProbe(snapshot,'true'))}]};
 const head={...arm,controls:{...arm.controls},probes:[{...arm.probes[0],...fail}]};
 if(failure==='controls')head.controls.fail=pass;if(failure==='gate')head.repository_gate_exit=1;if(failure==='source')head.source_sha256='d'.repeat(64);
 const native={context,source_sha:snapshot.head_sha,base_sha:snapshot.base_sha,test_digest:hash(JSON.stringify(plan.tests)),arm:head,base_arm:arm};
 const values={'snapshot.json':snapshot,'state.json':{context,state:'PROBES_PROPOSED',test_digest:native.test_digest},'plan.json':plan,'native.json':native,'repair-state.json':{state:'NO_REPRODUCED_FAILURE'}},hashes={};
 for(const [n,v]of Object.entries(values)){const raw=JSON.stringify(v);await writeFile(join(dir,n),raw);hashes[n]=hash(raw);}
 await writeFile(join(dir,'manifest.json'),JSON.stringify({context,hashes}));
 const {MATHGRAPH_CONTROLLER_SHA:ambient,...env}=process.env;
 const run=spawnSync(process.execPath,[new URL('./driver.mjs',import.meta.url).pathname,'assess',dir],{encoding:'utf8',env:{...env,GITHUB_SHA:context.verifier_sha,GITHUB_RUN_ID:'123',GITHUB_RUN_ATTEMPT:'1'}});assert.equal(run.status,0,run.stderr);
 const report=JSON.parse(await readFile(join(dir,'assessment.json'),'utf8'));assert.equal(report.status,'UNKNOWN');assert.equal(report.original[0].execution,'UNKNOWN');assert.equal(report.comparison[0].change,'HEAD_UNKNOWN');
 }finally{await rm(dir,{recursive:true,force:true});}
});
