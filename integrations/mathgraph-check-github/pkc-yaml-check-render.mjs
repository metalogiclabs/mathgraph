// CI-only rendering: not a GitHub App publisher and never writes Check Runs.
import {readFileSync,writeFileSync} from "node:fs";
import {projectPKCYamlCheck} from "./pkc-yaml-check-projection.mjs";
const [source,output]=process.argv.slice(2);
if(!source||!output)throw Error("USAGE: report.json output.json");
const report=JSON.parse(readFileSync(source,"utf8"));
const head=process.env.SOURCE_HEAD;
const check=projectPKCYamlCheck(report,{
 carrierRepo:"metalogiclabs/mathgraph",carrierHead:head,authorized:true
});
if(check.output.title!=="PKC_L4YAML_HISTORICAL_RESEARCH_BOUNDED" ||
   check.conclusion!=="neutral")throw Error("APP_PROJECTION_NOT_ADMITTED");
writeFileSync(output,JSON.stringify({
 schema:"mathgraph.check.pkcyaml.app-payload-shadow.v1",
 sourceHead:head,check,publication:"NOT_PUBLISHED",appAuth:"NOT_TESTED",
 merge:"UNKNOWN",authorization:"NONE"},null,2)+"\n");
console.log("APP_PAYLOAD_SHADOW_PASS: no GitHub Checks API call");
