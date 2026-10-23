// Live, explicitly first-party qualification only. Existing registered GitHub App.
// Security gate: exact PR and SHA pinned, no third-party destinations.
import {githubSnapshot} from "./authenticated-cycle-v1.mjs";
import {reconcileAdvisory} from "./app-token-reconcile-v1.mjs";
const repository="metalogiclabs/go-ethereum";
const pr=19;
const sha="a04aa77aaebd81d11274560e8d24d90c6f417589";
const appId=5308912;
const token=process.env.MATHGRAPH_APP_INSTALLATION_TOKEN;
async function main(){
 if(typeof token!=="string"||token.length<10)throw Error("INSTALLATION_TOKEN_MISSING");
 const observed=await githubSnapshot({repository,pr,token});
 if(observed.result.subject.head_sha!==sha)throw Error("TARGET_HEAD_CHANGED");
 const report={source:{repository,head_sha:sha},
  status:observed.result.status,permission:"ADVISORY_ONLY",
  scope:"GITHUB_CHECK_RUN_OBSERVATION_ONLY",
  evidence:observed.input.evidence,results:observed.result.results};
 const result=await reconcileAdvisory(report,{
  repository,pr,headSha:sha,appId,installationToken:token,
  allowedRepos:[repository],write:true});
 if(!["CREATED","UPDATED","UNCHANGED"].includes(result.mode))
  throw Error("PUBLICATION_NOT_QUALIFIED");
 // Independent second network readback, not merely the POST/PATCH response.
 const response=await fetch("https://api.github.com/repos/"+repository+"/check-runs/"+result.check_run_id,{
  headers:{Authorization:"Bearer "+token,Accept:"application/vnd.github+json",
   "X-GitHub-Api-Version":"2022-11-28"},signal:AbortSignal.timeout(15000)});
 if(!response.ok)throw Error("INDEPENDENT_READBACK_HTTP_"+response.status);
 const check=await response.json();
 const eid="mathgraph-check-advisory-v1:"+repository+"#"+pr+"@"+sha;
 if(check.app?.id!==appId||check.head_sha!==sha||check.external_id!==eid||
    check.conclusion!=="neutral"||check.name!=="MathGraph Check / advisory evidence")
  throw Error("INDEPENDENT_READBACK_IDENTITY_MISMATCH");
 console.log("MATHGRAPH_LIVE_APP_ADVISORY_VERIFIED "+JSON.stringify({
  outcome:result.mode,appId,checkRunId:check.id,repository,pr,sha,
  conclusion:check.conclusion,observedCheckCount:observed.input.evidence.length,
  assessment:report.status,scope:report.scope}));
}
await main().catch(e=>{console.error("MATHGRAPH_LIVE_APP_ADVISORY_UNKNOWN "+e.message);process.exitCode=1;});
