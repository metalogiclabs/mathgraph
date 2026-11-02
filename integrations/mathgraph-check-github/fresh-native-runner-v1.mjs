// Untrusted elaboration gets an isolated directory per verification attempt.
// Completion includes confirmed removal of each uniquely named container.
import {writeFile,chmod} from 'node:fs/promises';import {join} from 'node:path';
import {randomUUID} from 'node:crypto';import {execFile} from 'node:child_process';import {promisify} from 'node:util';
import {dependencyMountArgs} from './mention-native-demo-v1.mjs';
const exec=promisify(execFile);
export async function freshNativeRunner({directory,dependencyDirectory,image='mathgraph-lean-demo:v1',execute=exec,resolveDependencies=dependencyMountArgs}){
 await chmod(directory,0o777);const dependencyArgs=await resolveDependencies(dependencyDirectory);
 const options={timeout:120000,killSignal:'SIGKILL',maxBuffer:262144,env:{PATH:process.env.PATH??'/usr/bin:/bin'}};
 return async(name,source,{strict=false}={})=>{
  if(!['Candidate','Consumer','Sanity','Negative'].includes(name))throw Error('NATIVE_UNIT_REFUSED');
  await writeFile(join(directory,name+'.lean'),source,{mode:0o644});const container='mathgraph-fresh-'+randomUUID();
  const args=['run','--rm','--name',container,'--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--memory','4g','--cpus','2','--tmpfs','/tmp:rw,noexec,nosuid,size=64m','--mount','type=bind,src='+directory+',dst=/work',...dependencyArgs,image,...(strict?['-DwarningAsError=true']:[]),'-o','/work/'+name+'.olean','/work/'+name+'.lean'];
  try{const r=await execute('docker',args,options);return {code:0,output:r.stdout+r.stderr};}
  catch(e){if(e.code===1)return {code:1,output:String(e.stdout??'')+String(e.stderr??'')};throw Error('NATIVE_RESOURCE_LIMIT');}
  finally{
   const cleanupOptions={...options,timeout:15000,maxBuffer:8192};
   try{await execute('docker',['rm','-f',container],cleanupOptions);}catch{}
   try{await execute('docker',['inspect',container],cleanupOptions);throw Error('NATIVE_CLEANUP_UNCONFIRMED');}
   catch(e){if(!(e.code===1&&/No such (?:object|container)/i.test(String(e.stderr??''))))throw Error('NATIVE_CLEANUP_UNCONFIRMED');}
  }
 };
}
