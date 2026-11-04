// No-secret, owned-fixture-only native isolation experiment. It does not
// accept PR input or provide a community sandbox service.
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {mkdtemp,writeFile,rm} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {tmpdir} from 'node:os';
import {pathToFileURL} from 'node:url';
import {sandboxDockerArgs,runIsolatedLeanSource} from './sandbox-native.mjs';

const exec=promisify(execFile);
const ensure=(okay,reason)=>{if(!okay)throw Error(reason);};
const positive='import Init\nexample : 2 + 2 = 4 := by decide\n';
const negative='import Init\nexample : False := by trivial\n';

export async function probeSandboxBoundary(){
 const directory=await mkdtemp(join(tmpdir(),'omm-lean-'));
 const sourcePath=join(directory,'Submission.lean');
 try{
  await writeFile(sourcePath,positive,{mode:0o444,flag:'wx'});
  const args=sandboxDockerArgs({sourcePath});
  const imageAt=args.indexOf('mathgraph-lean-sandbox:omm-v1');
  ensure(imageAt>0,'SANDBOX_IMAGE_MISSING');
  const shell=[...args.slice(0,imageAt),'--entrypoint','/bin/sh',args[imageAt],'-c',
   'set -eu; test -r /work/Submission.lean; test "$(id -u)" -eq 65534; '+
   '! (echo denied > /work/Submission.lean); '+
   '! (echo denied > /etc/mathgraph-sandbox-violation); '+
   '! grep -q "00000000" /proc/net/route; '+
   'echo OMM_BOUNDARY_OBSERVED'];
  const result=await exec('docker',shell,{timeout:20000,maxBuffer:262144,
   env:{PATH:process.env.PATH??'/usr/bin:/bin'}});
  ensure(result.stdout.includes('OMM_BOUNDARY_OBSERVED'),'SANDBOX_GUARD_FAILED');
  return {read_only:true,no_default_route:true,uid:65534};
 }finally{await rm(directory,{recursive:true,force:true});}
}

export async function qualifySandboxSmoke({native=runIsolatedLeanSource,probe=probeSandboxBoundary}={}){
 const [p,n]=[await native({source:positive}),await native({source:negative})];
 const guard=await probe();
 ensure(p?.status==='LEAN_ACCEPTED'&&p.exit_code===0&&
  n?.status==='LEAN_REJECTED_THIS_REPLAY'&&n.exit_code===1&&
  guard?.read_only===true&&guard.no_default_route===true&&guard.uid===65534,
  'SANDBOX_SMOKE_FAILED');
 return {schema:'mathgraph.omm.sandbox-smoke.v1',status:'SANDBOX_SMOKE_OBSERVED',
  candidate_compilation:'OBSERVED',negative_control:'REJECTED_THIS_REPLAY',
  first_party_positive_sha256:p.source_sha256,first_party_negative_sha256:n.source_sha256,
  isolation:{...guard,network_mode:'none',host_source_mount:'SINGLE_READ_ONLY_FILE',
   image:'mathgraph-lean-sandbox:omm-v1',memory:'512m',pids:32,cpus:1},
  intent_fidelity:'UNKNOWN',community_execution_permission:'DENIED',
  independent_evidence_warrant:'UNKNOWN'};
}

if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
 try{
  ensure(process.argv.length===2&&process.env.GITHUB_REPOSITORY==='metalogiclabs/mathgraph'&&
   process.env.GITHUB_EVENT_NAME==='push'&&process.env.GITHUB_ACTOR_ID==='32909488'&&
   /^[a-f0-9]{40}$/.test(process.env.GITHUB_SHA??'')&&
   typeof process.env.RUNNER_TEMP==='string'&&process.env.RUNNER_TEMP.startsWith('/')&&
   !process.env.OPENAI_API_KEY&&!process.env.MATHGRAPH_APP_INSTALLATION_TOKEN,
   'UNTRUSTED_SMOKE_CONTEXT');
  const report=await qualifySandboxSmoke();
  report.controller_sha=process.env.GITHUB_SHA;
  report.run_url=`https://github.com/metalogiclabs/mathgraph/actions/runs/${process.env.GITHUB_RUN_ID}`;
  await writeFile(join(process.env.RUNNER_TEMP,'omm-sandbox-smoke.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});
  console.log('OMM_SANDBOX_SMOKE_READBACK '+JSON.stringify(report));
 }catch(e){console.error('OMM_SANDBOX_SMOKE_UNKNOWN:'+String(e.message));process.exitCode=1;}
}
