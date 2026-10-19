// Strict read-only report generator. The caller must independently SHA256-check
// the GitHub artifact ZIP before extracting cross-domain.json and yaml.json.
// Never publishes a GitHub Check or treats a modeled withdrawal as native replay.
import {readFileSync,writeFileSync} from "node:fs";
import {advisory} from "./check_advisory.mjs";
const [crossPath,yamlPath,outPath]=process.argv.slice(2);
if(!crossPath||!yamlPath||!outPath)throw Error("USAGE: cross-domain.json yaml.json report.json");
const cross=JSON.parse(readFileSync(crossPath,"utf8"));
const yaml=JSON.parse(readFileSync(yamlPath,"utf8"));
function check(v,why){if(!v)throw Error("RECEIPT_NOT_ADMITTED:"+why)}
check(cross.protocol_commit==="9c8b427c679398fd80ea56d9a91a1627b2e96b6d","protocol");
check(cross.M5==="UNKNOWN: requires native verifier re-execution after source revision restoration","M5");
check(cross.cross_domain_semantic_acquisition==="UNKNOWN","transfer");
check(cross.new_native_sources_executed===false,"native execution");
check(yaml.protocol==="L4YAML_STYLE_REPAIR_VERIFY_V2" && yaml.expectation==="original-red","yaml scope");
check(yaml.upstream==="nasa-jpl/L4YAML@fdef03caf19e8862792034793da11020b39d6110","yaml pin");
check(yaml.native_correctness_checks?.distinct_dump_option_values===false && yaml.independent_checks?.qNone_is_null_in_both===false,"yaml native mismatch");
const expectations={M1:["P1","P2"],M2:["P2","P3"],M3:["Y2"],M4:["Y1","Y2"]};
for(const [id,claims] of Object.entries(expectations)){
 const t=cross.tests?.[id];check(t?.pass===true && JSON.stringify(t.changed)===JSON.stringify(claims),"withdrawal "+id);
}
const baseline={P1:"WARRANTED_BOUNDED",P2:"REJECTED_BOUNDED",P3:"UNKNOWN",Y1:"UNKNOWN",Y2:"REJECTED_BOUNDED",Y3:"UNKNOWN"};
check(JSON.stringify(cross.baseline)===JSON.stringify(baseline),"baseline");
const head=process.env.GITHUB_SHA;
check(typeof head==="string" && /^[a-f0-9]{40}$/.test(head),"source SHA");
const view=advisory(cross,{sourceHead:head,expectedHead:head});
check(view.title==="CROSS_DOMAIN_ADVISORY_BOUNDED" && view.conclusion==="neutral","advisory");
const report={schema:"mathgraph.check.pkcyaml.shadow.v1",authority:"ARCHIVE_SHA256_VERIFIED_BY_WORKFLOW",
 subject:"PKC/L4YAML pinned historical research; NOT carrier PR source",sourceHead:head,
 advisory:view,withdrawalTests:cross.tests,restoration:"UNKNOWN_NATIVE_REPLAY_REQUIRED",
 transfer:"UNKNOWN",merge:"UNKNOWN",authorization:"NONE",liveAppCheck:false};
writeFileSync(outPath,JSON.stringify(report,null,2)+"\n");
console.log("SHADOW_REPORT_PASS: bounded claims only; M5 and transfer UNKNOWN");
