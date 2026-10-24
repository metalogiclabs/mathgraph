// Separate, default-off route. Never expands the Geth Worker SCOPE or gh() paths.
export const CARRIER=Object.freeze({
  repo:"metalogiclabs/mathgraph",
  pr:178,
  head:"05a6057e94d899ded94374db4a831963034aea93",
  schema:"mathgraph.pkcyaml-pr-delivery.v1"
});
const ACTIONS=new Set(["opened","reopened","edited","synchronize","ready_for_review"]);
const DELIVERY=/^[0-9a-f-]{16,80}$/i;

export function parseCarrierSignedEvent(payload,delivery,eventName,enabled=false){
  if(!enabled || eventName!=="pull_request" || !ACTIONS.has(payload?.action) ||
     !DELIVERY.test(String(delivery||"")) ||
     payload?.repository?.full_name!==CARRIER.repo ||
     payload?.pull_request?.number!==CARRIER.pr ||
     payload?.pull_request?.head?.sha!==CARRIER.head ||
     payload?.pull_request?.head?.repo?.full_name!==CARRIER.repo ||
     payload?.pull_request?.base?.repo?.full_name!==CARRIER.repo ||
     !Number.isSafeInteger(payload?.installation?.id) || payload.installation.id<1)
    return null;
  return {schema:CARRIER.schema,repository:CARRIER.repo,number:CARRIER.pr,
    sha:CARRIER.head,installationID:payload.installation.id,delivery,action:payload.action};
}

export function carrierQueueItem(item){
  return !!item && item.schema===CARRIER.schema &&
    item.repository===CARRIER.repo && item.number===CARRIER.pr &&
    item.sha===CARRIER.head && Number.isSafeInteger(item.installationID) &&
    item.installationID>0 && ACTIONS.has(item.action) &&
    DELIVERY.test(String(item.delivery||"")) &&
    Object.keys(item).sort().join(",")===
      "action,delivery,installationID,number,repository,schema,sha";
}

const ROOT="/repos/"+CARRIER.repo;
const PERMISSIONS=Object.freeze({checks:"write",pull_requests:"read",actions:"read"});
const ARTIFACT=ROOT+"/actions/artifacts/12171240289";
const CHECK_NAME=encodeURIComponent("MathGraph Check / evidence scope");
const PERMITTED_GET=new Set([
  "/app",ROOT+"/installation",ROOT+"/pulls/178",
  ROOT+"/pulls/178/files?per_page=100&page=1",ARTIFACT,
  ROOT+"/commits/"+CARRIER.head+
    "/check-runs?check_name="+CHECK_NAME+"&filter=all&per_page=100"
]);
function permitted(path,method){
  if(method==="GET")return PERMITTED_GET.has(path) ||
    /^\/repos\/metalogiclabs\/mathgraph\/check-runs\/[1-9][0-9]*$/.test(path);
  if(method==="GET_BYTES")return path===ARTIFACT+"/zip";
  if(method==="POST")return path===ROOT+"/check-runs" ||
    /^\/app\/installations\/[1-9][0-9]*\/access_tokens$/.test(path);
  if(method==="PATCH")return /^\/repos\/metalogiclabs\/mathgraph\/check-runs\/[1-9][0-9]*$/.test(path);
  return method==="DELETE" && path==="/installation/token";
}
function ensured(ok,code){if(!ok)throw Error(code);}
function permissionsOK(p){return p?.checks==="write" &&
  ["read","write"].includes(p?.pull_requests) &&
  ["read","write"].includes(p?.actions);}
const REDIRECT_HOSTS=new Set(["objects.githubusercontent.com","pipelines.actions.githubusercontent.com"]);
function safeArchiveRedirect(location){
  try{
    const url=new URL(location);
    return url.protocol==="https:" && !url.username && !url.password &&
      (REDIRECT_HOSTS.has(url.hostname) || url.hostname.endsWith(".blob.core.windows.net"));
  }catch{return false;}
}
async function boundedBytes(response){
  ensured(response.ok,"ARCHIVE_DOWNLOAD_HTTP_"+response.status);
  const declared=Number(response.headers.get("content-length"));
  ensured(!Number.isFinite(declared) || declared<=2_000_000,"ARCHIVE_TOO_LARGE");
  const reader=response.body?.getReader();
  ensured(!!reader,"ARCHIVE_STREAM_UNAVAILABLE");
  const parts=[];let total=0;
  try{
    while(true){const {value,done}=await reader.read();if(done)break;
      total+=value.length;
      ensured(total<=2_000_000,"ARCHIVE_TOO_LARGE");
      parts.push(value);
    }
  }finally{reader.releaseLock();}
  const bytes=new Uint8Array(total);let off=0;
  for(const p of parts){bytes.set(p,off);off+=p.length;}
  return bytes;
}

// Unlike legacy gh(), this API can access only the one carrier and one artifact.
// It never accepts a dynamic repository name or bearer token destination.
export async function carrierGitHub(path,token,method="GET",body,{fetcher=fetch}={}){
  ensured(permitted(path,method),"CARRIER_API_PATH_DENIED");
  ensured(typeof token==="string" && token.length>0,"CARRIER_TOKEN_MISSING");
  const response=await fetcher("https://api.github.com"+path,{
    method:method==="GET_BYTES"?"GET":method,
    headers:{Accept:"application/vnd.github+json",
      "X-GitHub-Api-Version":"2022-11-28",
      "User-Agent":"MathGraph-Check-Cloudflare-Pilot",
      Authorization:"Bearer "+token,
      ...(body===undefined?{}:{"Content-Type":"application/json"})},
    body:body===undefined?undefined:JSON.stringify(body),
    redirect:"manual",signal:AbortSignal.timeout(20000)
  });
  if(method==="GET_BYTES"){
    if(response.status===302 || response.status===303){
      const location=response.headers.get("location");
      ensured(safeArchiveRedirect(location),"ARCHIVE_REDIRECT_DENIED");
      // Crucially, never send the installation bearer token to the archive host.
      const archive=await fetcher(location,{method:"GET",redirect:"error",
        signal:AbortSignal.timeout(20000)});
      return boundedBytes(archive);
    }
    return boundedBytes(response);
  }
  if(!response.ok){const error=Error("GITHUB_HTTP_"+response.status);
    error.status=response.status;error.apiPath=path;throw error;}
  return response.status===204?{revoked:true}:response.json();
}

const UNKNOWN_OUTPUT=Object.freeze({
  title:"PKC_L4YAML_EVIDENCE_UNKNOWN",
  summary:"Previously displayed historical research evidence is no longer authenticated " +
    "at the frozen carrier. Any dependent advisory warrant requires independent " +
    "requalification. No defect is claimed in the carrier and no merge authority exists."
});

// Withdrawal is authorized by the current App installation + exact live PR head,
// not by the absent or tampered evidence. Never writes a new Check on failure.
async function withdrawCarrierCheck(item,token,api){
  const pr=await api(ROOT+"/pulls/178",token);
  ensured(pr?.state==="open" && pr.head?.sha===CARRIER.head &&
    pr.head?.repo?.full_name===CARRIER.repo &&
    pr.base?.repo?.full_name===CARRIER.repo,"STALE_WITHDRAWAL_SOURCE");
  const index=await api(ROOT+"/commits/"+CARRIER.head+
    "/check-runs?check_name="+CHECK_NAME+"&filter=all&per_page=100",token);
  ensured(Array.isArray(index?.check_runs) &&
    Number.isSafeInteger(index.total_count) &&
    index.total_count<=index.check_runs.length,"WITHDRAWAL_CHECK_CENSUS_INCOMPLETE");
  const external=CARRIER.repo+"#178@"+CARRIER.head;
  const owned=index.check_runs.filter(c=>c?.name==="MathGraph Check / evidence scope" &&
    c?.app?.id===5308912 && c?.external_id===external);
  ensured(owned.length<=1,"DUPLICATE_CARRIER_CHECK_AUTHORITY");
  if(owned.length===0)return null;
  const old=owned[0];
  ensured(Number.isSafeInteger(old.id) && old.id>0 &&
    old.head_sha===CARRIER.head && old.status==="completed" &&
    old.conclusion==="neutral","PREVIOUS_CARRIER_CHECK_INVALID");
  const same=old.output?.title===UNKNOWN_OUTPUT.title &&
    old.output?.summary===UNKNOWN_OUTPUT.summary;
  if(same)return {state:"ALREADY_UNKNOWN",checkId:old.id};
  const path=ROOT+"/check-runs/"+old.id;
  const details="https://github.com/"+CARRIER.repo+"/runs/"+old.id;
  const updated=await api(path,token,"PATCH",{
    status:"completed",conclusion:"neutral",output:UNKNOWN_OUTPUT,
    details_url:details
  });
  ensured(updated?.id===old.id && updated.app?.id===5308912 &&
    updated.head_sha===CARRIER.head && updated.conclusion==="neutral",
    "CARRIER_WITHDRAWAL_PATCH_UNCONFIRMED");
  const readback=await api(path,token);
  ensured(readback?.id===old.id && readback.app?.id===5308912 &&
    readback.head_sha===CARRIER.head && readback.external_id===external &&
    readback.status==="completed" && readback.conclusion==="neutral" &&
    readback.details_url===details &&
    readback.output?.title===UNKNOWN_OUTPUT.title &&
    readback.output?.summary===UNKNOWN_OUTPUT.summary,
    "CARRIER_WITHDRAWAL_READBACK_MISMATCH");
  return {state:"WITHDRAWN_TO_UNKNOWN",checkId:old.id};
}

function nativeReceiptUnavailable(error){
  return /^(ARTIFACT_|ARCHIVE_|ZIP_|PUBLICATION_DENIED:)/.test(error?.message||"") ||
    (error?.status===403 || error?.status===404) &&
      typeof error.apiPath==="string" && error.apiPath.startsWith(ARTIFACT);
}

export async function processCarrierQueue(item,env,{fetcher=fetch,makeJWT}={}){
  if(!carrierQueueItem(item))return {outcome:"IGNORED_INVALID_CARRIER"};
  if(env?.PKC_YAML_CARRIER_ENABLED!=="true")return {outcome:"CARRIER_DISABLED"};
  ensured(typeof makeJWT==="function" &&
    String(env.GITHUB_APP_ID)==="5308912" &&
    env.GITHUB_APP_CLIENT_ID==="Iv23lioiUs5KfHD7mkkw" &&
    !!env.GITHUB_APP_PRIVATE_KEY,"CARRIER_APP_CONFIGURATION_INVALID");
  const api=(path,token,method="GET",body)=>carrierGitHub(path,token,method,body,{fetcher});
  const jwt=makeJWT(env.GITHUB_APP_PRIVATE_KEY);
  const app=await api("/app",jwt);
  ensured(app?.id===5308912 && app?.owner?.login==="metalogiclabs" &&
    permissionsOK(app.permissions),"CARRIER_APP_IDENTITY_INVALID");
  const installation=await api(ROOT+"/installation",jwt);
  ensured(installation?.id===item.installationID && installation.app_id===5308912 &&
    installation.account?.login==="metalogiclabs" &&
    !installation.suspended_at && permissionsOK(installation.permissions),
    "CARRIER_INSTALLATION_INVALID");
  const minted=await api("/app/installations/"+installation.id+"/access_tokens",jwt,"POST",{
    repositories:["mathgraph"],permissions:PERMISSIONS
  });
  ensured(typeof minted?.token==="string" && minted.token.length>=10,
    "CARRIER_TOKEN_NOT_ISSUED");
  const token=minted.token;let result,failed,revokeOK=false;
  try{
    ensured(permissionsOK(minted.permissions),"CARRIER_TOKEN_PERMISSIONS_INVALID");
    const {consumePKCYaml}=await import("../pkc-yaml-live-consumer.mjs");
    result=await consumePKCYaml({githubAPI:api,repo:CARRIER.repo,pr:CARRIER.pr,
      head:CARRIER.head,token,appId:5308912,installed:true,enabled:true});
  }catch(e){
    if(nativeReceiptUnavailable(e)){
      try{result=await withdrawCarrierCheck(item,token,api);}
      catch(withdrawalError){failed=withdrawalError;}
    }
    if(!result && !failed)failed=e;
  }
  finally{
    try{revokeOK=(await api("/installation/token",token,"DELETE")).revoked===true;}
    catch{revokeOK=false;}
  }
  if(failed)throw failed;
  ensured(revokeOK,"CARRIER_TOKEN_REVOCATION_UNCONFIRMED");
  return {outcome:result.state,repository:CARRIER.repo,number:CARRIER.pr,
    sha:CARRIER.head,appID:5308912,tokenRevoked:true};
}
