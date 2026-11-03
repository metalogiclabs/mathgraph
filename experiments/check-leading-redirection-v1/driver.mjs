// Source data never selects commands; native.py remains credential-free.
import {readFile,writeFile,mkdir,readdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {executionContext} from '../../integrations/mathgraph-check-github/pr-pilot-v1/context.mjs';
import {planFor,inspectNative} from '../check-expectation-admission-v1/binding-native.mjs';
import {admitLeanPlan,admitLeanPatch,inspectArm} from '../../integrations/mathgraph-check-github/lean-investigator-v1/contracts.mjs';
const [phase,root]=process.argv.slice(2),context=executionContext();
const policy=JSON.parse(await readFile(new URL('./binding.json',import.meta.url)));
const hash=s=>createHash('sha256').update(s).digest('hex'),same=(a,b)=>JSON.stringify(a)===JSON.stringify(b),need=(b,c)=>{if(!b)throw Error(c);};
const load=async n=>JSON.parse(await readFile(root+'/'+n+'.json')),save=async(n,v)=>writeFile(root+'/'+n+'.json',JSON.stringify(v,null,2)+'\n');
async function seal(){const hashes={};for(const n of(await readdir(root)).filter(n=>n.endsWith('.json')&&n!=='manifest.json').sort())hashes[n]=hash(await readFile(root+'/'+n));await save('manifest',{context,hashes});}
async function verify(){const m=await load('manifest');need(same(m.context,context),'CONTEXT_CHANGED');for(const[n,h]of Object.entries(m.hashes))need(/^[a-z][a-z0-9_-]*\.json$/.test(n)&&hash(await readFile(root+'/'+n))===h,'ARTIFACT_CHANGED');}
if(phase==='prepare'){
 await mkdir(root,{recursive:true});
 const source=async path=>{const r=await fetch(`https://api.github.com/repos/${policy.subject.repository}/contents/${path}?ref=${policy.subject.revision}`,{redirect:'error',headers:{Authorization:'Bearer '+process.env.GITHUB_TOKEN,Accept:'application/vnd.github.raw+json'},signal:AbortSignal.timeout(30000)});need(r.ok,'SOURCE_HTTP_'+r.status);return r.text();};
 const src=await source(policy.subject.path),cli=await source(policy.cli_path);need(hash(src)===policy.subject.sha256&&hash(cli)===policy.cli_sha256,'SOURCE_CHANGED');
 const snapshot={repository:policy.subject.repository,head_sha:policy.subject.revision,path:policy.subject.path,source:src,source_sha256:hash(src),module:'Scripts.Ledger',namespace:'Scripts.Ledger',cli_path:policy.cli_path,cli_source:cli,cli_sha256:hash(cli),cli_module:'Scripts.Main.CheckScriptsLedger',toolchain:policy.toolchain,mode:'OWNER_SELECTED_RETROSPECTIVE_SOURCE_AUDIT'};
 const plan=planFor(policy);for(const t of plan.tests)admitLeanPlan({summary:plan.summary,tests:[t]});
 await save('snapshot',snapshot);await save('plan',plan);await save('state',{context,state:'PROBES_PROPOSED',test_digest:hash(JSON.stringify(plan.tests)),model_calls:0});await seal();
}else if(phase==='initial'){
 await verify();const s=await load('snapshot'),p=await load('plan'),n=await load('native'),state=await load('state');
 need(same(p,planFor(policy))&&same(n.context,context)&&n.source_sha===policy.subject.revision&&s.head_sha===policy.subject.revision&&hash(s.source)===policy.subject.sha256&&hash(s.cli_source)===policy.cli_sha256&&n.test_digest===state.test_digest&&state.test_digest===hash(JSON.stringify(p.tests)),'INITIAL_IDENTITY_CHANGED');
 const initial=inspectArm(n.arm,{profile:s,plan:p,source:s.source});await save('initial-inspection',{context,subject:policy.subject,initial,complete:initial.complete,failures:initial.rows.filter(r=>r.execution==='CANDIDATE_ASSERTION_FAILURE').map(r=>r.id)});await seal();need(initial.complete,'INITIAL_INCOMPLETE');
}else if(phase==='patch'){
 await verify();const i=await load('initial-inspection');need(i.complete===true&&i.failures.length>0,'NO_CONFIRMED_DISCREPANCY');
 const p=JSON.parse(await readFile(new URL('./patch.json',import.meta.url))),s=await load('snapshot'),content=admitLeanPatch(p,s.source);
 await save('patch',{...p,content,path:s.path,original_sha256:hash(s.source),patched_sha256:hash(content)});await save('repair-state',{state:'PATCH_PROPOSED',model_calls:0,origin:'AUTHORED_AFTER_FROZEN_NATIVE_BASELINE',patched_sha256:hash(content)});await seal();
}else if(phase==='assess'){
 await verify();const patchPolicy=JSON.parse(await readFile(new URL('./patch.json',import.meta.url))),data={policy:{...policy,patch:patchPolicy},context};for(const[k,n]of Object.entries({snapshot:'snapshot',plan:'plan',state:'state',native:'native',repair:'native-repair',patch:'patch'}))data[k]=await load(n);
 await save('inspection',inspectNative(data));await seal();
}else throw Error('UNKNOWN_PHASE');
