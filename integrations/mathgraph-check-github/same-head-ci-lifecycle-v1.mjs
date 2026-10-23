// Interpret two authenticated Github snapshots as observations of one logical
// check. The caller must supply snapshots obtained independently from GitHub.
import {replayLifecycle} from "./living-warrant-cycle-v1.mjs";
const SHA=/^[a-f0-9]{40}$/;
export function qualifySameHeadLifecycle({repository,sha,observations,otherChecks=[]}={}){
 const failure=(reason)=>({state:"UNKNOWN",reason,permission:"ADVISORY_ONLY"});
 if(typeof repository!=="string"||!SHA.test(sha??"")||
   !Array.isArray(observations)||observations.length<2||
   !Array.isArray(otherChecks))return failure("INVALID_OBSERVATION_SERIES");
 const receipts=[],events=[];
 const claims=[{id:"target",requires:["target"]},...otherChecks.map((c,i)=>({id:"other:"+i,requires:["other:"+i]}))];
 for(let i=0;i<otherChecks.length;i++){
   const o=otherChecks[i];
   if(o?.source_sha!==sha||!o.authenticated_receipt||o.conclusion!=="success")return failure("UNVERIFIED_INDEPENDENT_EVIDENCE");
   receipts.push(o.authenticated_receipt);
   events.push({type:"OBSERVE",id:"other:"+i,generation:1,source_sha:sha,receipt_id:o.authenticated_receipt,conclusion:"success"});
 }
 for(let i=0;i<observations.length;i++){
   const o=observations[i];
   if(o?.source_sha!==sha||typeof o.authenticated_receipt!=="string"||
      !Number.isSafeInteger(o.run_attempt)||o.run_attempt<1||
      !Number.isSafeInteger(o.check_run_id)||o.check_run_id<1||
      !["success","failure","pending"].includes(o.conclusion))
      return failure("INVALID_AUTHENTICATED_RUN");
   if(i>0 && (o.run_attempt<=observations[i-1].run_attempt||
      o.check_run_id===observations[i-1].check_run_id&&o.conclusion!==observations[i-1].conclusion&&
      o.run_attempt===observations[i-1].run_attempt))
      return failure("NONMONOTONIC_REPLAY");
   receipts.push(o.authenticated_receipt);
   // Pending newer attempt explicitly withdraws the old success.
   events.push({type:"OBSERVE",id:"target",generation:i+1,source_sha:sha,
     receipt_id:o.authenticated_receipt,conclusion:o.conclusion});
 }
 const result=replayLifecycle({source:{repository,sha},claims,events,authenticatedReceipts:receipts});
 return {...result,scope:"REPORTED_GITHUB_CHECK_RUN_RESULTS_ONLY",native_execution:"NOT_PERFORMED_BY_ADAPTER"};
}
