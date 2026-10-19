// External receipt admission for the owned PKC/L4YAML research carrier.
// GitHub metadata is authenticated by the caller's installation-scoped read.
// This does NOT download, decode or verify the native archive's inner JSON.
// Consequently its strongest conclusion is METADATA_VERIFIED, never a
// newly executed native verification or safe-to-merge decision.
import {advisory} from "./check_advisory.mjs";
export const AUTHORITY=Object.freeze({
 repo:"metalogiclabs/mathgraph",
 head:"1d2bfdbd02dd40b12aa8f23685e47f121a6b6ceb",
 run:39202345740,artifact:12164257659,
 name:"cross-domain-authenticated-v1",
 digest:"sha256:14b1233bb55a2f7e7e92b678a717dd5caa8fdf2de5435ff51fcabf5d9a2fbd26"
});
const fail=why=>({state:"UNKNOWN",check:{conclusion:"neutral",title:"CROSS_DOMAIN_EVIDENCE_UNKNOWN",
 summary:"Receipt not admitted: "+why+". No merge authorization."}});
export async function qualifiedAdvisory({githubRead,receipt,carrierHead,withdrawn=[]}={}) {
 if(typeof githubRead!=="function")return fail("read authority unavailable");
 if(carrierHead!==AUTHORITY.head)return fail("unrecognized carrier revision");
 try {
  const [run,artifact]=await Promise.all([
   githubRead("/repos/"+AUTHORITY.repo+"/actions/runs/"+AUTHORITY.run),
   githubRead("/repos/"+AUTHORITY.repo+"/actions/artifacts/"+AUTHORITY.artifact)
  ]);
  if(run?.id!==AUTHORITY.run || run?.head_sha!==AUTHORITY.head ||
     run?.status!=="completed" || run?.conclusion!=="success" ||
     run?.repository?.full_name!==AUTHORITY.repo)
    return fail("workflow identity or outcome mismatch");
  if(artifact?.id!==AUTHORITY.artifact || artifact?.name!==AUTHORITY.name ||
     artifact?.expired!==false || artifact?.digest!==AUTHORITY.digest ||
     artifact?.workflow_run?.id!==AUTHORITY.run ||
     artifact?.workflow_run?.head_sha!==AUTHORITY.head)
    return fail("archive authority mismatch");
  // Only a receipt already authenticated from archive bytes by a separate
  // trusted verifier can be used. No claim that the GitHub metadata proves
  // the content of a caller-supplied object.
  if(receipt?.archive_authenticated!==true)return fail("archive contents not authenticated");
  // No trusted byte-verifier is wired in V1; a caller boolean is not authority.
  return fail("archive-byte verification not wired; metadata only");
  const output=advisory(receipt,{sourceHead:carrierHead,expectedHead:AUTHORITY.head,withdrawn});
  if(output.title==="EVIDENCE_UNKNOWN")return fail("advisory scope rejected");
  return {state:"METADATA_VERIFIED_ARCHIVE_ASSERTED_BY_CALLER_NOT_INDEPENDENTLY_AUDITED",
   check:{...output,summary:output.summary+
    "\nMetadata pins checked; archive_authenticated is a caller assertion, not established by this adapter."}};
 }catch{return fail("GitHub read or validation failure")}
}
