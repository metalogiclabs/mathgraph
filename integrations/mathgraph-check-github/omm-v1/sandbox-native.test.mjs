import test from 'node:test';
import assert from 'node:assert/strict';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {sandboxDockerArgs,runIsolatedLeanSource} from './sandbox-native.mjs';

const candidate=join(tmpdir(),'omm-lean-abc123','Submission.lean');

test('Docker boundary has one read-only input, no network, no privileges and hard resource caps',()=>{
 const args=sandboxDockerArgs({sourcePath:candidate});
 assert.deepEqual(args.slice(0,2),['run','--rm']);
 assert.match(args[args.indexOf('--name')+1],/^mathgraph-omm-[-A-Za-z0-9_]+$/);
 assert.deepEqual(args.slice(-3),['-o','/tmp/Submission.olean','/work/Submission.lean']);
 const joined=args.join(' ');
 for(const item of ['--network none','--read-only','--cap-drop ALL','--security-opt no-new-privileges',
  '--pids-limit 32','--memory 512m','--memory-swap 512m','--cpus 1',
  '--user 65534:65534','--pull never','--ipc none',
  'type=bind,src='+candidate+',dst=/work/Submission.lean,readonly'])assert.ok(joined.includes(item),item);
 assert.equal(joined.includes('GITHUB_TOKEN'),false);
 assert.equal(joined.includes('/var/run/docker.sock'),false);
 assert.equal(joined.includes(',dst=/work,readonly'),false);
 assert.equal(args.filter(x=>x==='--mount').length,1);
});

test('arbitrary mount path, escape, noncanonical source and image override cannot cross the boundary',()=>{
 for(const bad of ['/etc/passwd',join(tmpdir(),'other','Submission.lean'),
   join(tmpdir(),'omm-lean-abc123','../Submission.lean'),
   candidate+',dst=/etc/passwd'])assert.throws(()=>sandboxDockerArgs({sourcePath:bad}),/UNSAFE_SANDBOX_SOURCE/);
 assert.throws(()=>sandboxDockerArgs({sourcePath:candidate,image:'ubuntu:latest'}),/UNSUPPORTED_SANDBOX_OPTION/);
});

test('isolated runner keeps host credentials out and reports positive and negative native exits separately',async()=>{
 const invocations=[];
 const run=async(command,args,opts)=>{
  invocations.push({command,args,opts});
  return {stdout:'Lean output',stderr:''};
 };
 const accepted=await runIsolatedLeanSource({source:'import Init\nexample : True := by trivial\n',run});
 assert.equal(accepted.status,'LEAN_ACCEPTED');
 assert.equal(accepted.exit_code,0);
 assert.equal(invocations.length,2);
 assert.equal(invocations[0].command,'docker');
 assert.deepEqual(invocations[1].args.slice(0,2),['rm','-f']);
 assert.equal(invocations[1].args[2],invocations[0].args[invocations[0].args.indexOf('--name')+1]);
 assert.deepEqual(Object.keys(invocations[0].opts.env),['PATH']);
 assert.ok(invocations[0].opts.timeout<=60000);
 assert.ok(invocations[0].opts.maxBuffer<=262144);
 assert.equal(accepted.source_sha256.length,64);
 const failed=await runIsolatedLeanSource({source:'example : False := by trivial\n',run:async(_command,args)=>{
  if(args[0]==='run')throw Object.assign(Error('LEAN_EXIT_1'),{code:1,stdout:'type mismatch',stderr:''});
  return {stdout:'',stderr:''};
 }});
 assert.equal(failed.status,'LEAN_REJECTED_THIS_REPLAY');
 assert.equal(failed.exit_code,1);
 const resource=await runIsolatedLeanSource({source:'example : True := by trivial\n',run:async(_command,args)=>{
  if(args[0]==='run')throw Object.assign(Error('OOM'),{code:137});
  return {stdout:'',stderr:''};
 }});
 assert.equal(resource.status,'EXECUTION_UNKNOWN');
 assert.equal(resource.exit_code,137);
});

test('execution timeout is UNKNOWN and forcibly reaps the exact task container name',async()=>{
 const calls=[];
 const r=await runIsolatedLeanSource({source:'example : True := by trivial\n',
  run:async(_command,args)=>{
   calls.push(args);
   if(args[0]==='run')throw Object.assign(Error('timeout'),{code:'ETIMEDOUT'});
   return {stdout:'',stderr:''};
  }});
 assert.equal(r.status,'EXECUTION_UNKNOWN');
 assert.equal(r.exit_code,null);
 assert.equal(calls.length,2);
 assert.deepEqual(calls[1],['rm','-f',calls[0][calls[0].indexOf('--name')+1]]);
});

test('unconfirmed container cleanup cannot be reported as accepted Lean execution',async()=>{
 let count=0;
 const r=await runIsolatedLeanSource({source:'example : True := by trivial\n',run:async()=>{
  if(count++===0)return {stdout:'ok',stderr:''};
  throw Object.assign(Error('daemon unavailable'),{code:125,stderr:'permission denied'});
 }});
 assert.equal(r.status,'EXECUTION_UNKNOWN');
 assert.equal(r.reason,'SANDBOX_CLEANUP_UNCONFIRMED');
});

test('over-budget source bytes and NULs are rejected before Docker is invoked',async()=>{
 let count=0;const run=async()=>{count++;return {stdout:'',stderr:''};};
 await assert.rejects(runIsolatedLeanSource({source:'x'.repeat(32769),run}),/SOURCE_SIZE_REFUSED/);
 await assert.rejects(runIsolatedLeanSource({source:'x\u0000y',run}),/SOURCE_FORMAT_REFUSED/);
 await assert.rejects(runIsolatedLeanSource({source:'',run}),/SOURCE_SIZE_REFUSED/);
 assert.equal(count,0);
});
