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
