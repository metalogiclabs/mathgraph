import {readFile,writeFile,mkdir,readdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {executionContext} from '../../integrations/mathgraph-check-github/pr-pilot-v1/context.mjs';
import {admitLeanPlan,admitLeanPatch} from '../../integrations/mathgraph-check-github/lean-investigator-v1/contracts.mjs';
import {planFor,inspectNative} from './binding-native.mjs';
const policy=JSON.parse(await readFile(new URL('./binding.json',import.meta.url)));
const [phase,root]=process.argv.slice(2),context=executionContext();
const hash=s=>createHash('sha256').update(s).digest('hex');
const load=async name=>JSON.parse(await readFile(`${root}/${name}.json`));
const save=async(name,value)=>writeFile(`${root}/${name}.json`,JSON.stringify(value,null,2)+'\n');
const ensure=(b,why)=>{if(!b)throw Error(why);};
if(phase==='prepare'){
 await mkdir(root,{recursive:true});
 async function source(path){const r=await fetch(`https://api.github.com/repos/${policy.subject.repository}/contents/${path}?ref=${policy.subject.revision}`,{redirect:'error',headers:{Authorization:'Bearer '+process.env.GITHUB_TOKEN,Accept:'application/vnd.github.raw+json','User-Agent':'MathGraph-Binding-Qualification'},signal:AbortSignal.timeout(30000)});ensure(r.ok,'SOURCE_HTTP_'+r.status);return r.text();}
 const src=await source(policy.subject.path),cli=await source(policy.cli_path);
 ensure(hash(src)===policy.subject.sha256&&hash(cli)===policy.cli_sha256,'SOURCE_IDENTITY_MISMATCH');
 const snapshot={repository:policy.subject.repository,head_sha:policy.subject.revision,path:policy.subject.path,source:src,source_sha256:hash(src),module:'Scripts.Ledger',namespace:'Scripts.Ledger',cli_path:policy.cli_path,cli_source:cli,cli_sha256:hash(cli),cli_module:'Scripts.Main.CheckScriptsLedger',toolchain:policy.toolchain,mode:'OWNER_SELECTED_RETROSPECTIVE_SOURCE_AUDIT'};
 const plan=planFor(policy);for(const t of plan.tests)admitLeanPlan({summary:plan.summary,tests:[t]});
 const content=admitLeanPatch(policy.patch,src),patch={...policy.patch,content,original_sha256:hash(src),patched_sha256:hash(content),path:policy.subject.path};
 await save('snapshot',snapshot);await save('plan',plan);await save('patch',patch);
 await save('state',{context,state:'PROBES_PROPOSED',test_digest:hash(JSON.stringify(plan.tests)),model_calls:0});
 await save('repair-state',{state:'PATCH_PROPOSED',model_calls:0,patched_sha256:patch.patched_sha256});
 const hashes={};for(const n of (await readdir(root)).filter(n=>n.endsWith('.json')).sort())hashes[n]=hash(await readFile(`${root}/${n}`));
 await save('manifest',{context,hashes});
}else if(phase==='assess'){
 const manifest=await load('manifest');ensure(JSON.stringify(manifest.context)===JSON.stringify(context),'MANIFEST_CONTEXT_MISMATCH');
 for(const [name,h]of Object.entries(manifest.hashes)){ensure(/^[a-z][a-z0-9_-]*\.json$/.test(name)&&hash(await readFile(`${root}/${name}`))===h,'NATIVE_ARTIFACT_CHANGED');}
 const data={policy,context};for(const [key,file]of Object.entries({snapshot:'snapshot',plan:'plan',state:'state',native:'native',repair:'native-repair',patch:'patch'}))data[key]=await load(file);
 await save('inspection',inspectNative(data));
}else throw Error('UNKNOWN_PHASE');
