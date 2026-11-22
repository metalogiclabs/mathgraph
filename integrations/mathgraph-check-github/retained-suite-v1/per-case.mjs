#!/usr/bin/env node
// Retained EA01 observation profile. No hosted admission or subject mutation.
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {readFile,writeFile,mkdir,realpath,readdir} from 'node:fs/promises';
import {dirname,join,resolve,relative} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {performance} from 'node:perf_hooks';

const HERE=dirname(fileURLToPath(import.meta.url));
const hash=x=>createHash('sha256').update(x).digest('hex');
const json=x=>JSON.stringify(x,null,2)+'\n';
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const SOURCE_PATH='Tests/SuiteRunner/Reports.lean';
const PRESETS=['unlimited','default','strict','permissive','safe_tags'];
const FAMILIES=['aggregate-counts-v1','per-case-acceptance-v2'];
const METHOD_FILES=['per-case.mjs','per-case-native.py','per-case-reference.py','per-case-cases.json'];
export const PER_CASE_METHOD='suite-per-case-agreement-v1';
const corpusBytes=readFileSync(join(HERE,'per-case-cases.json'));
export const PER_CASE_CASES=JSON.parse(corpusBytes);
export const PER_CASE_CORPUS_SHA=hash(corpusBytes);
const SCOPE='Five frozen observation scenarios through the actual Reports comparison, serialized readback and HTML consumers. Source is an exact local Git blob, compiled as a standalone module with its original guards and a disclosed empty HtmlReport dependency. Backend observations are controlled fixtures; the four YAML parsers and Main.runCompare do not execute. No whole-domain, full CLI exit, parsed-value equality or YAML conformance claim.';
// These are the actual two supported report styles, not subject-supplied trust
// flags. New styles/markup need review; hidden or nonrendered claims are UNKNOWN.
const STYLES={
  'aggregate-counts-v1':'14895d92d287f3a241bbfb739ce2ad97a2b4cc3a8b37e5cc69c52263174cbe02',
  'per-case-acceptance-v2':'1939705a74531b0524578cd4b8657e139ab01d675914b5d880cc75f5a68d904e'
};
const VERDICTS={
  'aggregate-counts-v1':[
    '✗ Backend mismatch detected!',
    '✓ All backends produce identical results for every preset'
  ],
  'per-case-acceptance-v2':[
    '✗ Per-case acceptance comparison failed or has incomplete evidence',
    '✓ Per-case acceptance agrees for all four backends and five presets (values/output not compared)'
  ]
};

function presetClaimMatches(row,family){
  const {preset,agreement,line}=row;
  if(family==='aggregate-counts-v1'){
    if(agreement)return new RegExp('^'+preset.padEnd(12,' ')+': [0-9]+ passed, [0-9]+ failed, [0-9]+ skipped \\([0-9]+ total\\) — all 4 backends identical$').test(line);
    const tuple='\\([0-9]+, [0-9]+, [0-9]+, [0-9]+\\)';
    const body=['lean','c','python','rust'].map(b=>"'"+b+"': "+tuple).join(', ');
    return new RegExp("^MISMATCH for preset '"+preset+"': \\{"+body+'\\}$').test(line);
  }
  if(agreement)return new RegExp('^'+preset+': [0-9]+ accepted, [0-9]+ rejected, [0-9]+ skipped — per-case acceptance agrees across all 4 backends$').test(line);
  return /^INCOMPLETE OR MISMATCH: \S[^\r\n]*$/.test(line);
}

export function renderedAgreement(html,family){
  const fail=()=>{throw Error('HTML_TERMINAL_STATUS_UNRECOGNIZED');};
  if(typeof html!=='string'||!FAMILIES.includes(family)||html.includes('<!--'))fail();
  let styleCount=0;
  const markup=html.replace(/<style>([\s\S]*?)<\/style>/g,(_,css)=>{
    if(++styleCount>1||hash(css)!==STYLES[family])fail();
    return '<style></style>';
  });
  const allowed=new Set(['html','head','meta','title','style','body','h1','h2','table','tr','th','td','p']);
  const stack=[],paragraphs=[];
  let activeParagraph=null;
  let end=0;
  for(const token of markup.matchAll(/<[^<>]*>/g)){
    if(markup.slice(end,token.index).includes('<'))fail();end=token.index+token[0].length;
    if(token[0]==='<!DOCTYPE html>')continue;
    const parsed=token[0].match(/^<(\/)?([a-z][a-z0-9]*)([^<>]*)>$/);
    if(!parsed||!allowed.has(parsed[2]))fail();
    const [,closing,tag,raw]=parsed,attrs=raw.trim();
    if(closing){
      if(attrs||stack.at(-1)!==tag)fail();
      if(tag==='p'&&activeParagraph&&activeParagraph.depth===stack.length){
        const content=markup.slice(activeParagraph.start,token.index);
        if(content.includes('<')||/&(?!amp;|lt;|gt;|quot;|#x27;)/.test(content))fail();
        const entities={'&amp;':'&','&lt;':'<','&gt;':'>','&quot;':'"','&#x27;':"'"};
        const text=content.replace(/&(?:amp|lt|gt|quot|#x27);/g,x=>entities[x]).trim();
        paragraphs.push({css:activeParagraph.css,text});activeParagraph=null;
      }
      stack.pop();continue;
    }
    if(tag==='html'){if(attrs&&!/^lang=(['"])en\1$/.test(attrs))fail();}
    else if(tag==='meta'){if(!/^charset=(['"])utf-8\1$/.test(attrs)||stack.at(-1)!=='head')fail();}
    else if(tag==='p'||tag==='td'){
      if(attrs&&!/^class=(['"])(?:summary )?(?:match|mismatch)\1$/.test(attrs))fail();
      if(tag==='p'&&attrs){
        if(activeParagraph||stack.some(t=>['head','title','style'].includes(t)))fail();
        activeParagraph={css:attrs.match(/^class=(['"])(.*?)\1$/)[2],start:end,depth:stack.length+1};
      }
    }else if(attrs)fail();
    if(tag==='style'&&(stack.at(-1)!=='head'||styleCount!==1))fail();
    if(tag!=='meta')stack.push(tag);
  }
  if(stack.length||markup.slice(end).includes('<'))fail();
  const accepted=family==='aggregate-counts-v1'?'summary match':'match';
  const rejected=family==='aggregate-counts-v1'?'summary mismatch':'mismatch';
  const terminal=paragraphs.filter(p=>p.css===accepted||p.css===rejected);
  if(terminal.length!==1)throw Error('HTML_TERMINAL_STATUS_UNRECOGNIZED');
  const agreement=terminal[0].css===accepted,text=terminal[0].text;
  if(agreement||family==='aggregate-counts-v1'){
    if(text!==VERDICTS[family][Number(agreement)])fail();
  }else if(!/^Insufficient or inconsistent evidence: \S[^\r\n]*$/.test(text))fail();
  return agreement;
}

export function assessPerCaseArm(raw,source){
  const unknown=reason=>({complete:false,reason,observations:[],mismatches:[]});
  if(raw?.source_sha256!==source?.source_sha256)return unknown('SOURCE_BINDING_MISMATCH');
  if(raw?.corpus_sha256!==PER_CASE_CORPUS_SHA)return unknown('CORPUS_BINDING_MISMATCH');
  if(!FAMILIES.includes(raw.schema_family))return unknown(raw.reason??'UNSUPPORTED_COMPARISON_API');
  if(raw.build_exit!==0)return unknown(raw.reason??'MODULE_BUILD_FAILED');
  const pass=raw.controls?.pass,fail=raw.controls?.fail;
  if(pass?.exit!==0||pass.guard_false!==false||pass.other_errors!==false||
     fail?.exit!==1||fail.guard_false!==true||fail.other_errors!==false)return unknown('NATIVE_CONTROLS_FAILED');
  if(raw.observer_exit!==0)return unknown(raw.reason??'OBSERVER_EXECUTION_FAILED');
  if(raw.source_preserved!==true||raw.inputs_preserved!==true||!/^[a-f0-9]{64}$/.test(raw.observer_sha256??''))
    return unknown('SOURCE_OR_OBSERVER_CHANGED');
  const rows=raw.observations;
  if(!Array.isArray(rows)||rows.length!==PER_CASE_CASES.length||
    !same(rows.map(r=>r?.id).toSorted(),PER_CASE_CASES.map(c=>c.id).toSorted()))return unknown(raw.reason??'OBSERVER_CASE_COVERAGE_INCOMPLETE');
  const observations=[];
  try{
    for(const fixture of PER_CASE_CASES){
      const row=rows.find(r=>r.id===fixture.id);
      if(typeof row.agreement!=='boolean'||typeof row.readback_agreement!=='boolean'||typeof row.decoded_ok!=='boolean'||
        typeof row.verdict!=='string'||typeof row.serialized!=='string'||typeof row.html!=='string'||
        !Array.isArray(row.preset_agreement)||row.preset_agreement.length!==PRESETS.length||
        !same(row.preset_agreement.map(r=>r?.preset).toSorted(),PRESETS.toSorted())||
        !row.preset_agreement.every(r=>typeof r.agreement==='boolean'&&typeof r.line==='string'))
        return unknown('OBSERVER_OUTPUT_INVALID');
      if(row.verdict!==VERDICTS[raw.schema_family][Number(row.agreement)])return unknown('OBSERVER_VERDICT_TEXT_MISMATCH');
      if(!row.preset_agreement.every(r=>presetClaimMatches(r,raw.schema_family)))return unknown('OBSERVER_PRESET_TEXT_MISMATCH');
      const rendered_agreement=renderedAgreement(row.html,raw.schema_family);
      const observed={agreement:row.agreement,readback_agreement:row.readback_agreement,rendered_agreement,
        preset_agreement:PRESETS.map(p=>({preset:p,agreement:row.preset_agreement.find(r=>r.preset===p).agreement}))};
      const expected=fixture.expected.agreement;
      observations.push({id:fixture.id,description:fixture.description,expected:fixture.expected,observed,
        passed:[observed.agreement,observed.readback_agreement,observed.rendered_agreement].every(v=>v===expected)&&
          same(observed.preset_agreement,fixture.expected.preset_agreement),preset_agreement:row.preset_agreement,
        verdict:row.verdict,decoded_ok:row.decoded_ok});
    }
  }catch(error){return unknown(error.message);}
  return {complete:true,reason:null,schema_family:raw.schema_family,observations,
    mismatches:observations.filter(r=>!r.passed)};
}

function command(executable,args,options={}){
  const p=spawnSync(executable,args,{encoding:'utf8',timeout:30000,maxBuffer:8*1024*1024,...options});
  if(p.error||p.status!==0)throw Error('COMMAND_FAILED: '+executable+': '+(p.error?.message??p.stderr??p.stdout??'').slice(-1500));
  return p.stdout;
}

async function sourceAt(repo,ref){
  let revision;
  try{revision=command('git',['-C',repo,'rev-parse','--verify','--end-of-options',ref+'^{commit}']).trim();}
  catch{throw Error('REVISION_UNAVAILABLE: '+ref);}
  if(!/^[a-f0-9]{40}$/.test(revision))throw Error('INVALID_GIT_REVISION');
  let blob,bytes;
  try{
    blob=command('git',['-C',repo,'rev-parse','--verify',revision+':'+SOURCE_PATH]).trim();
    const p=spawnSync('git',['-C',repo,'cat-file','blob',blob],{timeout:30000,maxBuffer:262145});
    if(p.error||p.status!==0)throw Error('source unavailable');bytes=p.stdout;
  }catch{throw Error('MODULE_ABSENT_OR_UNREADABLE: '+revision+':'+SOURCE_PATH);}
  if(bytes.length>262144)throw Error('SOURCE_TOO_LARGE');
  let source;try{source=new TextDecoder('utf-8',{fatal:true}).decode(bytes);}catch{throw Error('SOURCE_NOT_UTF8');}
  return {repository:'local-git:'+repo,revision,git_blob:blob,path:SOURCE_PATH,source_sha256:hash(bytes),
    provenance:'LOCALLY_OBSERVED_GIT_OBJECT',source};
}

async function methodIdentity(){
  const files={};for(const name of METHOD_FILES)files[name]=hash(await readFile(join(HERE,name)));
  if(files['per-case-cases.json']!==PER_CASE_CORPUS_SHA)throw Error('FROZEN_CORPUS_CHANGED');
  return {id:PER_CASE_METHOD,input_count:PER_CASE_CASES.length,backends:4,presets:5,
    corpus_sha256:PER_CASE_CORPUS_SHA,reference_sha256:files['per-case-reference.py'],files,
    requirement_authority:'OPERATOR_ADOPTED_FINITE_KEYED_AGREEMENT',
    selection:'RETAINED_FIXED_PROFILE',hosted_admission:'NOT_REQUESTED'};
}

async function inventory(root,folder=root){
  const files={};for(const entry of await readdir(folder,{withFileTypes:true})){
    const path=join(folder,entry.name);
    if(entry.isDirectory())Object.assign(files,await inventory(root,path));
    else if(entry.isFile())files[relative(root,path)]=hash(await readFile(path));
  }return files;
}

function renderReport(r){
  const lines=['# MathGraph Check — retained per-case agreement','',
    '**'+r.status+'**','',
    '## Requirement','',
    'Compare keyed case outcomes. Equal aggregate totals alone must not establish agreement. Reordering one backend must preserve agreement when the keyed observations are identical.','',
    'This reuses the known EA01 failure class. Five scenarios contain a complete four-backend × five-preset roster, with two keyed observations per run. The strict-only scenario is one nondefault-preset control; it is not exhaustive preset defect coverage.',''];
  if(r.reason)lines.push('**Reason:** '+r.reason,'');
  lines.push('## Source and observations','','| Arm | Revision | Complete | Discrepancies |','| --- | --- | --- | --- |');
  for(const label of ['base','head']){
    const s=r.subjects[label],arm=r[label];
    lines.push(`| ${label} | ${s?.revision??'unavailable'} | ${arm?.complete===true?'yes':'UNKNOWN'} | ${arm?.complete?arm.mismatches.length:'UNKNOWN'} |`);
  }
  if(r.base?.complete&&r.head?.complete){
    lines.push('','| Scenario | Independent agreement expectation | Base | Head |','| --- | --- | --- | --- |');
    for(const c of PER_CASE_CASES){
      const display=label=>r[label].observations.find(o=>o.id===c.id).passed?'matches requirement':'discrepancy';
      lines.push(`| ${c.id} | ${c.expected.agreement?'agree':'reject agreement'} | ${display('base')} | ${display('head')} |`);
    }
  }
  lines.push('','## Evidence and cost','',
    '- `request.json`, `corpus.json`, `reference.json`, `native.json` and `native-logs/` retain source bindings, literal inputs, independent expectations and actual consumer output.',
    '- `work/` retains exact source, the disclosed dependency stub, original compiled module and generated observers.',
    `- Wall time: ${r.cost.wall_seconds.toFixed(3)} seconds. Native subprocesses: ${r.cost.native_processes??'incomplete'}. Model calls: 0.`,
    '- Source identity comes from local Git objects; no remote publisher authentication is asserted.','',
    '## Boundary','',SCOPE,'',
    'Execution is for reviewed local source and is not a hostile-source sandbox. Results are advisory. Human trial and comparative advantage remain NOT_RUN.','');
  return lines.join('\n');
}

export async function runPerCase(options){
  const started=performance.now(),out=resolve(options.out);
  await mkdir(out,{recursive:false});
  const result={schema:'mathgraph.retained-suite-per-case.v1',profile:PER_CASE_METHOD,status:'UNKNOWN',
    permission:'ADVISORY_ONLY',human_trial:'NOT_RUN',comparative_advantage:'NOT_RUN',scope:SCOPE,subjects:{},
    cost:{model_calls:0,native_processes:null,wall_seconds:0,human_seconds:null}};
  try{
    const timeout=Number(options.timeout??120),python=options.python??'python3',lean=options.lean??process.env.MATHGRAPH_LEAN_BIN??'lean';
    if(!Number.isFinite(timeout)||timeout<1||timeout>600)throw Error('INVALID_TIMEOUT');
    result.method=await methodIdentity();
    const repo=await realpath(options.repo),sources={};
    for(const label of ['base','head']){
      sources[label]=await sourceAt(repo,options[label]);
      const {source,...identity}=sources[label];result.subjects[label]=identity;
    }
    await writeFile(join(out,'request.json'),json({sources}));
    await writeFile(join(out,'corpus.json'),corpusBytes);
    const requestHash=hash(await readFile(join(out,'request.json')));
    const referencePath=join(out,'reference.json');
    command(python,[join(HERE,'per-case-reference.py'),referencePath]);
    const reference=JSON.parse(await readFile(referencePath,'utf8'));
    if(reference.runner_sha256!==result.method.reference_sha256||reference.corpus_sha256!==PER_CASE_CORPUS_SHA||
      !same(reference.records,PER_CASE_CASES.map(c=>({id:c.id,observed:c.expected}))))throw Error('REFERENCE_INCOMPLETE_OR_DISAGREES');
    result.reference={status:'OBSERVED_AGREEMENT',input_count:reference.records.length,artifact_sha256:hash(await readFile(referencePath))};
    const p=spawnSync(python,[join(HERE,'per-case-native.py'),join(out,'request.json'),out,lean,String(timeout)],
      {encoding:'utf8',timeout:(timeout+15)*1000,maxBuffer:4*1024*1024});
    await writeFile(join(out,'driver.log'),(p.stdout??'')+(p.stderr??''));
    let native;try{native=JSON.parse(await readFile(join(out,'native.json'),'utf8'));}catch{}
    if(native){result.runtime=native.runtime;result.cost.native_processes=native.processes?.filter(p=>p.executed).length??null;}
    if(p.error||p.status!==0||!native)throw Error('NATIVE_EXECUTION_INCOMPLETE: '+(native?.failure??p.error?.message??p.stderr??'').slice(-1600));
    if(hash(await readFile(join(out,'request.json')))!==requestHash||hash(await readFile(join(out,'corpus.json')))!==PER_CASE_CORPUS_SHA||
      !same(result.method,await methodIdentity())||hash(await readFile(referencePath))!==result.reference.artifact_sha256)
      throw Error('METHOD_OR_INPUT_CHANGED_DURING_EXECUTION');
    for(const label of ['base','head'])result[label]=assessPerCaseArm(native[label],sources[label]);
    if(result.base.complete&&result.head.complete)
      result.status=result.head.mismatches.length?'OBSERVED_MISMATCH':'OBSERVED_AGREEMENT';
    else result.reason=['base','head'].filter(label=>!result[label].complete).map(label=>label+': '+result[label].reason).join('; ');
  }catch(error){result.status='UNKNOWN';result.reason=error.message;}
  result.cost.wall_seconds=(performance.now()-started)/1000;
  result.evidence=await inventory(out);
  await writeFile(join(out,'result.json'),json(result));
  await writeFile(join(out,'report.md'),renderReport(result));
  return {result,exit_code:result.status==='UNKNOWN'?2:result.status==='OBSERVED_MISMATCH'?1:0};
}

if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  try{
    const options={};const args=process.argv.slice(2);
    for(let i=0;i<args.length;i+=2){
      const name=args[i]?.replace(/^--/,'');
      if(!args[i]?.startsWith('--')||!['repo','base','head','out','lean','python','timeout'].includes(name)||args[i+1]===undefined||Object.hasOwn(options,name))throw Error('INVALID_ARGUMENT');
      options[name]=args[i+1];
    }
    for(const key of ['repo','base','head','out'])if(!options[key])throw Error('MISSING_ARGUMENT: --'+key);
    const {result,exit_code}=await runPerCase(options);
    console.log(json({status:result.status,reason:result.reason,cost:result.cost,report:join(resolve(options.out),'report.md')}));
    process.exitCode=exit_code;
  }catch(error){console.error(error.message);process.exitCode=2;}
}
