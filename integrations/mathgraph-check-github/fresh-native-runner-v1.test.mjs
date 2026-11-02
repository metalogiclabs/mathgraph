import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtemp,rm} from 'node:fs/promises';import {join} from 'node:path';import {tmpdir} from 'node:os';
const m=await import('./fresh-native-runner-v1.mjs').catch(()=>({}));
const absent=()=>Object.assign(Error('absent'),{code:1,stderr:'Error: No such object: container'});
test('client timeouts force-remove the named container and confirm absence before returning',async()=>{
 const directory=await mkdtemp(join(tmpdir(),'fresh-runner-')),calls=[];
 try{const run=await m.freshNativeRunner({directory,dependencyDirectory:'/trusted',resolveDependencies:async()=>[],execute:async(cmd,args,options)=>{calls.push({cmd,args,options});if(args[0]==='run')throw Object.assign(Error('timeout'),{killed:true});if(args[0]==='inspect')throw absent();return {stdout:'',stderr:''};}});
 await assert.rejects(run('Candidate','proof'),/NATIVE_RESOURCE_LIMIT/);assert.deepEqual(calls.map(x=>x.args[0]),['run','rm','inspect']);assert.equal(calls[0].args[calls[0].args.indexOf('--name')+1],calls[1].args.at(-1));assert.equal(calls[1].args[1],'-f');assert.deepEqual(Object.keys(calls[0].options.env),['PATH']);assert.equal(calls[0].options.killSignal,'SIGKILL');}finally{await rm(directory,{recursive:true,force:true});}
});
test('unconfirmed cleanup is fatal, while ordinary compile errors retain diagnostics',async()=>{
 const directory=await mkdtemp(join(tmpdir(),'fresh-runner-'));
 try{
 const stuck=await m.freshNativeRunner({directory,dependencyDirectory:'/trusted',resolveDependencies:async()=>[],execute:async(cmd,args)=>({stdout:args[0]==='inspect'?'still present':'',stderr:''})});await assert.rejects(stuck('Candidate','proof'),/NATIVE_CLEANUP_UNCONFIRMED/);
 const run=await m.freshNativeRunner({directory,dependencyDirectory:'/trusted',resolveDependencies:async()=>[],execute:async(cmd,args)=>{if(args[0]==='run')throw Object.assign(Error('compiler'),{code:1,stdout:'type mismatch',stderr:''});if(args[0]==='inspect')throw absent();return {stdout:'',stderr:''};}});assert.deepEqual(await run('Candidate','proof'),{code:1,output:'type mismatch'});
 }finally{await rm(directory,{recursive:true,force:true});}
});
