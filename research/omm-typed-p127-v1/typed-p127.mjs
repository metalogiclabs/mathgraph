// Research-only replay of a single publicly pinned Mathathon Lean statement.
// This is not a proof or a human-intent verifier. Source and native output must
// come from a credentialless first-party runner; the operator-attested scope
// labels below remain a separate, non-authoritative judgment.
import {createHash} from 'node:crypto';
import {readFile,writeFile} from 'node:fs/promises';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {assessDeclaredScope} from '../../integrations/mathgraph-check-github/omm-v1/scope-contract-research.mjs';

const exec=promisify(execFile);
const sha=s=>createHash('sha256').update(s).digest('hex');
const SOURCE_SHA='86ab2826d38ff5595c66405125c26a63a16e254d56a10f9b660d7633a1ef4e5f';
const MATHLIB='56a005855ea17e0b0958f73ec801ae140b0a1679';
const TOOLCHAIN='7289597a44543246c9227b8cae501767e095ce17f6d448b95fc4a8dc97268f6d';
const DECL='Mathathon.P127.rogers_ramanujan';
const IDENTITY=Object.freeze({repository:'SAIRcompetition/mathathon-judge',
  head_sha:'4d6098d263275ff1cb0308908a693e776c116f53',
  source_path:'problems_ai/lean/MathathonProblems/P127_RogersRamanujan.lean',
  source_sha256:SOURCE_SHA});
const TAGS=['MATHGRAPH_P127_TYPE_BEGIN','MATHGRAPH_P127_TYPE_END',
  'MATHGRAPH_P127_AXIOMS_BEGIN','MATHGRAPH_P127_AXIOMS_END'];

function unknown(reason){return {schema:'mathgraph.omm.p127-typed-scope-research.v1',
  status:'UNKNOWN',reason,intent_fidelity:'UNKNOWN',proof_status:'UNKNOWN',
  evidence_warrant:'UNKNOWN'};}

function cut(output,open,close){
  if(output.split(open).length!==2||output.split(close).length!==2)return null;
  const start=output.indexOf(open)+open.length,end=output.indexOf(close);
  if(end<=start)return null;
  return output.slice(start,end).trim();
}

/** Concatenate the immutable public source with native Lean printing commands. */
export function prepareP127Audit(sourceBytes){
  if(typeof sourceBytes!=='string'||sha(sourceBytes)!==SOURCE_SHA)
    throw Error('SOURCE_BYTES_CHANGED');
  return sourceBytes+'\n'+
    '#eval IO.println "'+TAGS[0]+'"\n'+
    '#print '+DECL+'\n'+
    '#eval IO.println "'+TAGS[1]+'"\n'+
    '#eval IO.println "'+TAGS[2]+'"\n'+
    '#print axioms '+DECL+'\n'+
    '#eval IO.println "'+TAGS[3]+'"\n';
}

function declaredScope(ids,typeHash){
  const contract={schema:'mathgraph.omm.declared-scope-contract.research.v1',
    ...IDENTITY,requirement_ids:ids};
  const annotation={schema:'mathgraph.omm.type-scope-annotation.research.v1',
    ...IDENTITY,declaration:DECL,type_sha256:typeHash,attested_scope_ids:['count-equality']};
  const contractBytes=JSON.stringify(contract),typeAnnotationBytes=JSON.stringify(annotation);
  return assessDeclaredScope({currentSource:IDENTITY,contractBytes,
    expectedContractSha256:sha(contractBytes),typeAnnotationBytes,
    expectedTypeAnnotationSha256:sha(typeAnnotationBytes)});
}

/**
 * Native print *text* is evidence only when the runner proves provenance;
 * the source contract and requirement mapping are curator-attested. The
 * on-disk Lean theorem ends in sorry, so even successful elaboration is not
 * proof acceptance or evidence of a mathematical discovery.
 */
export function assessP127Native({sourceBytes,nativeOutput,exitCode,mathlibGit,
  toolchainDigest}={}){
  if(typeof sourceBytes!=='string'||sha(sourceBytes)!==SOURCE_SHA)
    return unknown('OFFICIAL_SOURCE_NOT_PINNED');
  if(exitCode!==0||mathlibGit!==MATHLIB||toolchainDigest!==TOOLCHAIN)
    return unknown('NATIVE_BUILD_OR_ENVIRONMENT_UNQUALIFIED');
  if(typeof nativeOutput!=='string'||nativeOutput.length>2_000_000)
    return unknown('NATIVE_PRINT_MISSING');
  const typeText=cut(nativeOutput,TAGS[0],TAGS[1]);
  const axiomText=cut(nativeOutput,TAGS[2],TAGS[3]);
  if(!typeText||!axiomText||nativeOutput.indexOf(TAGS[2])<nativeOutput.indexOf(TAGS[1])||
    !typeText.includes('theorem '+DECL)||!typeText.includes('.card')||
    !typeText.includes('=')||!axiomText.includes(DECL))
    return unknown('ELABORATED_TYPE_OR_AXIOM_PRINT_NOT_OBSERVED');

  const typeHash=sha(typeText);
  const original=declaredScope(['count-equality','natural-bijection'],typeHash);
  const narrow=declaredScope(['count-equality'],typeHash);
  if(original.status!=='PINNED_SCOPE_ANNOTATIONS_COMPARED'||
     narrow.status!=='PINNED_SCOPE_ANNOTATIONS_COMPARED')
    return unknown('DECLARED_SCOPE_COMPARISON_FAILED');
  const hasSorry=/\bsorryAx\b/.test(axiomText);
  return {schema:'mathgraph.omm.p127-typed-scope-research.v1',
    status:'PINNED_NATIVE_TYPE_TEXT_OBSERVED',source_sha256:SOURCE_SHA,
    type_sha256:typeHash,native_output_sha256:sha(nativeOutput),
    mathlib_git:MATHLIB,lean_toolchain_distribution_sha256:TOOLCHAIN,
    axiom_observation:hasSorry?'SORRY_AXIOM_PRESENT':'UNKNOWN',
    proof_status:hasSorry?'NOT_ESTABLISHED_SORRY':'UNKNOWN',
    original_scope:original,narrowed_scope:narrow,
    scope_annotation_authority:'CURATOR_LABELS_ONLY',
    intent_fidelity:'UNKNOWN',evidence_warrant:'UNKNOWN',
    reason:'ELABORATION_TEXT_NOT_MATHEMATICAL_OR_HUMAN_INTENT_WARRANT'};
}

// First-party credentialless workflow interface: preflight and replay on a
// fresh runner. Outputs are retained even when the native process rejects.
async function main(){
  const action=process.argv[2],directory=process.argv[3];
  if(!['prepare','replay'].includes(action)||!directory?.startsWith('/')||
    process.argv.length!==4)throw Error('FIXED_RESEARCH_CLI_ARGUMENTS_REQUIRED');
  const root=resolve(directory),src=await readFile(join(root,'P127.source.lean'),'utf8');
  if(action==='prepare'){
    await writeFile(join(root,'P127.Audit.lean'),prepareP127Audit(src),{flag:'wx'});
    return;
  }
  if(await readFile(join(root,'P127.Audit.lean'),'utf8')!==prepareP127Audit(src))
    throw Error('AUDIT_SOURCE_CHANGED');
  const mathlibGit=(await exec('git',['-C',join(root,'.lake/packages/mathlib'),
    'rev-parse','HEAD'],{timeout:10000})).stdout.trim();
  let exitCode=0,nativeOutput='';
  try{
    const run=await exec('lake',['env','lean','P127.Audit.lean'],{
      cwd:root,timeout:180000,maxBuffer:2_000_000,env:{...process.env,LEAN_NUM_THREADS:'1'}});
    nativeOutput=run.stdout+run.stderr;
  }catch(e){
    exitCode=Number.isInteger(e.code)?e.code:999;
    nativeOutput=String(e.stdout??'')+String(e.stderr??'')+'\n'+String(e.message);
  }
  await writeFile(join(root,'P127.native-output.txt'),nativeOutput,{flag:'wx'});
  const result=assessP127Native({sourceBytes:src,nativeOutput,exitCode,mathlibGit,
    toolchainDigest:TOOLCHAIN});
  await writeFile(join(root,'P127.assessment.json'),JSON.stringify(result,null,2)+'\n',
    {flag:'wx'});
  console.log(JSON.stringify({status:result.status,proof_status:result.proof_status,
    declared_gap:result.original_scope?.declared_scope??'UNKNOWN',
    source_sha256:result.source_sha256??null,type_sha256:result.type_sha256??null}));
  if(result.status!=='PINNED_NATIVE_TYPE_TEXT_OBSERVED')
    throw Error('NATIVE_TYPE_EVIDENCE_INCOMPLETE');
}

if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href)
  main().catch(e=>{console.error('P127_RESEARCH_UNKNOWN:'+e.message);process.exitCode=1;});
