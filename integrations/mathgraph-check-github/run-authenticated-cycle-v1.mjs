// Read-only first-party live qualification entrypoint.
import {githubSnapshot} from "./authenticated-cycle-v1.mjs";
import {writeFile} from "node:fs/promises";
import {pathToFileURL} from 'node:url';

/** Do not confuse authenticated CI observations with requirement assurance. */
export function makeLiveReadbackReport(snapshot){
 if(!snapshot?.input||!Array.isArray(snapshot.input.evidence)||
   !snapshot.result?.subject||!Array.isArray(snapshot.result.results)||
   !['OBSERVED','BLOCKED','UNKNOWN'].includes(snapshot.result.status))
  throw Error('INVALID_AUTHENTICATED_SNAPSHOT');
 return {schema:'mathgraph.check.live-readback.v1',
  source:snapshot.result.subject,status:snapshot.result.status,
  scope:'GITHUB_CHECK_RUN_OBSERVATION_ONLY',permission:'ADVISORY_ONLY',
  evidence:snapshot.input.evidence.map(e=>({id:e.id,name:e.name,
   conclusion:e.conclusion,check_run_id:e.check_run_id})),
  results:snapshot.result.results,resolve:snapshot.plans,
  excluded_self_check_run_ids:snapshot.excluded_self_check_run_ids??[],
  requirement_assurance:{status:'UNKNOWN',
   reason:'INTENDED_REQUIREMENT_NOT_ADMITTED_IN_THIS_RUN',
   source_to_claim:'NOT_ESTABLISHED',
   observation_sufficiency:'NOT_ESTABLISHED',
   proof_replay:'NOT_PERFORMED',terminal_form:null,
   next_action:'QUALIFY_REQUIREMENT_AND_SEPARATING_PROBES'}};
}

if(import.meta.url===pathToFileURL(process.argv[1]??'').href){
 try{
  const snapshot=await githubSnapshot({repository:process.env.GITHUB_REPOSITORY,
   pr:Number(process.env.MATHGRAPH_PR_NUMBER),token:process.env.GITHUB_TOKEN,
   selfWorkflowRunId:process.env.GITHUB_RUN_ID?Number(process.env.GITHUB_RUN_ID):undefined});
  const report=makeLiveReadbackReport(snapshot);
  await writeFile(process.env.MATHGRAPH_REPORT_PATH||'mathgraph-check-live.json',
   JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({status:report.status,source:report.source,
   observed_checks:report.evidence.length,scope:report.scope,
   requirement_assurance:report.requirement_assurance.status}));
 }catch(error){
  console.error('READBACK_UNKNOWN:',error.message);
  process.exitCode=1;
 }
}
