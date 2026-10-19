// Runs in Actions against an exact authenticated ZIP downloaded by CI.
// No GitHub Checks API writes.
import {readFileSync} from "node:fs";
import {checkArtifactBytes,extractBoundReport,qualifyLiveCheck,PIN}
 from "./pkc-yaml-live-boundary.mjs";
const path=process.argv[2];
if(!path)throw Error("ZIP_PATH_REQUIRED");
const bytes=readFileSync(path);
const meta={id:PIN.artifact,digest:"sha256:"+PIN.digest,expired:false,
 workflow_run:{id:PIN.run}};
if(!checkArtifactBytes(bytes,meta))throw Error("PINNED_ZIP_DIGEST_MISMATCH");
const report=extractBoundReport(bytes);
if(report.schema!=="mathgraph.check.pkcyaml.shadow.v1" ||
 report.merge!=="UNKNOWN" || report.authorization!=="NONE" ||
 report.liveAppCheck!==false)throw Error("EXTRACTED_REPORT_SCOPE_MISMATCH");
const head=report.sourceHead;
const admitted=qualifyLiveCheck({zipBytes:bytes,artifactMetadata:meta,
 repo:PIN.repo,pr:171,head,liveHead:head,appId:5308912,
 installed:true,existingChecks:[]});
if(!admitted.admitted || admitted.check.conclusion!=="neutral" ||
 admitted.operation!=="CREATE_ONE")throw Error("ZIP_TO_GATE_NOT_ADMITTED");
const tampered=Buffer.from(bytes);tampered[0]^=1;
const denied=qualifyLiveCheck({zipBytes:tampered,artifactMetadata:meta,
 repo:PIN.repo,pr:171,head,liveHead:head,appId:5308912,
 installed:true,existingChecks:[]});
if(denied.admitted)throw Error("TAMPERED_ZIP_ADMITTED");
console.log("PINNED_ZIP_TO_GATE_PASS; tampering rejected; NO_CHECK_PUBLISHED");
