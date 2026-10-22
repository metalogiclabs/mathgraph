// Read-only first-party live qualification entrypoint.
import {githubSnapshot} from "./authenticated-cycle-v1.mjs";
import {writeFile} from "node:fs/promises";
const repository=process.env.GITHUB_REPOSITORY;
const pr=Number(process.env.MATHGRAPH_PR_NUMBER);
const token=process.env.GITHUB_TOKEN;
try{
 const snapshot=await githubSnapshot({repository,pr,token});
 const report={schema:"mathgraph.check.live-readback.v1",
  source:snapshot.result.subject,status:snapshot.result.status,
  scope:"GITHUB_CHECK_RUN_OBSERVATION_ONLY",
  permission:"ADVISORY_ONLY",
  evidence:snapshot.input.evidence.map(e=>({id:e.id,name:e.name,conclusion:e.conclusion,check_run_id:e.check_run_id})),
  results:snapshot.result.results,resolve:snapshot.plans};
 await writeFile(process.env.MATHGRAPH_REPORT_PATH||"mathgraph-check-live.json",
  JSON.stringify(report,null,2)+"\n");
 console.log(JSON.stringify({status:report.status,source:report.source,
  observed_checks:report.evidence.length,scope:report.scope}));
}catch(error){
 console.error("READBACK_UNKNOWN:",error.message);
 process.exitCode=1;
}
