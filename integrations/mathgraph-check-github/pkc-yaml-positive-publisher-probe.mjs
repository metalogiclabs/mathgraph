// Positive end-to-end rehearsal with real SHA-pinned artifact bytes and
// an in-memory GitHub API simulator. NEVER sends a Check Runs API write.
import {readFileSync} from "node:fs";
import {publishPKCYaml} from "./pkc-yaml-publish-adapter.mjs";
import {PIN} from "./pkc-yaml-live-boundary.mjs";
import {CARRIER} from "./pkc-yaml-carrier-policy.mjs";
const path=process.argv[2];
if(!path)throw Error("PINNED_ZIP_REQUIRED");
const zipBytes=readFileSync(path),repo=CARRIER.repository,pr=CARRIER.allowedPR;
const head=CARRIER.allowedHead,appId=5308912;
const artifactMetadata={id:PIN.artifact,digest:"sha256:"+PIN.digest,
 expired:false,workflow_run:{id:PIN.run}};
let writes=0,stored=null;
const api=async(path,method="GET",body)=>{
 if(path===`/repos/${repo}/pulls/${pr}`)return {head:{sha:head}};
 if(path.startsWith(`/repos/${repo}/commits/${head}/check-runs?`))
  return {total_count:0,check_runs:[]};
 if(path===`/repos/${repo}/check-runs` && method==="POST"){
  writes++;stored={...body,id:999001,app:{id:appId}};
  return {id:999001};
 }
 if(path===`/repos/${repo}/check-runs/999001`)return stored;
 throw Error("UNEXPECTED_MOCK_API:"+method+" "+path);
};
const r=await publishPKCYaml({api,zipBytes,artifactMetadata,repo,pr,head,appId,installed:true});
if(r.state!=="APP_CHECK_VERIFIED" || r.conclusion!=="neutral" ||
 r.checkId!==999001 || writes!==1)throw Error("SIMULATED_PUBLISHER_NOT_QUALIFIED");
console.log("SIMULATED_APP_CHECK_PASS: exact head, neutral, one write/readback; NO_LIVE_CHECK");
