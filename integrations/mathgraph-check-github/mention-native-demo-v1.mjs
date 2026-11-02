// Deliberately small, declared demonstration boundary. This is not a generic
// source-to-intent checker. The original target is fixed by this trusted module.
import {createHash} from 'node:crypto';
import {writeFile,chmod,readdir,access} from 'node:fs/promises';
import {join} from 'node:path';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
const exec=promisify(execFile);
export const originalTarget='theorem mathgraph_reverse_length (xs : List Nat) : xs.reverse.length = xs.length';
export const brokenSource='import Std\n\ntheorem mathgraph_reverse_length (xs : List Nat) (h : xs.reverse.length = xs.length) : xs.reverse.length = xs.length := h\n';
export const demoPath='mathgraph-demo/ReverseLength.lean';
const bodies=['by simp','by simpa','by exact List.length_reverse'];
export function repairedSource(proof){
 if(!bodies.includes(proof))throw Error('UNSUPPORTED_PROOF_CONSTRUCTOR');
 return 'import Std\n\n'+originalTarget+' := '+proof+'\n';
}
export async function nativeDemo({source,run}){
 if(source!==brokenSource&&!bodies.some(p=>repairedSource(p)===source))throw Error('UNSUPPORTED_DEMO_SOURCE');
 const sourceHash=createHash('sha256').update(source).digest('hex');
 const targetHash=createHash('sha256').update(originalTarget).digest('hex');
 const compiled=await run('Candidate',source);
 if(compiled.code!==0)return {status:'UNKNOWN',source_sha256:sourceHash,target_sha256:targetHash,source_compiles:false,original_claim_satisfied:false};
 const consumer=await run('Consumer','import Candidate\n\nexample (xs : List Nat) : xs.reverse.length = xs.length := mathgraph_reverse_length xs\n#print axioms mathgraph_reverse_length\n');
 const audit=consumer.output.match(/^'mathgraph_reverse_length' (?:does not depend on any axioms|depends on axioms: \[([^\]]*)\])\s*$/m);
 const axioms=audit?(audit[1]?audit[1].split(',').map(x=>x.trim()):[]):null;
 const clean=consumer.code===0&&axioms!==null&&axioms.every(x=>x==='propext')&&new Set(axioms).size===axioms.length;
 return {status:clean?'ORIGINAL_TARGET_VERIFIED':consumer.code===1&&/type mismatch/i.test(consumer.output)?'CLAIM_NOT_ESTABLISHED':'UNKNOWN',source_sha256:sourceHash,target_sha256:targetHash,source_compiles:true,original_claim_satisfied:clean,axioms:clean?axioms:null};
}
export async function dependencyMountArgs(directory){
 if(typeof directory!=='string'||!directory.startsWith('/')||/[,\n\r]/.test(directory))throw Error('INVALID_DEPENDENCY_DIRECTORY');
 await access(join(directory,'mathlib/.lake/build/lib/lean/Mathlib/GroupTheory/Subgroup/Centralizer.olean'));
 const entries=await readdir(directory,{withFileTypes:true}),paths=[];
 for(const e of entries){if(!e.isDirectory()||!/^[A-Za-z0-9_-]+$/.test(e.name))continue;try{await access(join(directory,e.name,'.lake/build/lib/lean'));paths.push('/mathgraph-deps/'+e.name+'/.lake/build/lib/lean');}catch{}}
 return ['--mount','type=bind,src='+directory+',dst=/mathgraph-deps,readonly','--env','LEAN_PATH=/work:/opt/lean/lib/lean:'+paths.join(':')];
}
export async function dockerRunner(directory,{image='mathgraph-lean-demo:v1',dependencyDirectory}={}){
 await chmod(directory,0o777);const dependencyArgs=dependencyDirectory?await dependencyMountArgs(dependencyDirectory):[];
 return async(name,source)=>{
  if(!/^(Candidate|Consumer|Sanity|Negative)$/.test(name))throw Error('INVALID_NATIVE_UNIT');
  await writeFile(join(directory,name+'.lean'),source,{mode:0o644});
  const args=['run','--rm','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','64','--memory','1g','--cpus','2','--tmpfs','/tmp:rw,noexec,nosuid,size=64m','--mount','type=bind,src='+directory+',dst=/work',...dependencyArgs,image,'-o','/work/'+name+'.olean','/work/'+name+'.lean'];
  try{const r=await exec('docker',args,{timeout:60000,maxBuffer:262144,env:{PATH:process.env.PATH??'/usr/bin:/bin'}});return {code:0,output:r.stdout+r.stderr};}
  catch(e){if(e.code===1)return {code:1,output:String(e.stdout??'')+String(e.stderr??'')};throw Error('NATIVE_EXECUTION_INCOMPLETE');}
 };
}
