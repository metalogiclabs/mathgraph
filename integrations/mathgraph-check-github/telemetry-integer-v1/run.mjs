import {createHash} from 'node:crypto';
import {readFile,writeFile,mkdir,realpath,readdir} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import {join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {performance} from 'node:perf_hooks';

export const PROFILE='telemetry-integer-identity-v1';
const SOURCE='openc3/python/openc3/accessors/accessor.py';
const HERE=fileURLToPath(new URL('.',import.meta.url));
const hash=x=>createHash('sha256').update(x).digest('hex');
const json=x=>JSON.stringify(x,null,2)+'\n';
export const SCOPE='Finite INT/UINT conversion cases through the committed OpenC3 Accessor module. The ConfigParser import is replaced by a refusing stub; every function body is unchanged. BOOL, complete package/packet paths, hostile-source isolation, all-input correctness, mission authority and commercial value are outside this profile.';

async function methodIdentity(){
 const files={};for(const name of ['run.mjs','native.py','corpus.py'])files[name]=hash(await readFile(join(HERE,name)));
 return {id:PROFILE,files,selection:'RETAINED_FIXED_PROFILE'};
}
function git(repo,args,{binary=false}={}){
 const p=spawnSync('git',['-C',repo,...args],{encoding:binary?undefined:'utf8',timeout:30000,maxBuffer:262144,
  env:{...process.env,GIT_NO_LAZY_FETCH:'1'}});
 if(p.error||p.status!==0)throw Error('SOURCE_OR_REVISION_UNAVAILABLE');
 return binary?p.stdout:p.stdout.trim();
}
async function sourceAt(repo,ref){
 const revision=git(repo,['rev-parse','--verify','--end-of-options',ref+'^{commit}']);
 if(!/^[a-f0-9]{40}$/.test(revision))throw Error('INVALID_SOURCE_REVISION');
 const git_blob=git(repo,['rev-parse','--verify',revision+':'+SOURCE]);
 if(!/^[a-f0-9]{40}$/.test(git_blob))throw Error('INVALID_SOURCE_BLOB');
 const bytes=git(repo,['cat-file','blob',git_blob],{binary:true});
 return {identity:{repository:'local-git:'+repo,revision,path:SOURCE,git_blob,
  source_sha256:hash(bytes),authority:'LOCALLY_OBSERVED_GIT_OBJECT'},bytes};
}
function validateNative(native,source){
 const rows=native?.observations;
 if(native?.schema!=='mathgraph.telemetry-integer-native.v1'||native.complete!==true||
  native.source_sha256!==source.source_sha256||!Array.isArray(rows)||rows.length!==108||
  !Array.isArray(native.case_ids)||native.case_ids.length!==108||new Set(native.case_ids).size!==108||
  rows.some((r,i)=>r.id!==native.case_ids[i]||typeof r.passed!=='boolean')||
  JSON.stringify(native.mismatches)!==JSON.stringify(rows.filter(r=>!r.passed).map(r=>r.id)))throw Error('NATIVE_RECEIPT_INCOMPLETE_OR_INCONSISTENT');
 return native;
}
export function renderReport(r){
 const lines=['# MathGraph Check — telemetry integer identity','',`**${r.status}**`,'',
  '## Requirement','',r.obligation,'',
  'The operator selects this finite profile. Mission/customer ratification and full requirement adequacy are not established by selecting it.','',
  '## Observations','','| Revision | Commit | Cases | Discrepancies |','| --- | --- | ---: | ---: |'];
 for(const side of ['base','head'])lines.push(`| ${side} | ${r.subjects[side]?.revision??'unavailable'} | ${r[side]?.observations?.length??'UNKNOWN'} | ${r[side]?.mismatches?.length??'UNKNOWN'} |`);
 for(const side of ['base','head'])if(r[side]?.reason)lines.push('',`- ${side}: ${r[side].reason}`);
 const witness=r.head?.observations?.find(x=>!x.passed)??r.base?.observations?.find(x=>!x.passed);
 if(witness)lines.push('','## Retained witness','',`- Input: \`${witness.input_repr}\`.`,
  `- Required value: \`${witness.expected_repr}\`.`,`- Observed value: \`${witness.actual_repr}\`.`,
  `- Case: \`${witness.id}\`. The arm-specific result contains every observation.`);
 lines.push('','## Scope','',SCOPE,'',
  'This is known-class calibration/reuse, not blind discovery, certification or permission to deploy. Each invocation executes both exact source revisions afresh. A changed source or requirement needs a new check; historical results remain historical.','',
  '## Cost and evidence','',`- Wall seconds: ${r.cost.wall_seconds.toFixed(3)}.`,
  `- Native processes: ${r.cost.native_processes}. Model calls: 0.`,
  '- Human effort, independent operator use and comparative value: NOT_RUN.',
  '- result.json: identities, method digests, observations, dependencies and evidence hashes.',
  '- base/ and head/: exact source, request, native receipt and raw driver log when available.','');
 return lines.join('\n');
}
export async function runNumerical(options){
 const started=performance.now(),out=resolve(options.out);await mkdir(out,{recursive:false});
 const method=await methodIdentity();
 const r={schema:'mathgraph.telemetry-integer-check.v1',profile:PROFILE,status:'UNKNOWN',permission:'ADVISORY_ONLY',
  scope:SCOPE,obligation:'Preserve the exact integer value and integer type for the 64-bit INT/UINT scalar and array forms in the fixed corpus; preserve its declared fractional/None compatibility and invalid-input refusals.',
  requirement_authority:'OPERATOR_SELECTED_FINITE_EXPECTATIONS; MISSION_AUTHORITY_NOT_ESTABLISHED',
  method,subjects:{},cost:{model_calls:0,native_processes:0,wall_seconds:0,human_effort:'NOT_RUN',comparative_value:'NOT_RUN'}};
 let repo;
 try{repo=await realpath(options.repo);}catch{r.reason='LOCAL_REPOSITORY_UNAVAILABLE';}
 for(const side of ['base','head']){
  const folder=join(out,side);await mkdir(folder);
  try{
   if(!repo)throw Error(r.reason);
   const source=await sourceAt(repo,options[side]);r.subjects[side]=source.identity;
   const source_file=join(folder,'accessor.py');await writeFile(source_file,source.bytes);
   const request=join(folder,'request.json'),receipt=join(folder,'native.json');
   await writeFile(request,json({source_file,source_sha256:source.identity.source_sha256}));
   r.cost.native_processes++;
   const p=spawnSync(options.python??'python3',['-I','-S','-B',join(HERE,'native.py'),request,receipt],
    {encoding:'utf8',timeout:(options.timeout??120)*1000,maxBuffer:1024*1024,
     env:{PATH:process.env.PATH,LANG:'C.UTF-8'}});
   await writeFile(join(folder,'driver.log'),(p.stdout??'')+(p.stderr??''));
   if(p.error||p.status!==0)throw Error('NATIVE_EXECUTION_INCOMPLETE: '+(p.error?.code??'exit '+p.status));
   r[side]=validateNative(JSON.parse(await readFile(receipt,'utf8')),source.identity);
   if(hash(await readFile(source_file))!==source.identity.source_sha256)throw Error('SOURCE_CHANGED_DURING_EXECUTION');
  }catch(e){r[side]={complete:false,reason:e.message};}
 }
 if(JSON.stringify(method)!==JSON.stringify(await methodIdentity())){
  r.reason='METHOD_CHANGED_DURING_EXECUTION';for(const side of ['base','head'])r[side]={complete:false,reason:r.reason};
 }
 if(r.base.complete&&r.head.complete)r.status=r.head.mismatches.length?'OBSERVED_MISMATCH':'OBSERVED_AGREEMENT';
 r.dependencies={source_revisions:r.subjects,method,requirement:hash(r.obligation),runtime:{base:r.base.runtime,head:r.head.runtime}};
 r.cost.wall_seconds=(performance.now()-started)/1000;
 r.evidence={};for(const side of ['base','head'])for(const name of await readdir(join(out,side)))r.evidence[side+'/'+name]=hash(await readFile(join(out,side,name)));
 await writeFile(join(out,'result.json'),json(r));await writeFile(join(out,'report.md'),renderReport(r));
 return {result:r,exit_code:r.status==='UNKNOWN'?2:r.status==='OBSERVED_MISMATCH'?1:0};
}
