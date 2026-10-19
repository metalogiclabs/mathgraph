// Opt-in bridge for an existing App installation token. No new permissions.
// Caller must supply the signed-webhook-authorized repo, PR, head and token.
// This module never changes webhook configuration or deploys a Worker.
import {publishPKCYaml} from "./pkc-yaml-publish-adapter.mjs";
import {PIN} from "./pkc-yaml-live-boundary.mjs";
import {carrierAdmitted} from "./pkc-yaml-carrier-policy.mjs";
const ALLOW="metalogiclabs/mathgraph";
const ART="/repos/"+ALLOW+"/actions/artifacts/"+PIN.artifact;
const ZIP=ART+"/zip";
export async function consumePKCYaml({githubAPI,repo,pr,head,token,
 appId=5308912,installed=false,enabled=false,carrierFiles=[]}={}) {
 if(!enabled)return {state:"DISABLED"};
 if(repo!==ALLOW || !Number.isSafeInteger(pr) || pr<1 ||
    !/^[a-f0-9]{40}$/.test(head||"") || !token ||
    appId!==5308912 || !installed)throw Error("APP_CARRIER_NOT_AUTHORIZED");
 if(typeof githubAPI!=="function")throw Error("APP_API_REQUIRED");
 const fresh=await githubAPI("/repos/"+repo+"/pulls/"+pr,token);
 if(fresh?.head?.sha!==head)throw Error("STALE_CARRIER_HEAD");
 const fileData=await githubAPI("/repos/"+repo+"/pulls/"+pr+"/files?per_page=100&page=1",token);
 if(!Array.isArray(fileData) || fileData.length!==1 ||
    !carrierAdmitted(repo,pr,head,fileData))throw Error("DEDICATED_CARRIER_NOT_QUALIFIED");
 // The caller's GitHub client must return raw Uint8Array ZIP bytes for ZIP,
 // not JSON or a redirect body. Refuse unsupported transport.
 const metadata=await githubAPI(ART,token);
 if(metadata?.id!==PIN.artifact || metadata?.expired!==false ||
    metadata?.digest!=="sha256:"+PIN.digest ||
    metadata?.workflow_run?.id!==PIN.run)throw Error("ARTIFACT_AUTHORITY_MISMATCH");
 const zipBytes=await githubAPI(ZIP,token,"GET_BYTES");
 if(!(zipBytes instanceof Uint8Array))throw Error("ZIP_BYTE_TRANSPORT_UNAVAILABLE");
 const api=(path,method="GET",body)=>githubAPI(path,token,method,body);
 return publishPKCYaml({api,zipBytes,artifactMetadata:metadata,repo,pr,head,
   appId,installed});
}
