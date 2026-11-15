// First-party fixed-source Artin cohort for OMM qualification only. No GitHub
// webhook, model request or arbitrary Lean source may invoke this runner.
import {createHash} from 'node:crypto';
import {artinStrongSource,artinRepairSource,artinTarget,bindPublishedArtin} from '../mention-artin-control-v1.mjs';

const sha=s=>createHash('sha256').update(s).digest('hex');
const REPO='metalogiclabs/mathgraph';
const MATHLIB='8f9d9cff6bd728b17a24e163c9402775d9e6a365';
const TOOLCHAIN=sha('leanprover/lean4:v4.28.0\n');
const CANDIDATE='Artin_exercise_2_2_9';
const CONSUMER='MathGraphConsumer.original_target';
const PRS=Object.freeze({
  239:{head:'2f6aaba0d71f1c0b4c0db58618a8981ccd59dc17',base:'dfd87d1e921953badedcfae21ade76bb38f5c04a',source:artinStrongSource},
  240:{head:'06f09cd5aaa866365ceb6540cd06389bd37a727c',base:'2f6aaba0d71f1c0b4c0db58618a8981ccd59dc17',source:artinRepairSource}
});

const consumerSource='import Candidate\n\nopen Subgroup\n\n'+
 artinTarget.replace('theorem Artin_exercise_2_2_9','theorem '+CONSUMER)+
 ' := by\n  exact Artin_exercise_2_2_9 h\n';
const auditSource=`import Consumer\n#print axioms ${CANDIDATE}\n#print axioms ${CONSUMER}\n`;

function readAxioms(output,name){
 const lines=String(output??'').split(/\r?\n/).map(s=>s.trim());
 const matching=lines.filter(line=>line.startsWith(`'${name}' `));
 if(matching.length!==1)return null;
 if(matching[0]===`'${name}' does not depend on any axioms`)return [];
 const prefix=`'${name}' depends on axioms: [`;
 if(!matching[0].startsWith(prefix)||!matching[0].endsWith(']'))return null;
 const raw=matching[0].slice(prefix.length,-1);
 return raw?raw.split(',').map(x=>x.trim()):[];
}

const STANDARD=new Set(['propext','Classical.choice','Quot.sound']);
const clean=axioms=>Array.isArray(axioms)&&new Set(axioms).size===axioms.length&&axioms.every(x=>STANDARD.has(x));

/** The source and PR commits are predeclared first-party controls, never user input. */
export async function runControlledArtinCase({publishedSource,request,source,mathlibGit,leanToolchainSha256,run}={}){
 const profile=PRS[request?.number];
 if(request?.schema!=='mathgraph.omm.request.v1'||request?.repository!==REPO||request.command!=='check'||
   !profile||request.head_sha!==profile.head||request.base_sha!==profile.base||
   source!==profile.source||request.candidate_source_sha256!==sha(source)||
   mathlibGit!==MATHLIB||leanToolchainSha256!==TOOLCHAIN||typeof run!=='function')
  throw Error('UNREGISTERED_ARTIN_SOURCE_OR_ENVIRONMENT');
 const published=bindPublishedArtin(publishedSource);
 const contract={schema:'mathgraph.omm.claim-contract.v1',repository:REPO,number:request.number,
  head_sha:profile.head,base_sha:profile.base,reference_sha256:published.source_sha256,
  candidate_sha256:sha(source),consumer_sha256:sha(consumerSource),
  consumer_name:CONSUMER,candidate_name:CANDIDATE,mathlib_git:MATHLIB,
  lean_toolchain_sha256:TOOLCHAIN};
 const trace=[];let auditOutput='';let executionFailed=false;
 const execute=async(unit,content)=>{
  try{
   const r=await run(unit,content);
   if(!r||!Number.isInteger(r.code)||r.code<0||typeof r.output!=='string')throw Error('INVALID_NATIVE_RESULT');
   trace.push({unit,exit_code:r.code});return r;
  }catch{executionFailed=true;trace.push({unit,exit_code:null,execution_failed:true});return null;}
 };
 const candidate=await execute('Candidate',source);
 let consumer=null;
 if(candidate?.code===0)consumer=await execute('Consumer',consumerSource);
 if(consumer?.code===0){const audit=await execute('Audit',auditSource);auditOutput=audit?.output??'';}
 const candidateAxioms=readAxioms(auditOutput,CANDIDATE),axioms=readAxioms(auditOutput,CONSUMER);
 const accepted=trace.length===3&&trace.every(x=>x.exit_code===0)&&
  clean(candidateAxioms)&&clean(axioms);
 const native={execution_status:executionFailed?'RUN_FAILED':'EXECUTED',
  source_reference_sha256:contract.reference_sha256,candidate_sha256:contract.candidate_sha256,
  consumer_sha256:contract.consumer_sha256,consumer_name:CONSUMER,
  candidate_declaration_name:CANDIDATE,mathlib_git:MATHLIB,lean_toolchain_sha256:TOOLCHAIN,
  candidate_source_build:candidate?.code===0?'LEAN_ACCEPTED':'UNKNOWN',
  original_target_status:accepted?'NATIVE_CONSUMER_ACCEPTED':'UNKNOWN',
  candidate_axioms:clean(candidateAxioms)?candidateAxioms:null,
  axioms:clean(axioms)?axioms:null,trace};
 const receipt={schema:'mathgraph.omm.native-receipt.v1',repository:REPO,number:request.number,
  head_sha:profile.head,base_sha:profile.base,native};
 return {contract,receipt};
}
