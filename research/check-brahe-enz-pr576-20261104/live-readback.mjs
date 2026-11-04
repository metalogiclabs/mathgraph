// Read-only, exact-source qualification of GitHub Check observations.
// Success below is CI observation only. It does not establish ENZ semantics,
// acceptance by Brahe maintainers, or any permission to take an action.
import {writeFile} from "node:fs/promises";
import {pathToFileURL} from "node:url";
import {requalifyFreshGitHubCI} from "../../integrations/mathgraph-check-github/fresh-ci-requalification-v1.mjs";

export const PINNED_TARGETS=Object.freeze([
 {name:"MathGraph Check G1",repository:"metalogiclabs/mathgraph",pr:266,
  head_sha:"1a71cbb3c51c0991fb68dfcf4e2c5a558abce81f",
  base_sha:"74b8fb21cf47c7c98efd0d04edd30af9120126cb",
  requiredChecks:["contract","test","all-fixtures"]},
 {name:"Brahe ENZ PR 576",repository:"duncaneddy/brahe",pr:576,
  head_sha:"ebe0997414f677de2c3b188439ad3e3107ec9985",
  base_sha:"a134dd1dfb7450f3ed93df00e1680c67f54fd3be",
  requiredChecks:[
   "ci-success",
   "test-rust / test-rust (ubuntu-latest, stable)",
   "test-python / test-python (ubuntu-latest, 3.10, stable)",
  ]},
]);

const boundedUnknown=(target,reason,observed)=>({
 target:target.name,status:"UNKNOWN",reason,subject:observed?.subject??null,
 permission:"ADVISORY_ONLY",semantic_verification:"NOT_ESTABLISHED",
 checks:observed?.checks??[],
});

export function qualifyPinnedObservation(target,observed){
 if(observed?.subject?.repository!==target.repository||
    observed?.subject?.pr!==target.pr||
    observed?.subject?.head_sha!==target.head_sha||
    observed?.subject?.base_sha!==target.base_sha)
  return boundedUnknown(target,"EXACT_SOURCE_PIN_NOT_ESTABLISHED",observed);
 if(observed.permission!=="ADVISORY_ONLY"||
    observed.semantic_verification!=="NOT_ESTABLISHED")
  return boundedUnknown(target,"OVERSTATED_TRUST_BOUNDARY",observed);
 if(observed.status!=="OBSERVED"||
    !Array.isArray(observed.checks)||
    observed.checks.length!==target.requiredChecks.length||
    !target.requiredChecks.every((name,i)=>observed.checks[i].name===name&&
      observed.checks[i].status==="OBSERVED"&&
      Number.isSafeInteger(observed.checks[i].check_run_id)))
  return boundedUnknown(target,"INDEPENDENT_EXACT_HEAD_CHECKS_NOT_ALL_OBSERVED",observed);
 return {target:target.name,status:"OBSERVED",reason:"EXACT_HEAD_GITHUB_CI_ONLY",
  subject:observed.subject,
  permission:"ADVISORY_ONLY",semantic_verification:"NOT_ESTABLISHED",
  checks:observed.checks};
}

export async function runLiveReadback({token,requalify=requalifyFreshGitHubCI}={}){
 const observations=[];
 for(const target of PINNED_TARGETS){
  try{
   const observed=await requalify({repository:target.repository,pr:target.pr,
    token,requiredChecks:target.requiredChecks});
   observations.push(qualifyPinnedObservation(target,observed));
  }catch(error){
   observations.push(boundedUnknown(target,"GITHUB_READBACK_FAILED:"+String(error?.message??error)));
  }
 }
 const target=PINNED_TARGETS[1];
 const negativeControls=[];
 const controls=[
  {id:"missing-required-check",args:{
   repository:target.repository,pr:target.pr,token,
   requiredChecks:["mathgraph-does-not-exist-qualifier"]}},
  {id:"wrong-previous-subject",args:{
   repository:target.repository,pr:target.pr,token,
   requiredChecks:target.requiredChecks,
   previous:{result:{subject:{repository:"other/repo",pr:576,head_sha:target.head_sha}},
    independent_requalification:true}}},
  {id:"forged-old-success-and-flag",args:{
   repository:target.repository,pr:target.pr,token,
   requiredChecks:["mathgraph-does-not-exist-qualifier"],
   previous:{result:{subject:{repository:target.repository,pr:576,head_sha:"a".repeat(40)},
    results:[{id:"mathgraph-does-not-exist-qualifier",status:"OBSERVED"}]},
    independent_requalification:true}}},
 ];
 for(const control of controls){
  try{
   const observed=await requalify(control.args);
   negativeControls.push({id:control.id,
    outcome:observed.status==="UNKNOWN"&&observed.permission==="ADVISORY_ONLY"&&
     observed.semantic_verification==="NOT_ESTABLISHED"?"PASS":"FAIL",
    status:observed.status,reason:observed.reason});
  }catch(error){
   negativeControls.push({id:control.id,outcome:"UNKNOWN",
    reason:"GITHUB_READBACK_FAILED:"+String(error?.message??error)});
  }
 }
 return {schema:"mathgraph.check.brahe-readback-experiment.v1",
  trust_boundary:"CI_ONLY_NO_SEMANTIC_OR_ACTION_AUTHORITY",
  observations,negativeControls,
  experiment_status:observations.every(x=>x.status==="OBSERVED")&&
    negativeControls.every(x=>x.outcome==="PASS")?"PASS":"UNKNOWN"};
}

if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
 const result=await runLiveReadback({token:process.env.GITHUB_TOKEN});
 await writeFile(process.env.MATHGRAPH_READBACK_OUT??"mathgraph-check-brahe-live.json",
  JSON.stringify(result,null,2)+"\n");
 process.stdout.write(JSON.stringify(result,null,2)+"\n");
 if(result.experiment_status!=="PASS")process.exitCode=1;
}
