// Pure event gate to be called only after the existing HMAC signature verifier.
// Default OFF. No installation permission changes and no network calls.
export function routePKCYamlEvent({signatureVerified=false,event,action,payload,
 allowRepos=[],enabled=false}={}) {
 if(!enabled)return {route:"LEGACY_ONLY",reason:"OPT_IN_DISABLED"};
 if(!signatureVerified)return {route:"DENY",reason:"SIGNATURE_NOT_VERIFIED"};
 if(event!=="pull_request" ||
   !["opened","reopened","edited","synchronize","ready_for_review"].includes(action))
   return {route:"DENY",reason:"UNSUPPORTED_EVENT"};
 const repo=payload?.repository?.full_name;
 if(repo!=="metalogiclabs/mathgraph" || !allowRepos.includes(repo))
   return {route:"DENY",reason:"CARRIER_NOT_ALLOWLISTED"};
 if(!Number.isSafeInteger(payload?.installation?.id) ||
    !Number.isSafeInteger(payload?.pull_request?.number) ||
    !/^[a-f0-9]{40}$/.test(payload?.pull_request?.head?.sha||""))
   return {route:"DENY",reason:"EVENT_IDENTITY_INVALID"};
 return {route:"PKC_YAML_ADVISORY",reason:"SOURCE_SCOPED",
  repo,pr:payload.pull_request.number,head:payload.pull_request.head.sha,
  installationId:payload.installation.id};
}
