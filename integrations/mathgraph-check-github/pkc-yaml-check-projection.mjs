// Read-only adapter for an independently authenticated PKC/L4YAML shadow report.
// Authentication, GitHub installation authorization, source-head refresh,
// and App-owned Check publication belong to the existing publisher.
// This function never promotes a carrier PR to safe-to-merge.
const SCHEMA="mathgraph.check.pkcyaml.shadow.v1";
const SHA=/^[a-f0-9]{40}$/;
const CLAIMS=["P1","P2","P3","Y1","Y2","Y3"];
export function projectPKCYamlCheck(report,{carrierRepo,carrierHead,authorized=false}={}) {
 const unknown=reason=>({name:"MathGraph Check / evidence scope",status:"completed",
   conclusion:"neutral",output:{title:"PKC_L4YAML_EVIDENCE_UNKNOWN",
   summary:"External research evidence UNKNOWN: "+reason+
   "\nNo carrier-code finding, NASA/JPL endorsement, or merge authority."}});
 if(!authorized || carrierRepo!=="metalogiclabs/mathgraph" ||
    !SHA.test(carrierHead||""))return unknown("installation/source authority missing");
 if(report?.schema!==SCHEMA || !SHA.test(report?.sourceHead||"") ||
    report?.authority!=="ARCHIVE_SHA256_VERIFIED_BY_WORKFLOW" ||
    report?.sourceHead==="0".repeat(40) ||
    report?.liveAppCheck!==false || report?.merge!=="UNKNOWN" ||
    report?.authorization!=="NONE" ||
    report?.restoration!=="UNKNOWN_NATIVE_REPLAY_REQUIRED" ||
    report?.transfer!=="UNKNOWN")return unknown("receipt scope or source mismatch");
 const a=report.advisory;
 if(a?.conclusion!=="neutral" || a?.merge!=="UNKNOWN" ||
    a?.authorization!=="NONE" ||
    !a.verdicts || Object.keys(a.verdicts).sort().join(",")!==CLAIMS.slice().sort().join(","))
   return unknown("unrecognized claim scope");
 const baseline={P1:"WARRANTED_BOUNDED",P2:"REJECTED_BOUNDED",P3:"UNKNOWN",
   Y1:"UNKNOWN",Y2:"REJECTED_BOUNDED",Y3:"UNKNOWN"};
 if(CLAIMS.some(k=>a.verdicts[k]!==baseline[k]) ||
    !["M1","M2","M3","M4"].every(k=>report.withdrawalTests?.[k]?.pass===true))
   return unknown("unsupported verdict or withdrawal");
 return {name:"MathGraph Check / evidence scope",status:"completed",conclusion:"neutral",
   output:{title:"PKC_L4YAML_HISTORICAL_RESEARCH_BOUNDED",
   summary:["**External research subjects:** pinned NASA/JPL PKC and L4YAML; NOT a defect in this carrier PR.",
     "Historical native evidence replay; four modeled selective withdrawals.",
     "Research receipt source revision: "+report.sourceHead+". Carrier PR revision: "+carrierHead+". These are distinct identities.",
     ...CLAIMS.map(k=>k+": "+baseline[k]),
     "Restoration native requalification: UNKNOWN. General transfer: UNKNOWN.",
     "Archive digest qualification is asserted by the report producer and must be independently checked by the publisher.",
     "**ADVISORY ONLY.** No NASA/JPL endorsement. No merge authorization."].join("\n")}};
}
