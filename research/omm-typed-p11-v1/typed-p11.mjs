// Fixed second-case research replay. The source proof uses sorry; declared
// deliverable IDs are curator labels, never authenticated human intent.
import {createHash} from 'node:crypto';
import {readFile,writeFile} from 'node:fs/promises';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {assessDeclaredScope} from '../../integrations/mathgraph-check-github/omm-v1/scope-contract-research.mjs';

const exec=promisify(execFile);
const sha=s=>createHash('sha256').update(s).digest('hex');
const SOURCE_SHA='763247683fd75b69611e9e81ddf4edae73619e36e517544158bf1b2b316e5758';
const ORIGINAL_SHA='77f73762bd92303e43a2af8a28c216c3bc245a6d4178a815641bd374ac2193d6';
const MATHLIB='56a005855ea17e0b0958f73ec801ae140b0a1679';
const TOOLCHAIN='7289597a44543246c9227b8cae501767e095ce17f6d448b95fc4a8dc97268f6d';
const DECL='CollatzPositiveDensity.exists_positive_density';
const HEAD='4d6098d263275ff1cb0308908a693e776c116f53';
const SOURCE=Object.freeze({repository:'SAIRcompetition/mathathon-judge',head_sha:HEAD,
  source_path:'problems_ai/lean/MathathonProblems/P11_CollatzPositiveDensity.lean',
  source_sha256:SOURCE_SHA});
const ORIGINAL=Object.freeze({repository:SOURCE.repository,head_sha:HEAD,
  path:'problems_original/011-mazurs-collatz-paper.md',sha256:ORIGINAL_SHA});
const LABELS=['MATHGRAPH_P11_TYPE_BEGIN','MATHGRAPH_P11_TYPE_END',
  'MATHGRAPH_P11_AXIOMS_BEGIN','MATHGRAPH_P11_AXIOMS_END'];
const OUTCOME='A human-readable paper which explains the ideas behind this new breakthrough. Preferably, a new way to phrase this argument which is more conceptually nice.';

function unknown(reason){return {schema:'mathgraph.omm.p11-typed-scope-research.v1',
  status:'UNKNOWN',reason,intent_fidelity:'UNKNOWN',proof_status:'UNKNOWN',
  evidence_warrant:'UNKNOWN'};}

export function prepareP11Audit(sourceBytes){
  if(typeof sourceBytes!=='string'||sha(sourceBytes)!==SOURCE_SHA)
    throw Error('SOURCE_BYTES_CHANGED');
  return sourceBytes+'\n'+
    '#eval IO.println "'+LABELS[0]+'"\n'+
    '#check '+DECL+'\n'+
    '#eval IO.println "'+LABELS[1]+'"\n'+
    '#eval IO.println "'+LABELS[2]+'"\n'+
    '#print axioms '+DECL+'\n'+
    '#eval IO.println "'+LABELS[3]+'"\n';
}

function segment(output,startMarker,endMarker){
  if(output.split(startMarker).length!==2||output.split(endMarker).length!==2)return null;
  const start=output.indexOf(startMarker)+startMarker.length;
  const end=output.indexOf(endMarker);
  return end<=start?null:output.slice(start,end).trim();
}

function declaredScope(requirementIds,attestedIds,typeHash){
  const contract={schema:'mathgraph.omm.declared-scope-contract.research.v1',
    ...SOURCE,requirement_ids:requirementIds};
  const type={schema:'mathgraph.omm.type-scope-annotation.research.v1',
    ...SOURCE,declaration:DECL,type_sha256:typeHash,attested_scope_ids:attestedIds};
  const contractBytes=JSON.stringify(contract),typeAnnotationBytes=JSON.stringify(type);
  return assessDeclaredScope({currentSource:SOURCE,contractBytes,
    expectedContractSha256:sha(contractBytes),typeAnnotationBytes,
    expectedTypeAnnotationSha256:sha(typeAnnotationBytes)});
}

export function assessP11Native({sourceBytes,originalRequirementBytes,nativeOutput,
  exitCode,mathlibGit,toolchainDigest}={}){
  if(typeof sourceBytes!=='string'||sha(sourceBytes)!==SOURCE_SHA)
    return unknown('OFFICIAL_LEAN_SOURCE_NOT_PINNED');
  if(typeof originalRequirementBytes!=='string'||sha(originalRequirementBytes)!==ORIGINAL_SHA)
    return unknown('ORIGINAL_PAPER_REQUEST_NOT_PINNED');
  if(originalRequirementBytes.split('## Desired outcome\n\n')[1]?.trim()!==OUTCOME)
    return unknown('PUBLISHED_OUTCOME_NOT_READABLE');
  if(exitCode!==0||mathlibGit!==MATHLIB||toolchainDigest!==TOOLCHAIN)
    return unknown('NATIVE_ENVIRONMENT_UNQUALIFIED');
  if(typeof nativeOutput!=='string'||nativeOutput.length>2_000_000)
    return unknown('NATIVE_PRINT_MISSING');
  const typeText=segment(nativeOutput,LABELS[0],LABELS[1]);
  const axioms=segment(nativeOutput,LABELS[2],LABELS[3]);
  if(!typeText||!axioms||nativeOutput.indexOf(LABELS[2])<nativeOutput.indexOf(LABELS[1])||
    !typeText.startsWith(DECL+' :')||typeText.includes(':=')||
    !typeText.includes('∃ c')||!typeText.includes('∃ X₀')||
    !typeText.includes('countBelow')||!typeText.includes('523')||
    !axioms.includes(DECL))
    return unknown('NATIVE_TYPE_OR_AXIOMS_NOT_OBSERVED');
  const typeHash=sha(typeText);
  const original=declaredScope(['human-readable-exposition'],[],typeHash);
  const narrower=declaredScope(['positive-density-existence'],['positive-density-existence'],typeHash);
  if(original.status!=='PINNED_SCOPE_ANNOTATIONS_COMPARED'||
    narrower.status!=='PINNED_SCOPE_ANNOTATIONS_COMPARED')
    return unknown('DECLARED_SCOPE_COMPARISON_FAILED');
  const hasSorry=/\bsorryAx\b/.test(axioms);
  return {schema:'mathgraph.omm.p11-typed-scope-research.v1',
    status:'PINNED_NATIVE_TYPE_TEXT_OBSERVED',source_sha256:SOURCE_SHA,
    original_requirement_source:ORIGINAL,original_requested_outcome:OUTCOME,
    type_sha256:typeHash,native_output_sha256:sha(nativeOutput),
    original_scope:original,narrowed_scope:narrower,
    preference_ids:['conceptual-rephrasing'],preference_warrant:'UNKNOWN',
    scope_annotation_authority:'CURATOR_LABELS_ONLY',
    axiom_observation:hasSorry?'SORRY_AXIOM_PRESENT':'UNKNOWN',
    proof_status:hasSorry?'NOT_ESTABLISHED_SORRY':'UNKNOWN',
    mathlib_git:MATHLIB,lean_toolchain_distribution_sha256:TOOLCHAIN,
    intent_fidelity:'UNKNOWN',evidence_warrant:'UNKNOWN',
    reason:'THEOREM_TYPE_CANNOT_ATTEST_EXPOSITION_OR_HUMAN_INTENT'};
}

async function main(){
  const action=process.argv[2],directory=process.argv[3];
  if(!['prepare','replay'].includes(action)||!directory?.startsWith('/')||
    process.argv.length!==4)throw Error('FIXED_RESEARCH_CLI_ARGUMENTS_REQUIRED');
  const root=resolve(directory);
  const sourceBytes=await readFile(join(root,'P11.source.lean'),'utf8');
  const originalRequirementBytes=await readFile(join(root,'P11.original.md'),'utf8');
  if(sha(originalRequirementBytes)!==ORIGINAL_SHA)throw Error('ORIGINAL_PAPER_REQUEST_NOT_PINNED');
  if(action==='prepare'){
    await writeFile(join(root,'P11.Audit.lean'),prepareP11Audit(sourceBytes),{flag:'wx'});
    return;
  }
  if(await readFile(join(root,'P11.Audit.lean'),'utf8')!==prepareP11Audit(sourceBytes))
    throw Error('P11_AUDIT_SOURCE_CHANGED');
  const mathlibGit=(await exec('git',['-C',join(root,'.lake/packages/mathlib'),
    'rev-parse','HEAD'],{timeout:10000})).stdout.trim();
  let exitCode=0,nativeOutput='';
  try{
    const run=await exec('lake',['env','lean','P11.Audit.lean'],{
      cwd:root,timeout:180000,maxBuffer:2_000_000,env:{...process.env,LEAN_NUM_THREADS:'1'}});
    nativeOutput=run.stdout+run.stderr;
  }catch(e){
    exitCode=Number.isInteger(e.code)?e.code:999;
    nativeOutput=String(e.stdout??'')+String(e.stderr??'')+'\n'+String(e.message);
  }
  await writeFile(join(root,'P11.native-output.txt'),nativeOutput,{flag:'wx'});
  const result=assessP11Native({sourceBytes,originalRequirementBytes,nativeOutput,
    exitCode,mathlibGit,toolchainDigest:TOOLCHAIN});
  await writeFile(join(root,'P11.assessment.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
  console.log(JSON.stringify({status:result.status,proof_status:result.proof_status,
    required_scope_gap:result.original_scope?.uncovered_requirement_ids??'UNKNOWN',
    preference_warrant:result.preference_warrant??'UNKNOWN',
    type_sha256:result.type_sha256??null}));
  if(result.status!=='PINNED_NATIVE_TYPE_TEXT_OBSERVED')
    throw Error('P11_NATIVE_TYPE_EVIDENCE_INCOMPLETE');
}

if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href)
  main().catch(e=>{console.error('P11_RESEARCH_UNKNOWN:'+e.message);process.exitCode=1;});
