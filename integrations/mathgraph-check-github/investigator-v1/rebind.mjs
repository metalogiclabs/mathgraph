// Explicit setup replay of an authenticated earlier same-repository plan.
// Does not alter the generated tests, source snapshot or proposal bytes.
import {readFile,writeFile,readdir} from 'node:fs/promises';import {createHash} from 'node:crypto';
const dir=process.argv[2]??'investigation';const prior=41511072108,head='177bba19bb14ffddb783377a58859183388f6dde';
const digest=x=>createHash('sha256').update(x).digest('hex');
const m=JSON.parse(await readFile(`${dir}/manifest.json`,'utf8'));
if(m.context.run_id!==prior||m.context.verifier_sha!==head||m.context.attempt!==1)throw Error('REPLAY_ORIGIN_MISMATCH');
for(const [name,h]of Object.entries(m.hashes)){if(!/^[a-z][a-z0-9_-]*\.json$/.test(name)||digest(await readFile(`${dir}/${name}`))!==h)throw Error('REPLAY_BYTES_CHANGED');}
const response=await fetch(`https://api.github.com/repos/metalogiclabs/mathgraph/actions/runs/${prior}`,{headers:{Authorization:`Bearer ${process.env.GITHUB_TOKEN}`,Accept:'application/vnd.github+json'},signal:AbortSignal.timeout(20000)});
if(!response.ok)throw Error('REPLAY_RUN_METADATA_UNAVAILABLE');const run=await response.json();
if(run.head_sha!==head||run.repository.full_name!=='metalogiclabs/mathgraph'||run.path!=='.github/workflows/check-investigator-pilot.yml'||run.run_attempt!==1)throw Error('REPLAY_RUN_METADATA_MISMATCH');
const context={verifier_sha:process.env.GITHUB_SHA,run_id:Number(process.env.GITHUB_RUN_ID),attempt:Number(process.env.GITHUB_RUN_ATTEMPT)};
if(!/^[a-f0-9]{40}$/.test(context.verifier_sha??'')||context.attempt!==1)throw Error('INVALID_REPLAY_CONTEXT');
const state=JSON.parse(await readFile(`${dir}/state.json`,'utf8'));if(state.state!=='PROBES_PROPOSED')throw Error('ORIGINAL_PLAN_NOT_PROPOSED');
await writeFile(`${dir}/replay-origin.json`,JSON.stringify({context:m.context,source_artifact_id:13172689027,source_artifact_sha256:'a7fd0f9621c17599111272d27661cd65a62178c5af70bd06d287a3e12ae62c2f',reason:'Dependency-only setup repair; generated tests and source snapshot unchanged'},null,2)+'\n');
await writeFile(`${dir}/state.json`,JSON.stringify({...state,context,generation_context:m.context},null,2)+'\n');
const hashes={};for(const name of (await readdir(dir)).filter(x=>x.endsWith('.json')&&x!=='manifest.json').sort())hashes[name]=digest(await readFile(`${dir}/${name}`));
await writeFile(`${dir}/manifest.json`,JSON.stringify({context,hashes},null,2)+'\n');
