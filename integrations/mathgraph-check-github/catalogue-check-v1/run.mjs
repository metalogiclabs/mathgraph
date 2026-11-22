#!/usr/bin/env node
import {createHash} from 'node:crypto';
import {readFile,writeFile,mkdir,realpath} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import {resolve,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {performance} from 'node:perf_hooks';
import {CATALOGUE,PROFILES,coverageFor} from './catalogue.mjs';

const hash=x=>createHash('sha256').update(x).digest('hex');
const json=x=>JSON.stringify(x,null,2)+'\n';
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const allowedIds=new Set(PROFILES.map(x=>x.id));
export function parseArgs(argv){
 if(argv.includes('--help'))return {help:true};
 const opts={},allowed=new Set(['repo','base','head','out','lean','python','timeout-seconds','profiles']);
 for(let i=0;i<argv.length;i+=2){const key=argv[i]?.replace(/^--/,'');
  if(!argv[i]?.startsWith('--')||!allowed.has(key)||argv[i+1]===undefined||Object.hasOwn(opts,key))throw Error('INVALID_ARGUMENT: '+argv[i]);
  opts[key]=argv[i+1];
 }
 for(const key of ['repo','base','head','out'])if(!opts[key])throw Error('MISSING_ARGUMENT: --'+key);
 opts.profiles=opts.profiles===undefined?PROFILES.map(p=>p.id):opts.profiles.split(',');
 if(opts.profiles.some(x=>!allowedIds.has(x)))throw Error('UNSUPPORTED_PROFILE');
 if(new Set(opts.profiles).size!==opts.profiles.length)throw Error('DUPLICATE_PROFILE');
 opts.timeout=Number(opts['timeout-seconds']??120);
 if(!Number.isFinite(opts.timeout)||opts.timeout<1||opts.timeout>600)throw Error('INVALID_TIMEOUT: use 1..600 seconds per profile');
 opts.lean=opts.lean??process.env.MATHGRAPH_LEAN_BIN??'lean';opts.python=opts.python??'python3';
 return opts;
}

function inspectArm(arm,expectedIds){
 if(arm?.complete!==true||!Array.isArray(arm.observations)||!arm.observations.length||!Array.isArray(arm.mismatches))return null;
 if(arm.observations.length!==expectedIds.length)return null;
 const ids=arm.observations.map(x=>x.id);
 if(ids.some(x=>typeof x!=='string'||!x)||new Set(ids).size!==ids.length||
  !same([...ids].sort(),[...expectedIds].sort())||arm.observations.some(x=>typeof x.passed!=='boolean'))return null;
 const expected=arm.observations.filter(x=>!x.passed).map(x=>x.id).sort();
 if(!same(expected,arm.mismatches.map(x=>x.id).sort()))return null;
 return {cases:arm.observations.length,mismatches:arm.mismatches.length};
}
export function inspectProfileResult(profile,r,revisions){
 let base=inspectArm(r?.base,profile.case_ids),head=inspectArm(r?.head,profile.case_ids);
 let reason=r?.reason??null,status=r?.status;
 const identityIssues=[];
 if(base&&(r.method?.id!==profile.id||r.subjects?.base?.revision!==revisions.base)){
  base=null;identityIssues.push('base');
 }
 if(head&&(r.method?.id!==profile.id||r.subjects?.head?.revision!==revisions.head)){
  head=null;identityIssues.push('head');
 }
 if(identityIssues.length){status='UNKNOWN';reason='PROFILE_IDENTITY_MISMATCH: '+identityIssues.join(', ')+(reason?'; '+reason:'');}
 if(status!=='UNKNOWN'){
  if(!['OBSERVED_AGREEMENT','OBSERVED_MISMATCH'].includes(status))reason='INVALID_PROFILE_OUTCOME';
  else if(r.method?.id!==profile.id||r.subjects?.base?.revision!==revisions.base||r.subjects?.head?.revision!==revisions.head)reason='PROFILE_IDENTITY_MISMATCH';
  else if(!base||!head)reason='PROFILE_OBSERVATIONS_INCOMPLETE_OR_INCONSISTENT';
  else if((head.mismatches===0)!==(status==='OBSERVED_AGREEMENT'))reason='PROFILE_VERDICT_DISAGREES_WITH_OBSERVATIONS';
  if(reason)status='UNKNOWN';
 }
 return {status:status??'UNKNOWN',reason:reason??(status==='UNKNOWN'?'PROFILE_EVIDENCE_INCOMPLETE':null),base,head};
}

async function runnerFor(id){
 if(id==='suite-per-case-agreement-v1')return (await import('../retained-suite-v1/per-case.mjs')).runPerCase;
 if(id==='suite-refusal-integrity-v1')return (await import('../retained-suite-v1/refusal.mjs')).runRefusal;
 const {runLocal}=await import('../pr-pilot-v1/local-report-check.mjs');
 return options=>runLocal({...options,profile:id});
}

function resolveCommit(repo,ref){
 const p=spawnSync('git',['-C',repo,'rev-parse','--verify','--end-of-options',ref+'^{commit}'],{encoding:'utf8',timeout:30000,maxBuffer:1024*1024});
 if(p.error||p.status!==0||!/^[a-f0-9]{40}$/.test(p.stdout.trim()))throw Error('REVISION_UNAVAILABLE: '+ref);
 return p.stdout.trim();
}
async function methodIdentity(){
 const files={};for(const name of ['catalogue.json','catalogue.mjs','run.mjs',
  '../pr-pilot-v1/report-cases.json','../pr-pilot-v1/report-status-cases.json',
  '../retained-suite-v1/per-case-cases.json','../retained-suite-v1/refusal-cases.json'])files[name]=hash(await readFile(new URL(name,import.meta.url)));
 return {id:'failure-catalogue-dispatch-v1',files};
}
const cell=x=>String(x??'').replaceAll('|','\\|').replaceAll('\n',' ');
export function renderReport(r){
 const lines=['# MathGraph Check — retained failure checks','',
  '**104 candidate prompts accounted for. Whole-family coverage remains unestablished.**','',
  `Run: **${r.status}**. Profiles: ${r.profile_counts.agreement} bounded agreement, ${r.profile_counts.discrepancy} with discrepancies, ${r.profile_counts.unknown} UNKNOWN, ${r.profile_counts.not_run} NOT_RUN.`,
  '',`${r.coverage.counts.mapped_prompts} prompts have a mapped finite obligation; ${r.coverage.counts.unsupported_by_this_command} have no executable connected to this command. A mapping is not a complete detector.`,
  '',`Catalogue: ${CATALOGUE.revision}. [Canonical source](${CATALOGUE.source.url}).`,'',
  '## Exact source','',`- Base: \`${r.subjects?.base??'unavailable'}\`.`,`- Head: \`${r.subjects?.head??'unavailable'}\`.`,
  '', 'Revisions are resolved once from local Git. Each profile reexecutes its selected source; no previous verdict is reused.',
  '', '## Retained checks','','| Profile | Result | Base discrepancies / cases | Head discrepancies / cases | Evidence |','| --- | --- | --- | --- | --- |'];
 const counts=a=>a?`${a.mismatches} / ${a.cases}`:'unavailable';
 for(const p of PROFILES){const x=r.profiles[p.id];lines.push(`| ${p.title} | ${x.status} | ${counts(x.base)} | ${counts(x.head)} | ${x.result?'[result]('+x.result+')':''} |`);}
 lines.push('');
 for(const p of PROFILES){const x=r.profiles[p.id];if(x.reason)lines.push(`- **${p.title}:** ${x.reason}`);}
 lines.push('','## 104-prompt coverage ledger','',
  'BOUNDED_AGREEMENT and BOUNDED_MISMATCH concern only the named finite obligations. UNKNOWN means incomplete execution evidence. NOT_RUN means a retained method was omitted. UNSUPPORTED_BY_THIS_COMMAND means no executable is connected here. No state establishes full-family coverage.','',
  '| ID | Prompt | Current evidence | Connected checks |','| --- | --- | --- | --- |');
 for(const row of r.coverage.items)lines.push(`| ${row.id} | ${cell(row.title)} | ${row.status}${row.incomplete?' (incomplete checks)':''} | ${row.checks.map(c=>cell(PROFILES.find(p=>p.id===c.profile).title)+': '+c.status).join('; ')} |`);
 lines.push('','## Verification boundary','');
 for(const p of PROFILES)lines.push(`- **${p.title}:** ${p.boundary}`);
 lines.push('',
  'The catalogue consists of candidate search prompts, not 104 independent defects or qualified detectors. Mappings overlap. Source hashes and complete receipts establish what was run; they do not establish a governing requirement, permission to act, full input coverage or whole-project correctness.',
  '', 'Other Check capabilities are outside this command. No external operator is needed for this execution; human utility and comparative value remain unmeasured.',
  '', '## Cost and retained evidence','',`- Wall time: ${r.cost.wall_seconds.toFixed(3)} seconds.`,
  `- Model calls: ${r.cost.model_calls??'unknown'}.`,
  '- `result.json`: exact revisions, dispatcher identity, all profile dispositions and all 104 prompts, obligations and residuals.',
  '- `checks/`: per-profile source/method identities, actual observations, reports and raw evidence.',
  '- Profile result digests in `result.json` bind this ledger to those retained receipts.','');
 return lines.join('\n');
}

export async function runCatalogue(options,{runners={}}={}){
 const selected=options.profiles??PROFILES.map(p=>p.id);
 if(!selected.length||selected.some(x=>!allowedIds.has(x)))throw Error('UNSUPPORTED_PROFILE');
 if(new Set(selected).size!==selected.length)throw Error('DUPLICATE_PROFILE');
 const started=performance.now(),out=resolve(options.out);
 try{await mkdir(out,{recursive:false});}catch(e){if(e.code==='EEXIST')throw Error('OUTPUT_ALREADY_EXISTS: '+out);throw e;}
 await mkdir(join(out,'checks'));
 const r={schema:'mathgraph.catalogue-check.v1',status:'INCOMPLETE',permission:'ADVISORY_ONLY',
  subjects:{},method:await methodIdentity(),profiles:{},cost:{wall_seconds:0,model_calls:0,human_utility:'NOT_RUN',comparative_value:'NOT_RUN'}};
 let repo,resolutionError;
 try{repo=await realpath(options.repo);r.repository='local-git:'+repo;
  r.subjects={base:resolveCommit(repo,options.base),head:resolveCommit(repo,options.head)};
 }catch(e){resolutionError=e.message;}
 for(const p of PROFILES){
  if(!selected.includes(p.id)){r.profiles[p.id]={status:'NOT_RUN',reason:'PROFILE_NOT_SELECTED',base:null,head:null};continue;}
  if(resolutionError){r.profiles[p.id]={status:'UNKNOWN',reason:resolutionError,base:null,head:null};continue;}
  try{
   const run=runners[p.id]??await runnerFor(p.id);
   if(typeof run!=='function')throw Error('EXECUTOR_UNAVAILABLE');
   const {result}=await run({...options,repo,...r.subjects,out:join(out,'checks',p.id),profile:p.id,
    lean:options.lean??process.env.MATHGRAPH_LEAN_BIN??'lean',python:options.python??'python3',timeout:options.timeout??120});
   const relative='checks/'+p.id+'/result.json',bytes=await readFile(join(out,relative));
   if(!same(JSON.parse(bytes),result))throw Error('PROFILE_RECEIPT_DISAGREES_WITH_RETURNED_RESULT');
   const inspected=inspectProfileResult(p,result,r.subjects);
   r.profiles[p.id]={...inspected,result:relative,result_sha256:hash(bytes),method:result.method??null};
   if(result.cost?.model_calls!==0)r.cost.model_calls=null;
  }catch(e){r.profiles[p.id]={status:'UNKNOWN',reason:e.message,base:null,head:null};}
 }
 if(!same(r.method,await methodIdentity())){
  for(const p of PROFILES)if(r.profiles[p.id].status!=='NOT_RUN')r.profiles[p.id]={...r.profiles[p.id],status:'UNKNOWN',reason:'DISPATCH_METHOD_CHANGED_DURING_EXECUTION'};
 }
 const profiles=Object.values(r.profiles),count=status=>profiles.filter(p=>p.status===status).length;
 r.profile_counts={agreement:count('OBSERVED_AGREEMENT'),discrepancy:count('OBSERVED_MISMATCH'),unknown:count('UNKNOWN'),not_run:count('NOT_RUN')};
 r.status=r.profile_counts.unknown||r.profile_counts.not_run?'INCOMPLETE':r.profile_counts.discrepancy?'COMPLETED_WITH_DISCREPANCIES':'COMPLETED_BOUNDED_AGREEMENT';
 r.coverage=coverageFor(r.profiles);r.cost.wall_seconds=(performance.now()-started)/1000;
 await writeFile(join(out,'result.json'),json(r));await writeFile(join(out,'report.md'),renderReport(r));
 return {result:r,exit_code:r.status==='INCOMPLETE'?2:r.profile_counts.discrepancy?1:0};
}

if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{
  const options=parseArgs(process.argv.slice(2));
  if(options.help)console.log('MathGraph retained failure checks\n\nnode run.mjs --repo LOCAL_GIT --base REV --head REV --out NEW_DIRECTORY [--lean LEAN_4_35_BINARY] [--python python3] [--timeout-seconds 120] [--profiles COMMA_SEPARATED_IDS]\n\nDefault: all four retained profiles, every one of the 104 candidate prompts accounted for. Explicit profile omissions remain NOT_RUN. Missing or unsupported source is UNKNOWN. The 104 ledger rows do not establish 104 detectors. Reviewed local source only. Exit 0: all selected finite obligations agree and no profile omitted; 1: completed discrepancies; 2: UNKNOWN or NOT_RUN. No exit establishes complete catalogue coverage.\n\nProfiles:\n'+PROFILES.map(p=>p.id).join('\n'));
  else{const {result,exit_code}=await runCatalogue(options);console.log(json({status:result.status,profiles:result.profile_counts,coverage:result.coverage.counts,report:join(resolve(options.out),'report.md')}));process.exitCode=exit_code;}
 }catch(e){console.error(e.message);process.exitCode=2;}
}
