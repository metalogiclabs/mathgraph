// Qualification-only native wrapper for two exact first-party Artin PR heads.
// The credentialless job executes only the pre-registered source bytes.
import {createHash} from 'node:crypto';
import {readFile,lstat,mkdir,writeFile} from 'node:fs/promises';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {runControlledArtinCase} from './artin-native.mjs';
import {assessOmmClaim} from './claim-admission.mjs';
import {formatOmmClaimReport} from './report.mjs';
import {buildOmmAppCheckPreview} from './app-check.mjs';

const exec=promisify(execFile);
const sha=s=>createHash('sha256').update(s).digest('hex');
const artifactErrors=new Set(['NATIVE_OLEAN_PREEXISTS','NATIVE_OLEAN_MISSING',
 'NATIVE_OLEAN_CHANGED','NATIVE_OLEAN_IMPORT_MISMATCH','NATIVE_OLEAN_UNEXPECTED_PART']);

export async function qualifyArtinDirectory({directory,mathlibGit,runUrl,run}={}){
 if(typeof directory!=='string'||!directory.startsWith('/')||typeof run!=='function')throw Error('INVALID_NATIVE_QUALIFICATION_DIRECTORY');
 const dir=resolve(directory);
 const [requestBytes,publishedSource,source,toolchain]=await Promise.all([
  readFile(join(dir,'request.json'),'utf8'),readFile(join(dir,'published-exercise.lean.txt'),'utf8'),
  readFile(join(dir,'candidate.lean.txt'),'utf8'),readFile(join(dir,'lean-toolchain'),'utf8')]);
 const request=JSON.parse(requestBytes);
 const raw=[];
 const auditedRun=async(unit,code)=>{
  const began=performance.now();
  try{
   const result=await run(unit,code);
   raw.push({unit,source_sha256:sha(code),exit_code:result?.code??null,
    stdout_stderr:String(result?.output??''),
    ...(result?.produced_olean_sha256?{produced_olean_sha256:result.produced_olean_sha256}:{}),
    ...(result?.imported_olean_sha256?{imported_olean_sha256:result.imported_olean_sha256}:{}),
    wall_clock_ms:Math.round(performance.now()-began)});
   return result;
  }catch(e){raw.push({unit,source_sha256:sha(code),exit_code:null,
   error:artifactErrors.has(e?.message)?e.message:'NATIVE_EXECUTION_FAILED',wall_clock_ms:Math.round(performance.now()-began)});throw e;}
 };
 const {contract,receipt}=await runControlledArtinCase({publishedSource,request,source,mathlibGit,
  leanToolchainSha256:sha(toolchain),run:auditedRun});
 const contractBytes=JSON.stringify(contract),receiptBytes=JSON.stringify(receipt);
 const assessment=assessOmmClaim({request,contractBytes,expectedContractSha256:sha(contractBytes),
  receiptBytes,expectedReceiptSha256:sha(receiptBytes)});
 const report=formatOmmClaimReport(assessment,request,runUrl);
 const preview=buildOmmAppCheckPreview({request,contractBytes,expectedContractSha256:sha(contractBytes),
  receiptBytes,expectedReceiptSha256:sha(receiptBytes),expectedHeadSha:request.head_sha,runUrl});
 if(JSON.stringify(preview.assessment)!==JSON.stringify(assessment))throw Error('APP_PREVIEW_ASSESSMENT_DIVERGED');
 const expected=request.number===239?'NOT_ESTABLISHED_IN_THIS_REPLAY':'CONSUMER_ACCEPTED';
 const dirOut=join(dir,'output');await mkdir(dirOut,{recursive:false});
 const files={
  'claim-contract.json':contractBytes,'native-receipt.json':receiptBytes,
  'assessment.json':JSON.stringify(assessment),'native-trace.json':JSON.stringify(raw),
  'report.md':report,'app-check-preview.json':JSON.stringify(preview.payload)
 };
 await Promise.all(Object.entries(files).map(([name,contents])=>writeFile(join(dirOut,name),contents,{flag:'wx'})));
 const manifest={schema:'mathgraph.omm.artin-qualification-manifest.v1',
  repository:request.repository,number:request.number,source_head:request.head_sha,base_sha:request.base_sha,
  candidate_source_sha256:sha(source),published_source_sha256:sha(publishedSource),
  claim_contract_sha256:sha(contractBytes),native_receipt_sha256:sha(receiptBytes),
  artifact_sha256:Object.fromEntries(Object.entries(files).map(([name,contents])=>[name,sha(contents)])),
  run_url:runUrl,release:'QUALIFICATION_ONLY',evidence_warrant:'UNKNOWN'};
 await writeFile(join(dirOut,'manifest.json'),JSON.stringify(manifest,null,2)+'\n',{flag:'wx'});
 if(assessment.status!=='NATIVE_RECEIPT_BOUND'||assessment.original_target!==expected)
  throw Error('ARTIN_COHORT_NOT_QUALIFIED');
 return assessment;
}

// Each qualification has a fresh runner and compiles only its registered units.
export function createArtinNativeRunner(directory,runLake){
 const build=join(directory,'.lake/build/lib/lean');
 const olean=unit=>join(build,unit+'.olean');
 const compiled=new Map();
 const env={PATH:process.env.PATH,HOME:process.env.HOME,LEAN_NUM_THREADS:'1'};
 const lake=runLake??(args=>exec('lake',args,{cwd:directory,env,timeout:120000,maxBuffer:512000}));
 const statOlean=path=>lstat(path).catch(error=>{
  if(error.code==='ENOENT')return null;
  throw error;
 });
 // These fixed sources use legacy Lean files and produce no split olean parts.
 const verifyLegacyOlean=async path=>{
  if(await statOlean(path+'.server')||await statOlean(path+'.private'))
   throw Error('NATIVE_OLEAN_UNEXPECTED_PART');
 };
 const digestOlean=async path=>{
  await verifyLegacyOlean(path);
  const stat=await statOlean(path);
  if(!stat?.isFile())throw Error('NATIVE_OLEAN_MISSING');
  return sha(await readFile(path));
 };
 const verifyCompiled=async()=>{
  for(const [unit,digest] of compiled){
   if(await digestOlean(olean(unit))!==digest)throw Error('NATIVE_OLEAN_CHANGED');
  }
 };
 return async(unit,code)=>{
  if(!['Candidate','Consumer','Audit'].includes(unit))throw Error('UNREGISTERED_NATIVE_UNIT');
  const file=join(directory,unit+'.lean');
  const output=unit==='Audit'?null:olean(unit);
  const dependency={Consumer:'Candidate',Audit:'Consumer'}[unit];
  if(output){
   await mkdir(build,{recursive:true});
   if(await statOlean(output))throw Error('NATIVE_OLEAN_PREEXISTS');
   await verifyLegacyOlean(output);
  }
  await writeFile(file,code,{flag:'wx',mode:0o600});
  let imported;
  if(dependency){
   imported=compiled.get(dependency);
   if(!imported)throw Error('NATIVE_OLEAN_MISSING');
   await verifyCompiled();
   let deps;
   try{deps=await lake(['env','lean','--deps',file]);}
   catch{throw Error('NATIVE_OLEAN_IMPORT_MISMATCH');}
   const paths=deps.stdout.split(/\r?\n/).filter(Boolean).map(path=>resolve(directory,path));
   if(!paths.includes(olean(dependency)))throw Error('NATIVE_OLEAN_IMPORT_MISMATCH');
  }
  let result;
  try{
   const r=await lake(['env','lean',...(output?['-o',output]:[]),file]);
   result={code:0,output:r.stdout+r.stderr};
  }catch(e){
   if(!Number.isInteger(e.code))throw Error('NATIVE_ENVIRONMENT_UNAVAILABLE');
   result={code:e.code,output:String(e.stdout??'')+String(e.stderr??'')};
  }
  await verifyCompiled();
  if(imported)result.imported_olean_sha256=imported;
  if(result.code===0&&output){
   result.produced_olean_sha256=await digestOlean(output);
   compiled.set(unit,result.produced_olean_sha256);
  }
  return result;
 };
}

if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
 const dir=process.argv[2];
 try{
  if(!dir||process.argv.length!==3||process.env.GITHUB_REPOSITORY!=='metalogiclabs/mathgraph'||
    !/^[1-9][0-9]*$/.test(process.env.GITHUB_RUN_ID??''))throw Error('QUALIFICATION_CONTEXT_REQUIRED');
  const {stdout}=await exec('git',['-C',join(resolve(dir),'.lake/packages/mathlib'),'rev-parse','HEAD'],{timeout:10000});
  const assessment=await qualifyArtinDirectory({directory:dir,mathlibGit:stdout.trim(),
   runUrl:`https://github.com/metalogiclabs/mathgraph/actions/runs/${process.env.GITHUB_RUN_ID}`,
   run:createArtinNativeRunner(resolve(dir))});
  console.log(JSON.stringify({status:assessment.status,original_target:assessment.original_target,
    candidate_proof:assessment.candidate_proof,intent_fidelity:assessment.intent_fidelity}));
 }catch(e){console.error('OMM_ARTIN_QUALIFICATION_INCOMPLETE:'+String(e.message));process.exitCode=1;}
}
