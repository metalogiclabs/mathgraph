// Qualification-only native wrapper for two exact first-party Artin PR heads.
// The credentialless job executes only the pre-registered source bytes.
import {createHash} from 'node:crypto';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
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
    stdout_stderr:String(result?.output??''),wall_clock_ms:Math.round(performance.now()-began)});
   return result;
  }catch(e){raw.push({unit,source_sha256:sha(code),exit_code:null,
   error:'NATIVE_EXECUTION_FAILED',wall_clock_ms:Math.round(performance.now()-began)});throw e;}
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

async function realNativeRun(directory,unit,code){
 if(!['Candidate','Consumer','Audit'].includes(unit))throw Error('UNREGISTERED_NATIVE_UNIT');
 const file=join(directory,unit+'.lean');
 await writeFile(file,code,{flag:'wx',mode:0o600});
 const withOlean=unit!=='Audit';
 if(withOlean)await mkdir(join(directory,'.lake/build/lib/lean'),{recursive:true});
 const args=['env','lean',...(withOlean?['-o',join(directory,'.lake/build/lib/lean',unit+'.olean')]:[]),file];
 const env={PATH:process.env.PATH,HOME:process.env.HOME,LEAN_NUM_THREADS:'1'};
 try{const r=await exec('lake',args,{cwd:directory,env,timeout:120000,maxBuffer:512000});return {code:0,output:r.stdout+r.stderr};}
 catch(e){if(Number.isInteger(e.code))return {code:e.code,output:String(e.stdout??'')+String(e.stderr??'')};throw Error('NATIVE_ENVIRONMENT_UNAVAILABLE');}
}

if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
 const dir=process.argv[2];
 try{
  if(!dir||process.argv.length!==3||process.env.GITHUB_REPOSITORY!=='metalogiclabs/mathgraph'||
    !/^[1-9][0-9]*$/.test(process.env.GITHUB_RUN_ID??''))throw Error('QUALIFICATION_CONTEXT_REQUIRED');
  const {stdout}=await exec('git',['-C',join(resolve(dir),'.lake/packages/mathlib'),'rev-parse','HEAD'],{timeout:10000});
  const assessment=await qualifyArtinDirectory({directory:dir,mathlibGit:stdout.trim(),
   runUrl:`https://github.com/metalogiclabs/mathgraph/actions/runs/${process.env.GITHUB_RUN_ID}`,
   run:(unit,code)=>realNativeRun(resolve(dir),unit,code)});
  console.log(JSON.stringify({status:assessment.status,original_target:assessment.original_target,
    candidate_proof:assessment.candidate_proof,intent_fidelity:assessment.intent_fidelity}));
 }catch(e){console.error('OMM_ARTIN_QUALIFICATION_INCOMPLETE:'+String(e.message));process.exitCode=1;}
}
