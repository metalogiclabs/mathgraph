#!/usr/bin/env node
// A local finite observation adapter. It grants no hosted admission or action permission.
import {createHash} from 'node:crypto';
import {readFile,writeFile,mkdir,realpath,readdir} from 'node:fs/promises';
import {resolve,join,dirname,relative} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {performance} from 'node:perf_hooks';
import {REPORT_CASES,REPORT_PROFILE,REPORT_GATE,REPORT_METHOD,REPORT_CORPUS_SHA,
        REPORT_REFERENCE_RUNNER_SHA,reportProbePlan} from './report-integrity.mjs';
import {renderProbe,inspectArm} from '../lean-investigator-v1/contracts.mjs';
import {compareProbeRows} from './engine.mjs';
import {STATUS_METHOD,STATUS_CASES,STATUS_CORPUS_SHA,STATUS_REFERENCE_SHA,STATUS_SCOPE,
        statusPlan,statusObserver,assessStatusRevision,renderStatusReport} from './report-status.mjs';

const HERE=dirname(fileURLToPath(import.meta.url));
const hash=x=>createHash('sha256').update(x).digest('hex');
const json=x=>JSON.stringify(x,null,2)+'\n';
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const PASS='GUARD_PASSED',FAIL='CANDIDATE_ASSERTION_FAILURE';
const METHOD_FILES=['local-report-check.mjs','local-report-native.py','report-integrity.mjs',
 'report-cases.json','report-reference.py','engine.mjs','../lean-investigator-v1/contracts.mjs',
 '../lean-investigator-v1/native.py','report-status.mjs','report-status-cases.json','report-status-reference.py'];
const SCOPE='Finite profile for exact committed Reports.lean bytes in an isolated module with the declared empty HtmlReport dependency, original module guards and 19 fixed XML acceptance cases. Full dependency-environment correspondence, full reports CLI, XML conformance and whole-repository correctness remain UNKNOWN.';

function casePlan(){return {tests:REPORT_CASES.map(c=>({id:c.id,
 expression:'(junitCases '+JSON.stringify(c.input)+').toOption.isSome == '+c.accepted}))};}
function probe(id,expression){const code=renderProbe(REPORT_PROFILE,expression);return {id,code,sha256:hash(code)};}

export function assessRevision(arm,source){
 const plan=reportProbePlan();
 const groups=inspectArm(arm,{profile:REPORT_PROFILE,plan,source});
 const cases=inspectArm({...arm,probes:arm?.cases},{profile:REPORT_PROFILE,plan:casePlan(),source});
 const consistent=groups.rows.every(g=>g.execution===(cases.rows.filter(r=>REPORT_CASES.find(c=>c.id===r.id)?.group===g.id)
  .some(r=>r.execution===FAIL)?FAIL:PASS));
 const complete=groups.complete&&cases.complete&&consistent;
 const observations=complete?REPORT_CASES.map(c=>{
  const row=cases.rows.find(r=>r.id===c.id);
  return {...c,observed_acceptance:row.execution===PASS?c.accepted:!c.accepted,passed:row.execution===PASS};
 }):[];
 const reason=complete?null:arm?.build_exit!==0?'MODULE_BUILD_FAILED':!groups.source_ok?'SOURCE_BINDING_MISMATCH':
  !groups.controls_ok?'NATIVE_CONTROLS_FAILED':!groups.baseline_ok?'SELECTED_GATE_FAILED':
  !groups.complete?'GROUP_OBSERVATIONS_INCOMPLETE':!cases.complete?'CASE_OBSERVATIONS_INCOMPLETE':'GROUP_CASE_DISAGREEMENT';
 return {complete,reason,groups:complete?groups.rows:groups.rows.map(r=>({...r,execution:'UNKNOWN'})),observations,mismatches:observations.filter(c=>!c.passed)};
}

function parseArgs(argv){
 if(argv.includes('--help'))return {help:true};
 const allowed=new Set(['repo','base','head','out','lean','python','timeout-seconds','profile']);const options={};
 for(let i=0;i<argv.length;i+=2){const key=argv[i]?.replace(/^--/,'');
  if(!argv[i]?.startsWith('--')||!allowed.has(key)||argv[i+1]===undefined||Object.hasOwn(options,key))throw Error('INVALID_ARGUMENT: '+argv[i]);
  options[key]=argv[i+1];
 }
 for(const key of ['repo','base','head','out'])if(!options[key])throw Error('MISSING_ARGUMENT: --'+key);
 options.timeout=Number(options['timeout-seconds']??120);
 if(!Number.isFinite(options.timeout)||options.timeout<1||options.timeout>600)throw Error('INVALID_TIMEOUT: use 1..600 seconds');
 options.lean=options.lean??process.env.MATHGRAPH_LEAN_BIN??'lean';options.python=options.python??'python3';
 options.profile=options.profile??REPORT_METHOD;
 if(![REPORT_METHOD,STATUS_METHOD].includes(options.profile))throw Error('UNSUPPORTED_PROFILE: '+options.profile);
 return options;
}

function command(executable,args,options={}){
 const p=spawnSync(executable,args,{encoding:'utf8',timeout:30000,maxBuffer:8*1024*1024,...options});
 if(p.error)throw Error('COMMAND_UNAVAILABLE_OR_TIMEOUT: '+executable+': '+p.error.message);
 if(p.status!==0)throw Error('COMMAND_FAILED: '+executable+': '+(p.stderr||p.stdout).slice(-1800));
 return p.stdout;
}

async function sourceAt(repo,ref){
 let revision;
 try{revision=command('git',['-C',repo,'rev-parse','--verify','--end-of-options',ref+'^{commit}']).trim();}
 catch{throw Error('REVISION_UNAVAILABLE: '+ref);}
 if(!/^[a-f0-9]{40}$/.test(revision))throw Error('INVALID_GIT_REVISION');
 let blob,bytes;
 try{
  blob=command('git',['-C',repo,'rev-parse','--verify',revision+':'+REPORT_PROFILE.path]).trim();
  const p=spawnSync('git',['-C',repo,'cat-file','blob',blob],{timeout:30000,maxBuffer:262145});
  if(p.error||p.status!==0)throw Error('blob read failed');bytes=p.stdout;
 }catch{throw Error('MODULE_ABSENT_OR_UNREADABLE: '+revision+':'+REPORT_PROFILE.path);}
 if(bytes.length>262144)throw Error('SOURCE_TOO_LARGE');
 let source;try{source=new TextDecoder('utf-8',{fatal:true}).decode(bytes);}catch{throw Error('SOURCE_NOT_UTF8');}
 return {repository:'local-git:'+repo,revision,git_blob:blob,path:REPORT_PROFILE.path,
  source_sha256:hash(bytes),source,provenance:'LOCALLY_OBSERVED_GIT_OBJECT'};
}

async function methodIdentity(profile=REPORT_METHOD){
 const files={};for(const name of METHOD_FILES)files[name]=hash(await readFile(join(HERE,name)));
 const status=profile===STATUS_METHOD,corpus=status?'report-status-cases.json':'report-cases.json',reference=status?'report-status-reference.py':'report-reference.py';
 if(files[corpus]!== (status?STATUS_CORPUS_SHA:REPORT_CORPUS_SHA)||files[reference]!== (status?STATUS_REFERENCE_SHA:REPORT_REFERENCE_RUNNER_SHA))throw Error('FROZEN_REFERENCE_CHANGED');
 return {id:profile,plan_sha256:hash(JSON.stringify(status?statusPlan():reportProbePlan())),
  corpus_sha256:files[corpus],reference_sha256:files[reference],
  files,selection:'RETAINED_FIXED_PROFILE',hosted_admission:'NOT_REQUESTED'};
}

function display(execution){return {[PASS]:'Pass',[FAIL]:'Discrepancy',UNKNOWN:'Unknown'}[execution]??'Unknown';}
export function renderLocalReport(r){
 if(r.profile===STATUS_METHOD)return renderStatusReport(r);
 const title=r.status==='UNKNOWN'?'Comparison incomplete':r.status==='OBSERVED_MISMATCH'?
  'The head revision disagrees with the retained report checks':'The head revision satisfies the retained report checks';
 const lines=['# MathGraph Check — report integrity','',`**${title}.**`,'',
  '## Requirement','',
  'Reject six malformed XML envelopes, preserve six valid reports and preserve seven existing refusals. These are the existing operator-adopted finite expectations, with Python ElementTree as the separate acceptance reference.','',
  r.reference?.status==='OBSERVED_AGREEMENT'?'This run independently replayed the reference for all 19 cases.':'Reference execution has not been qualified in this run.',''];
 if(r.reason)lines.push('**Reason:** '+r.reason,'');
 lines.push('## Source revisions','');
 for(const label of ['base','head']){const s=r.subjects?.[label];if(s)lines.push(`- **${label}:** \`${s.revision}\`; source SHA-256 \`${s.source_sha256}\`.`);}
 lines.push('','Source identity is read from local Git objects. The command does not authenticate a remote publisher.','');
 if(r.comparison?.length){
  lines.push('## What changed','','| Obligation | Base | Head | Change |','| --- | --- | --- | --- |');
  for(const row of r.comparison)lines.push(`| ${reportProbePlan().tests.find(t=>t.id===row.id).hypothesis} | ${display(row.base)} | ${display(row.head)} | ${row.change.replaceAll('_',' ').toLowerCase()} |`);
  lines.push('');
 }
 for(const label of ['base','head'])if(r[label])lines.push(`**${label}:** ${r[label].complete?r[label].observations.length+' individual cases observed; '+r[label].mismatches.length+' discrepancies.':'UNKNOWN — '+r[label].reason+'.'}`,'');
 const witness=(r.head?.mismatches?.length?r.head.mismatches:r.base?.mismatches??[]).toSorted((a,b)=>Buffer.byteLength(a.input)-Buffer.byteLength(b.input))[0];
 if(witness){
  lines.push('## A distinguishing input','','Smallest failing input in this fixed corpus:','','```xml',witness.input,'```','',
   'Independent finite expectation: **'+(witness.accepted?'accept':'reject')+'**.');
  for(const label of ['base','head']){const observed=r[label]?.observations?.find(c=>c.id===witness.id);if(observed)lines.push(`- ${label}: **${observed.observed_acceptance?'accepted':'rejected'}**.`);}
  lines.push('');
 }
 lines.push('## Reuse and cost','','The requirement, corpus and probe method are retained. '+(r.base?.complete&&r.head?.complete?'Both revisions were executed afresh.':'Fresh execution is incomplete.')+' No earlier acceptance verdict is reused.','',
  `- Wall time: ${r.cost.wall_seconds.toFixed(3)} seconds.`,
  `- Native subprocesses: ${r.cost.native_processes??'not completed'}.`,
  '- Model calls: 0. Human effort, second-operator use and comparative advantage: NOT_RUN.','',
  '## Next step','',r.status==='UNKNOWN'?'Resolve the stated missing source, toolchain or execution evidence, then rerun into a new output directory.':
   r.status==='OBSERVED_MISMATCH'?'Review the distinguishing input and the source diff. A repair can be checked with the same command and unchanged expectations.':
   'Review the source diff and normal repository CI. The selected finite report checks pass; broader guarantees require their own evidence.','',
  '## Scope','',SCOPE,'',
  'This is a local finite observation, not hosted admission, automatic repair permission, independent human approval or a measured 10x improvement. Execution is for reviewed local source; it is not a hostile-source sandbox.','',
  '## Evidence','',
  '- `result.json`: available source/method identities, observations, comparison and measured costs.');
 for(const name of ['request.json','reference.json','native.json','driver.log'])if(r.evidence?.[name])lines.push('- `'+name+'`: retained evidence from this invocation.');
 if(Object.keys(r.evidence??{}).some(k=>k.startsWith('native-logs/')))lines.push('- `native-logs/`: raw execution output.');
 lines.push('');
 return lines.join('\n');
}

async function inventory(root,folder=root){
 const entries={};for(const item of await readdir(folder,{withFileTypes:true})){
  const path=join(folder,item.name);if(item.isDirectory())Object.assign(entries,await inventory(root,path));
  else if(item.isFile())entries[relative(root,path)]=hash(await readFile(path));
 }return entries;
}

export async function runLocal(options){
 const profile=options.profile??REPORT_METHOD,status=profile===STATUS_METHOD;
 if(![REPORT_METHOD,STATUS_METHOD].includes(profile))throw Error('UNSUPPORTED_PROFILE: '+profile);
 const started=performance.now(),out=resolve(options.out);
 try{await mkdir(out,{recursive:false});}catch(e){if(e.code==='EEXIST')throw Error('OUTPUT_ALREADY_EXISTS: '+out);throw e;}
 const result={schema:status?'mathgraph.local-report-status-check.v1':'mathgraph.local-report-check.v1',profile,status:'UNKNOWN',permission:'ADVISORY_ONLY',
  human_trial:'NOT_RUN',comparative_advantage:'NOT_RUN',scope:status?STATUS_SCOPE:SCOPE,subjects:{},
  cost:{model_calls:0,native_processes:null,wall_seconds:0,human_seconds:null}};
 try{
  const repo=await realpath(options.repo);result.method=await methodIdentity(profile);
  const sources={};
  for(const label of ['base','head']){
   sources[label]=await sourceAt(repo,options[label]);
   const {source,...identity}=sources[label];result.subjects[label]=identity;
  }
  const groups=status?[]:reportProbePlan().tests.map(t=>probe(t.id,t.expression));
  const cases=status?STATUS_CASES.map(c=>{const code=statusObserver(c);return {id:c.id,code,sha256:hash(code)};}):casePlan().tests.map(t=>probe(t.id,t.expression));
  const payload={sources,groups,cases,case_mode:status?'json':'guard',gate:REPORT_GATE,
   controls:{pass:probe('control_pass','true'),fail:probe('control_fail','false')}};
  await writeFile(join(out,'request.json'),json(payload));
  const requestHash=hash(await readFile(join(out,'request.json')));
  const referencePath=join(out,'reference.json');
  command(options.python,[join(HERE,status?'report-status-reference.py':'report-reference.py'),referencePath]);
  const reference=JSON.parse(await readFile(referencePath,'utf8'));
  const expected=status?STATUS_CASES.map(c=>({id:c.id,observed:c.expected})):REPORT_CASES.map(c=>({...c,observed_acceptance:c.accepted}));
  if(reference.runner_sha256!==result.method.reference_sha256||reference.corpus_sha256!==result.method.corpus_sha256||
   !same(reference.records,expected))throw Error('REFERENCE_INCOMPLETE_OR_DISAGREES');
  result.reference={status:'OBSERVED_AGREEMENT',input_count:reference.records.length,artifact_sha256:hash(await readFile(referencePath))};
  const p=spawnSync(options.python,[join(HERE,'local-report-native.py'),join(out,'request.json'),out,options.lean,String(options.timeout)],
   {encoding:'utf8',timeout:(options.timeout+15)*1000,maxBuffer:4*1024*1024});
  await writeFile(join(out,'driver.log'),(p.stdout??'')+(p.stderr??''));
  if(p.error||p.status!==0)throw Error('NATIVE_EXECUTION_INCOMPLETE: '+(p.error?.message??p.stderr??'').slice(-1600));
  const native=JSON.parse(await readFile(join(out,'native.json'),'utf8'));
  result.runtime=native.runtime;result.cost.native_processes=native.processes.filter(p=>p.executed).length;
  if(hash(await readFile(join(out,'request.json')))!==requestHash||!same(result.method,await methodIdentity(profile))||
   hash(await readFile(referencePath))!==result.reference.artifact_sha256)throw Error('METHOD_OR_INPUT_CHANGED_DURING_EXECUTION');
  for(const label of ['base','head'])result[label]=(status?assessStatusRevision:assessRevision)(native[label],sources[label].source);
  result.comparison=compareProbeRows(result.base.groups,result.head.groups,{complete:result.base.complete});
  if(!result.base.complete||!result.head.complete)result.reason=[['base',result.base],['head',result.head]].filter(([,v])=>!v.complete).map(([n,v])=>n+': '+v.reason).join('; ');
  else result.status=result.head.mismatches.length?'OBSERVED_MISMATCH':'OBSERVED_AGREEMENT';
 }catch(error){result.status='UNKNOWN';result.reason=error.message;}
 result.cost.wall_seconds=(performance.now()-started)/1000;
 result.evidence=await inventory(out);
 await writeFile(join(out,'result.json'),json(result));
 await writeFile(join(out,'report.md'),renderLocalReport(result));
 return {result,exit_code:result.status==='UNKNOWN'?2:result.status==='OBSERVED_MISMATCH'?1:0};
}

if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{
  const options=parseArgs(process.argv.slice(2));
  if(options.help)console.log('MathGraph local report check\n\nnode local-report-check.mjs --repo LOCAL_GIT --base REV --head REV --out NEW_DIRECTORY [--profile junit-report-integrity-v1|junit-status-preservation-v1] [--lean LEAN_4_35_BINARY] [--python python3] [--timeout-seconds 120]\n\nDefault: retained 19-case XML acceptance profile. Optional status profile: 8 cases through actual JUnit rows and HTML. Source: committed Tests/SuiteRunner/Reports.lean. Local reviewed source only. Exit: 0 finite head agreement, 1 finite discrepancy, 2 UNKNOWN.');
  else{const {result,exit_code}=await runLocal(options);console.log(json({status:result.status,reason:result.reason,report:join(resolve(options.out),'report.md'),cost:result.cost}));process.exitCode=exit_code;}
 }catch(error){console.error(error.message);process.exitCode=2;}
}
