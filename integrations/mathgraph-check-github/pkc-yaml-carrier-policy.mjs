// Explicit carrier admission. This is historical research, never a finding
// about the code of the pull request carrying the evidence.
export const CARRIER=Object.freeze({
 repository:"metalogiclabs/mathgraph",
 allowedPR:176,
 evidenceKind:"HISTORICAL_PKC_L4YAML_RESEARCH_ONLY"
});
export function carrierAdmitted(repo,pr,head,files) {
 if(repo!==CARRIER.repository || pr!==CARRIER.allowedPR ||
   !/^[a-f0-9]{40}$/.test(head||""))return false;
 if(!Array.isArray(files) || files.length===0)return false;
 // Only the explicitly reviewed integration and evidence files may change.
 return files.every(f=>typeof f?.filename==="string" &&
   (f.filename.startsWith("integrations/mathgraph-check-github/") ||
    f.filename===".github/workflows/mathgraph-check-combined-app-integration.yml"));
}
