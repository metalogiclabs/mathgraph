// Explicit compiler-guided replay. No new probes, requirements or human repair.
import {readFile,writeFile,mkdir,readdir} from 'node:fs/promises';import {createHash} from 'node:crypto';
const input=process.argv[2]??'prior-lean-investigation',out=process.argv[3]??'lean-investigation';
const priorRun=41519286478,priorHead='1bcf11a86f884f4daabcb7d26055e69bf29be03e';
const hash=x=>createHash('sha256').update(x).digest('hex');const get=async n=>JSON.parse(await readFile(`${input}/${n}.json`,'utf8'));
const m=await get('manifest');if(m.context.run_id!==priorRun||m.context.verifier_sha!==priorHead||m.context.attempt!==1)throw Error('REVISION_ORIGIN_MISMATCH');
for(const[name,h]of Object.entries(m.hashes)){if(!/^[a-z][a-z0-9_-]*\.json$/.test(name)||hash(await readFile(`${input}/${name}`))!==h)throw Error('PRIOR_ARTIFACT_CHANGED');}
const response=await fetch(`https://api.github.com/repos/metalogiclabs/mathgraph/actions/runs/${priorRun}`,{headers:{Authorization:`Bearer ${process.env.GITHUB_TOKEN}`,Accept:'application/vnd.github+json'},signal:AbortSignal.timeout(20000)});
if(!response.ok)throw Error('ORIGIN_RUN_UNAVAILABLE');const run=await response.json();if(run.head_sha!==priorHead||run.repository.full_name!=='metalogiclabs/mathgraph'||run.path!=='.github/workflows/check-lean-investigator.yml'||run.run_attempt!==1)throw Error('ORIGIN_RUN_MISMATCH');
const context={verifier_sha:process.env.GITHUB_SHA,run_id:Number(process.env.GITHUB_RUN_ID),attempt:Number(process.env.GITHUB_RUN_ATTEMPT)};if(!/^[a-f0-9]{40}$/.test(context.verifier_sha??'')||context.attempt!==1)throw Error('INVALID_REVISION_CONTEXT');
await mkdir(out,{recursive:true});
for(const name of ['snapshot','plan','model-investigate'])await writeFile(`${out}/${name}.json`,await readFile(`${input}/${name}.json`));
const state=await get('state');if(state.state!=='PROBES_PROPOSED')throw Error('NO_ORIGINAL_PLAN');await writeFile(`${out}/state.json`,JSON.stringify({...state,context,proposal_origin:m.context},null,2)+'\n');
const candidate=await get('model-repair');const diagnostic=await readFile(`${input}/native-logs/repair-repaired-build.log`,'utf8');
await writeFile(`${out}/prior-feedback.json`,JSON.stringify({prior_run:priorRun,prior_verifier:priorHead,prior_candidate:candidate.proposal,compiler_diagnostic:diagnostic.slice(-5000),instruction:'The prior candidate failed native compilation. Return corrected exact replacements against the original source. Preserve the frozen probes and original requirements; no new tests or human repair are supplied.'},null,2)+'\n');
await writeFile(`${out}/origin-receipt.json`,JSON.stringify({context:m.context,source_artifact_id:13175964630,source_artifact_sha256:'ef985b4f495d283d6180ea4a679d7ee253f091ae24d6b56e88f29e219d594ba5',mode:'EXPLICIT_BOUNDED_COMPILER_FEEDBACK_REVISION',new_probe_generation:false},null,2)+'\n');
const hashes={};for(const name of(await readdir(out)).filter(x=>x.endsWith('.json')&&x!=='manifest.json').sort())hashes[name]=hash(await readFile(`${out}/${name}`));await writeFile(`${out}/manifest.json`,JSON.stringify({context,hashes},null,2)+'\n');
