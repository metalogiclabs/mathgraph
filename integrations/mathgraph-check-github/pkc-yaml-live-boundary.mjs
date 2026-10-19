// Fail-closed bridge contract. No publication occurs here.
// A GitHub artifact metadata digest is not proof of its extracted report;
// the caller must supply SHA256-verified ZIP bytes and a validated report.
import {createHash} from "node:crypto";
import {gatePKCYamlPublication} from "./pkc-yaml-publisher-gate.mjs";
export const PIN=Object.freeze({
  repo:"metalogiclabs/mathgraph",artifact:12171240289,
  digest:"2bbd575f1d93759a734fa459f4f48be599411a44b91d0627b397d02d4f8b98f9",
  run:39218904172
});
export function checkArtifactBytes(zipBytes,metadata) {
 if(!(zipBytes instanceof Uint8Array))return false;
 const hash=createHash("sha256").update(zipBytes).digest("hex");
 return hash===PIN.digest && metadata?.id===PIN.artifact &&
   metadata?.digest==="sha256:"+PIN.digest && metadata?.expired===false &&
   metadata?.workflow_run?.id===PIN.run;
}
export function qualifyLiveCheck({zipBytes,artifactMetadata,parsedReport,
  repo,pr,head,liveHead,appId,installed,existingChecks}={}) {
 const authenticated=checkArtifactBytes(zipBytes,artifactMetadata);
 // A separately parsed report is not yet proven to be extracted from zipBytes.
 // Do not promote on a digest match alone; a trusted archive parser must bind
 // the report bytes to the checked ZIP before calling the publisher gate.
 return gatePKCYamlPublication({report:parsedReport,repo,pr,head,liveHead,
   appId,installed,existingChecks,artifactAuthenticated:false && authenticated});
}
