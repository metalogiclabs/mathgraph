// Historical research must be shown on a dedicated evidence-only PR.
// Integration PR #176 changes executable App code and is NOT that carrier.
// No carrier is admitted until its identity and immutable manifest are frozen.
export const CARRIER=Object.freeze({repository:"metalogiclabs/mathgraph",
 allowedPR:178,evidenceKind:"HISTORICAL_PKC_L4YAML_RESEARCH_ONLY"});
export function carrierAdmitted(repo,pr,head,files) {
 return CARRIER.allowedPR!==null && repo===CARRIER.repository &&
   pr===CARRIER.allowedPR && /^[a-f0-9]{40}$/.test(head||"") &&
   Array.isArray(files) && files.length>0 &&
   files.every(f=>typeof f?.filename==="string" &&
     f.filename.startsWith(".mathgraph-check/pkc-yaml/"));
}
