// Call only after the existing webhook HMAC validation and delivery guards.
// Default OFF; no deployment or automatic installation.
import {routePKCYamlEvent} from "./pkc-yaml-event-gate.mjs";
import {consumePKCYaml} from "./pkc-yaml-live-consumer.mjs";
export async function handlePKCYamlSignedEvent({event,action,payload,
 signatureVerified=false,enabled=false,allowRepos=[],githubAPI,
 token,appId=5308912,installed=false}={}) {
 const route=routePKCYamlEvent({event,action,payload,signatureVerified,
  enabled,allowRepos});
 if(route.route!=="PKC_YAML_ADVISORY")
   return {state:route.route,reason:route.reason};
 if(!token || !installed)return {state:"UNKNOWN",reason:"INSTALLATION_AUTH_MISSING"};
 return consumePKCYaml({githubAPI,repo:route.repo,pr:route.pr,
   head:route.head,token,appId,installed,enabled:true});
}
