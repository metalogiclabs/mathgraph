#!/usr/bin/env node
// Execute an unchanged source projection of the real suite runner's runTest.
import {createHash} from 'node:crypto';
import {readFile,writeFile,mkdir,readdir,realpath} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import {dirname,join,relative,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {performance} from 'node:perf_hooks';

const HERE=dirname(fileURLToPath(import.meta.url));
const hash=value=>createHash('sha256').update(value).digest('hex');
const json=value=>JSON.stringify(value,null,2)+'\n';
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
export const REFUSAL_METHOD='suite-refusal-integrity-v1';
export const REFUSAL_CATALOGUE_IDS=[28,55,59,60,77,78,100];
export const REFUSAL_SCOPE='Finite controlled-process observations through the unchanged runTest function and Backend/TestResult declarations extracted from committed Tests/SuiteRunner/Main.lean. Actual Meta, Types, Init and CapstoneAttr dependencies are compiled; the repaired protocol module is compiled when used. Only the Lean backend route is exercised. A hashed timeout proxy records and forwards actual system-timeout stdout, stderr and status. Controlled producers model the explicitly adopted marker/status contract; full parser behavior, whole suite CLI/report gating, other backends, adversarial marker authenticity and all catalogue subtypes remain unqualified.';
const MAIN='Tests/SuiteRunner/Main.lean';
const DEPENDENCIES=['L4YAML/CapstoneAttr.lean','L4YAML/Init.lean','L4YAML/Spec/Types.lean','Tests/SuiteRunner/Meta.lean'];
const PROTOCOL='Tests/SuiteRunner/Protocol.lean';
const METHOD_FILES=['refusal.mjs','refusal-native.py','refusal-cases.json'];

export function extractProjection(source){
 const take=(name,start,end)=>{
  if(source.split(start).length!==2||source.split(end).length!==2)throw Error('UNSUPPORTED_SOURCE_SHAPE: '+name);
  const begin=source.indexOf(start),finish=source.indexOf(end);
  if(finish<=begin)throw Error('UNSUPPORTED_SOURCE_ORDER: '+name);
  const text=source.slice(begin,finish);
  return {text,identity:{start_byte:Buffer.byteLength(source.slice(0,begin)),end_byte:Buffer.byteLength(source.slice(0,finish)),sha256:hash(text)}};
 };
 const declarations=take('backend/result declarations','inductive Backend where','/-- Run a single test case against our parser (pure computation). -/');
 const runTest=take('runTest','def runTest (tc : TestCase)','/-- Summary statistics for a test run. -/');
 const protocol=runTest.text.includes('Protocol.classify');
 const rich=declarations.text.includes('| error (reason : String)')&&declarations.text.includes('| timeout\n');
 if(protocol!==rich)throw Error('UNSUPPORTED_RESULT_PROTOCOL_SHAPE');
 if(!source.includes('public import Tests.SuiteRunner.Meta')||
    (protocol&&!source.includes('public import Tests.SuiteRunner.Protocol')))throw Error('UNSUPPORTED_SOURCE_IMPORTS');
 const code='module\npublic import Tests.SuiteRunner.Meta\n'+(protocol?'public import Tests.SuiteRunner.Protocol\n':'')+
  '@[expose] public section\nopen Tests.SuiteRunner\n'+declarations.text+runTest.text+'\nend\n';
 return {code,sha256:hash(code),protocol,rich_result:rich,fragments:{declarations:declarations.identity,runTest:runTest.identity}};
}

function command(args){
 const p=spawnSync('git',args,{encoding:'utf8',timeout:30000,maxBuffer:1024*1024});
 if(p.error||p.status!==0)throw Error('GIT_OBJECT_UNAVAILABLE: '+(p.error?.message??p.stderr).slice(-700));
 return p.stdout;
}

async function sourceAt(repo,ref){
 const revision=command(['-C',repo,'rev-parse','--verify','--end-of-options',ref+'^{commit}']).trim();
 if(!/^[a-f0-9]{40}$/.test(revision))throw Error('INVALID_GIT_REVISION');
 const files={};
 const read=(path)=>{
  const blob=command(['-C',repo,'rev-parse','--verify',revision+':'+path]).trim();
  const p=spawnSync('git',['-C',repo,'cat-file','blob',blob],{timeout:30000,maxBuffer:512*1024});
  if(p.error||p.status!==0||p.stdout.length>262144)throw Error('MODULE_ABSENT_OR_TOO_LARGE: '+path);
  let content;try{content=new TextDecoder('utf-8',{fatal:true}).decode(p.stdout);}catch{throw Error('SOURCE_NOT_UTF8: '+path);}
  files[path]={content,git_blob:blob,source_sha256:hash(p.stdout)};
  return content;
 };
 const main=read(MAIN),projection=extractProjection(main);
 for(const path of DEPENDENCIES)read(path);
 if(projection.protocol)read(PROTOCOL);
 const identity={repository:'local-git:'+repo,revision,path:MAIN,git_blob:files[MAIN].git_blob,
  source_sha256:files[MAIN].source_sha256,fragments:projection.fragments,projection_sha256:projection.sha256,
  source_files:Object.fromEntries(Object.entries(files).map(([path,{content,...id}])=>[path,id])),
  protocol_module:projection.protocol?PROTOCOL:null,provenance:'LOCALLY_OBSERVED_GIT_OBJECT'};
 return {identity,files,projection};
}

export function observedOutcome(observed){
 if(!observed||!['PASS','FAIL','SKIP','ERROR','TIMEOUT'].includes(observed.kind))throw Error('UNRECOGNIZED_NATIVE_RESULT');
 // The original constructor exposes timeout as this exact fail reason.
 if(observed.kind==='FAIL'&&observed.reason==='timeout (possible infinite loop)')return 'TIMEOUT';
 return observed.kind;
}

export function assessRefusalArm(arm,snapshot,cases){
 const observations=[];
 let reason=arm?.reason??null;
 if(!arm||arm.build_exit!==0)reason??='SOURCE_PROJECTION_BUILD_FAILED';
 if(arm&&(!same(arm.source_hashes,Object.fromEntries(Object.entries(snapshot.files).map(([p,f])=>[p,f.source_sha256])))||
   arm.projection_sha256!==snapshot.projection.sha256))reason??='SOURCE_BINDING_MISMATCH';
 if(arm?.cases?.length!==cases.length)reason??='CASE_ROSTER_INCOMPLETE';
 for(const c of cases){
  const matches=(arm?.cases??[]).filter(r=>r.id===c.id);
  if(matches.length!==1||matches[0].complete!==true){reason??='CASE_EXECUTION_INCOMPLETE: '+c.id;continue;}
  const r=matches[0];
  try{
   if(r.observation.id!==c.id)throw Error('CASE_IDENTITY_MISMATCH');
   const outcome=observedOutcome(r.observation);
   observations.push({id:c.id,input:{expect_fail:c.expect_fail,yaml:c.expect_fail?'[\n':'[a]\n',
    behavior:c.behavior,exit_code:c.exit_code,stdout:c.stdout,stderr:c.stderr},expected:{outcome:c.expected},
    observed:{outcome,source_result:r.observation,process:r.process,backend_invocation:r.backend_invocation??null},
    passed:outcome===c.expected,differences:outcome===c.expected?[]:['expected '+c.expected+', observed '+outcome]});
  }catch(error){reason??=error.message+': '+c.id;}
 }
 const complete=!reason&&observations.length===cases.length;
 return {complete,reason,observations,mismatches:observations.filter(c=>!c.passed),
  projection_olean_sha256:arm?.projection_olean_sha256??null};
}

export function assessRefusalExecution(native,sources,cases){
 const base=assessRefusalArm(native?.base,sources.base,cases),head=assessRefusalArm(native?.head,sources.head,cases);
 const reason=native?.reason??(!base.complete||!head.complete?
  [['base',base],['head',head]].filter(([,arm])=>!arm.complete).map(([label,arm])=>label+': '+arm.reason).join('; '):null);
 return {base,head,status:reason?'UNKNOWN':head.mismatches.length?'OBSERVED_MISMATCH':'OBSERVED_AGREEMENT',...(reason?{reason}:{})};
}

async function methodIdentity(corpus){
 const files={};for(const name of METHOD_FILES)files[name]=hash(await readFile(join(HERE,name)));
 return {id:REFUSAL_METHOD,catalogue_revision:'2026-11-22-r2',catalogue_ids:REFUSAL_CATALOGUE_IDS,
  selection:'RETAINED_FIXED_PROFILE',corpus_sha256:files['refusal-cases.json'],case_count:corpus.cases.length,
  source_projection:'UNCHANGED_FUNCTION_AND_DECLARATION_BYTES_WITH_EXACT_DECLARED_DEPENDENCIES',
  contract:corpus.contract,files,hosted_admission:'NOT_REQUESTED'};
}

async function inventory(root,folder=root){
 const files={};for(const entry of await readdir(folder,{withFileTypes:true})){
  const path=join(folder,entry.name);
  if(entry.isDirectory())Object.assign(files,await inventory(root,path));
  else if(entry.isFile())files[relative(root,path)]=hash(await readFile(path));
 }return files;
}

export function renderRefusalReport(r){
 const title=r.status==='UNKNOWN'?'Comparison incomplete':r.status==='OBSERVED_MISMATCH'?
  'The head conflates at least one controlled process outcome':'The head preserves the selected process outcomes';
 const lines=['# MathGraph Check — suite refusal integrity','',`**${title}.**`,'',
  '## Requirement','',r.method?.contract??'The selected deliberate-result marker/status contract.',
  '', 'This check invokes the actual extracted `runTest` function. A deliberate refusal fixture is a protocol positive control; it does not establish that a real YAML parser refused correctly.',''];
 if(r.reason)lines.push('**Reason:** '+r.reason,'');
 lines.push('## Results','','| Case | Expected | Base | Head |','| --- | --- | --- | --- |');
 const ids=r.case_ids??[];
 for(const id of ids){
  const b=r.base?.observations?.find(c=>c.id===id),h=r.head?.observations?.find(c=>c.id===id);
  lines.push(`| ${id} | ${h?.expected.outcome??b?.expected.outcome??'not observed'} | ${b?.observed.outcome??'UNKNOWN'} | ${h?.observed.outcome??'UNKNOWN'} |`);
 }
 lines.push('');
 for(const name of ['base','head']){
  const s=r.subjects[name],a=r[name];
  if(s)lines.push(`**${name}:** commit \`${s.revision}\`; full Main source SHA-256 \`${s.source_sha256}\`; unchanged runTest fragment SHA-256 \`${s.fragments.runTest.sha256}\`.`,'');
  if(a)lines.push(a.complete?`${a.observations.length} individual process cases observed; ${a.mismatches.length} discrepancies.`:'UNKNOWN — '+a.reason+'.','');
 }
 lines.push('## Scope and reuse','',REFUSAL_SCOPE,'',
  'Exit 124 and an actual elapsed deadline are separate controls. Neither proves nontermination. A process can dishonestly emit a valid marker; this profile assumes the controlled producer is honest.','',
  'Cases, requirements and method are retained; both selected revisions execute afresh. Unknown source shapes or incomplete apparatus evidence produce UNKNOWN. Mappings to catalogue IDs describe finite coverage only.','',
  '## Cost and evidence','',`- Wall time: ${r.cost.wall_seconds.toFixed(3)} seconds.`,
  `- Driver subprocesses executed: ${r.cost.native_processes??'incomplete'}.`,
  `- Controlled backend invocations observed: ${r.cost.backend_invocations??'incomplete'}.`,
  '- Model calls: 0. Human trial and comparative advantage: NOT_RUN.',
  '- `result.json`: source/method identity and case observations.',
  '- `request.json`, `native.json`, `native-logs/`, `work/`: exact source projections, compiled modules, fixture identities, process output and invocation records.','',
  'This is an advisory local check for reviewed source. It grants no hosted admission or deployment authority.','');
 return lines.join('\n');
}

export async function runRefusal(options){
 const began=performance.now(),out=resolve(options.out);
 await mkdir(out,{recursive:false});
 const result={schema:'mathgraph.suite-refusal-check.v1',profile:REFUSAL_METHOD,status:'UNKNOWN',permission:'ADVISORY_ONLY',
  human_trial:'NOT_RUN',comparative_advantage:'NOT_RUN',scope:REFUSAL_SCOPE,subjects:{},
  cost:{model_calls:0,native_processes:null,backend_invocations:null,wall_seconds:0,human_seconds:null}};
 try{
  const timeout=Number(options.timeout??120);
  if(!Number.isFinite(timeout)||timeout<1||timeout>600)throw Error('INVALID_TIMEOUT');
  const repo=await realpath(options.repo),corpus=JSON.parse(await readFile(join(HERE,'refusal-cases.json'),'utf8'));
  if(corpus.profile!==REFUSAL_METHOD||!Array.isArray(corpus.cases)||corpus.cases.length===0||
   new Set(corpus.cases.map(c=>c.id)).size!==corpus.cases.length)throw Error('INVALID_FROZEN_CORPUS');
  result.case_ids=corpus.cases.map(c=>c.id);result.method=await methodIdentity(corpus);
  const sources={};
  for(const name of ['base','head']){sources[name]=await sourceAt(repo,options[name]);result.subjects[name]=sources[name].identity;}
  const request={sources,cases:corpus.cases,method:result.method};
  await writeFile(join(out,'request.json'),json(request));
  const requestSha=hash(await readFile(join(out,'request.json')));
  const processResult=spawnSync(options.python??'python3',[join(HERE,'refusal-native.py'),join(out,'request.json'),out,
   options.lean??process.env.MATHGRAPH_LEAN_BIN??'lean',String(timeout)],
   {encoding:'utf8',timeout:(timeout+15)*1000,maxBuffer:4*1024*1024});
  await writeFile(join(out,'driver.log'),(processResult.stdout??'')+(processResult.stderr??''));
  if(processResult.error||processResult.status!==0)throw Error('NATIVE_EXECUTION_INCOMPLETE: '+(processResult.error?.message??processResult.stderr).slice(-1500));
  const native=JSON.parse(await readFile(join(out,'native.json'),'utf8'));
  result.runtime=native.runtime;result.cost.native_processes=native.processes.filter(p=>p.executed).length;
  result.cost.backend_invocations=['base','head'].flatMap(n=>native[n]?.cases??[]).filter(c=>c.backend_invocation).length;
  if(hash(await readFile(join(out,'request.json')))!==requestSha||!same(result.method,await methodIdentity(corpus)))throw Error('METHOD_OR_INPUT_CHANGED_DURING_EXECUTION');
  Object.assign(result,assessRefusalExecution(native,sources,corpus.cases));
 }catch(error){result.status='UNKNOWN';result.reason=error.message;}
 result.cost.wall_seconds=(performance.now()-began)/1000;
 result.evidence=await inventory(out);
 await writeFile(join(out,'result.json'),json(result));
 await writeFile(join(out,'report.md'),renderRefusalReport(result));
 return {result,exit_code:result.status==='UNKNOWN'?2:result.status==='OBSERVED_MISMATCH'?1:0};
}

if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{
  const argv=process.argv.slice(2),options={};
  if(argv.includes('--help'))console.log('node refusal.mjs --repo LOCAL_GIT --base REV --head REV --out NEW_DIRECTORY --lean LEAN_4_35_BINARY [--python python3] [--timeout-seconds 120]\nExit 0: finite head agreement; 1: finite discrepancy; 2: UNKNOWN.');
  else{
   const allowed=new Set(['repo','base','head','out','lean','python','timeout-seconds']);
   for(let i=0;i<argv.length;i+=2){const k=argv[i]?.replace(/^--/,'');if(!argv[i]?.startsWith('--')||!allowed.has(k)||argv[i+1]===undefined||Object.hasOwn(options,k))throw Error('INVALID_ARGUMENT: '+argv[i]);options[k]=argv[i+1];}
   for(const k of ['repo','base','head','out'])if(!options[k])throw Error('MISSING_ARGUMENT: --'+k);
   options.timeout=options['timeout-seconds']??120;
   const {result,exit_code}=await runRefusal(options);
   console.log(json({status:result.status,reason:result.reason,base_mismatches:result.base?.mismatches.length,head_mismatches:result.head?.mismatches.length,report:join(resolve(options.out),'report.md'),cost:result.cost}));
   process.exitCode=exit_code;
  }
 }catch(error){console.error(error.message);process.exitCode=2;}
}
