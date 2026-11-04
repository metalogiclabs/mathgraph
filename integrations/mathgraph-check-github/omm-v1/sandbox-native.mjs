// Candidate community Lean execution boundary: first-party smoke only.
// Never run this in a credentialed GitHub App / model job. The container gets
// one read-only Lean source file, a tiny tmpfs and zero host/network access.
// Compiling Lean code does not establish a user's intended mathematical claim.
import {createHash} from 'node:crypto';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {mkdtemp,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,normalize,sep} from 'node:path';

const exec=promisify(execFile);
const IMAGE='mathgraph-lean-sandbox:omm-v1';
const digest=s=>createHash('sha256').update(s).digest('hex');
const assert=(yes,code)=>{if(!yes)throw Error(code);};

export function sandboxDockerArgs(options={}){
 assert(Object.keys(options).length===1&&typeof options.sourcePath==='string',
  'UNSUPPORTED_SANDBOX_OPTION');
 const sourcePath=options.sourcePath,base=tmpdir()+sep+'omm-lean-';
 assert(sourcePath.startsWith(base)&&sourcePath===normalize(sourcePath)&&
  /^[-a-zA-Z0-9_]+$/.test(sourcePath.slice(base.length).split(sep)[0]??'')&&
  sourcePath.slice(base.length).split(sep).length===2&&
  sourcePath.endsWith(sep+'Submission.lean')&&!sourcePath.includes(','),
  'UNSAFE_SANDBOX_SOURCE');
 const nonce=sourcePath.slice(base.length).split(sep)[0];
 return ['run','--rm','--name','mathgraph-omm-'+nonce,'--pull','never',
  '--network','none','--ipc','none','--read-only',
  '--cap-drop','ALL','--security-opt','no-new-privileges',
  '--pids-limit','32','--memory','512m','--memory-swap','512m','--cpus','1',
  '--user','65534:65534','--ulimit','nofile=128:128',
  '--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=32m,mode=1777',
  '--mount',`type=bind,src=${sourcePath},dst=/work/Submission.lean,readonly`,
  '--workdir','/work',
  '--env','HOME=/tmp','--env','LEAN_NUM_THREADS=1',
  IMAGE,'-o','/tmp/Submission.olean','/work/Submission.lean'];
}

/** An exec timeout kills the Docker CLI, not necessarily the daemon container. */
export async function reapIsolatedContainer({name,run=exec}={}){
 assert(typeof name==='string'&&/^mathgraph-omm-[-A-Za-z0-9_]+$/.test(name)&&
  typeof run==='function','UNSAFE_SANDBOX_REAP_TARGET');
 try{
  await run('docker',['rm','-f',name],{timeout:5000,maxBuffer:131072,
   env:{PATH:process.env.PATH??'/usr/bin:/bin'}});
 }catch(e){
  const message=String(e.stderr??'')+' '+String(e.message??'');
  if(!/No such container:/i.test(message))throw Error('SANDBOX_CLEANUP_UNCONFIRMED');
 }
}

export async function runIsolatedLeanSource({source,run=exec}={}){
 assert(typeof source==='string'&&Buffer.byteLength(source,'utf8')>0&&
  Buffer.byteLength(source,'utf8')<=32768,'SOURCE_SIZE_REFUSED');
 assert(!source.includes('\u0000'),'SOURCE_FORMAT_REFUSED');
 assert(typeof run==='function','INVALID_NATIVE_RUNNER');
 const directory=await mkdtemp(join(tmpdir(),'omm-lean-'));
 const sourcePath=join(directory,'Submission.lean'),sourceSha=digest(source);
 try{
  await writeFile(sourcePath,source,{mode:0o444,flag:'wx'});
  const args=sandboxDockerArgs({sourcePath});
  const opts={timeout:60000,maxBuffer:262144,env:{PATH:process.env.PATH??'/usr/bin:/bin'}};
  const name=args[args.indexOf('--name')+1];
  let outcome;
  try{
   const result=await run('docker',args,opts);
   outcome={status:'LEAN_ACCEPTED',exit_code:0,source_sha256:sourceSha,
    output:String(result.stdout??'').slice(0,131072)+String(result.stderr??'').slice(0,131072)};
  }catch(e){
   const code=Number.isInteger(e.code)?e.code:null;
   outcome={status:code===1?'LEAN_REJECTED_THIS_REPLAY':'EXECUTION_UNKNOWN',
    exit_code:code,source_sha256:sourceSha,
    output:(String(e.stdout??'')+String(e.stderr??'')).slice(0,131072),
    reason:code===1?'LEAN_EXITED_NONZERO':'RUNTIME_INCOMPLETE_OR_RESOURCE_BOUND'};
  }
  try{await reapIsolatedContainer({name,run});}
  catch{return {...outcome,status:'EXECUTION_UNKNOWN',reason:'SANDBOX_CLEANUP_UNCONFIRMED'};}
  return outcome;
 }finally{await rm(directory,{recursive:true,force:true});}
}
