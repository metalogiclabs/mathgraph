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
