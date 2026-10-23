import {collectAttempts,evaluateCollected} from "./github-attempt-collector-v1.mjs";
const series=await collectAttempts({repository:"metalogiclabs/mathgraph",runId:39878398161,
 expectedSha:"63018d9accc5c05c153cfe1ac22fca1c032cbbb5",token:process.env.GITHUB_TOKEN});
const result=evaluateCollected(series);
if(series.observations.length<3||series.observations.some(x=>x.conclusion!=="success")||result.state!=="OBSERVED")
 throw Error("HISTORICAL_ATTEMPTS_NOT_VERIFIED");
console.log("MATHGRAPH_COLLECTED_NATIVE_ATTEMPTS "+JSON.stringify({run_id:series.run_id,
 head_sha:series.head_sha,attempts:series.observations.map(x=>({attempt:x.attempt,
 job_ids:x.job_ids,conclusion:x.conclusion})),final:result.state,
 interim_pending_observed:false,permission:result.permission}));
