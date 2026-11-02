import {createHash} from 'node:crypto';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {readFile,stat} from 'node:fs/promises';
import {createReadStream} from 'node:fs';
import {join,resolve} from 'node:path';

const exec=promisify(execFile);
export const PINNED_ENV=Object.freeze({
 semanteq:'f92767000e14d11744580946980cf874324f5d19',
 mathlib:'0c154d67103f74be3a0f2c509f72ccbf5be9f2a7',
 toolchainSha:'1098ca8368e0db12138f33b070187e1f6527984ae0451a587b20e3e661f96a76',
 manifestSha:'cafd720ea1ea51f4c8653d5dca284ebcfc7ca16fdfb1a2a1499c71ad6408a666'
});
const sha=s=>createHash('sha256').update(s).digest('hex');
async function shaFile(path){const hash=createHash('sha256');for await(const chunk of createReadStream(path))hash.update(chunk);return hash.digest('hex');}

export async function inspectPinnedLeanEnvironment(projectDir){
 if(typeof projectDir!=='string'||!projectDir)return {ok:false,reason:'MISSING_PROJECT_DIR'};
 const cwd=resolve(projectDir);
 let revision,mathlibGit,toolchainSha,manifestSha,leanVersion,lakeVersion,binarySha;
 try{
  if(!(await stat(join(cwd,'.lake/build/bin/semanteq'))).isFile())throw Error('MISSING_SEMANTEQ_BINARY');
  const [git,mathlib,projectDirty,mathlibDirty]=await Promise.all([
   exec('git',['-C',cwd,'rev-parse','HEAD'],{timeout:10000,maxBuffer:4096}),
   exec('git',['-C',join(cwd,'.lake/packages/mathlib'),'rev-parse','HEAD'],{timeout:10000,maxBuffer:4096}),
   exec('git',['-C',cwd,'status','--porcelain','--untracked-files=no'],{timeout:10000,maxBuffer:4096}),
   exec('git',['-C',join(cwd,'.lake/packages/mathlib'),'status','--porcelain','--untracked-files=no'],{timeout:10000,maxBuffer:4096})
  ]);
  revision=git.stdout.trim();mathlibGit=mathlib.stdout.trim();
  if(projectDirty.stdout.trim()||mathlibDirty.stdout.trim())return {ok:false,reason:'TRACKED_SOURCE_DIRTY'};
  toolchainSha=sha(await readFile(join(cwd,'lean-toolchain')));
  manifestSha=sha(await readFile(join(cwd,'lake-manifest.json')));
  binarySha=await shaFile(join(cwd,'.lake/build/bin/semanteq'));
 }catch(e){return {ok:false,reason:`NATIVE_TOOL_NOT_AVAILABLE:${e.code??e.message}`};}
 const metadata={cwd,tool_git:revision,mathlib_git:mathlibGit,
  lean_toolchain_sha256:toolchainSha,lake_manifest_sha256:manifestSha,
  semanteq_executable_sha256:binarySha};
 if(revision!==PINNED_ENV.semanteq||mathlibGit!==PINNED_ENV.mathlib||
  toolchainSha!==PINNED_ENV.toolchainSha||manifestSha!==PINNED_ENV.manifestSha)
  return {...metadata,ok:false,reason:'PINNED_ENVIRONMENT_DRIFT'};
 try{
  const [lean,lake]=await Promise.all([
   exec('lake',['env','lean','--version'],{cwd,timeout:15000,maxBuffer:4096,env:process.env}),
   exec('lake',['--version'],{cwd,timeout:15000,maxBuffer:4096,env:process.env})
  ]);
  leanVersion=lean.stdout.trim();lakeVersion=lake.stdout.trim();
 }catch(e){return {...metadata,ok:false,reason:`LEAN_ENVIRONMENT_UNAVAILABLE:${e.message}`};}
 if(!leanVersion.includes('4.30.0-rc1'))return {...metadata,ok:false,reason:'LEAN_VERSION_MISMATCH',lean_version:leanVersion,lake_version:lakeVersion};
 return {...metadata,ok:true,lean_version:leanVersion,lake_version:lakeVersion};
}
