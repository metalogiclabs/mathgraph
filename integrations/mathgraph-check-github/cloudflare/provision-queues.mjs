// Cloudflare Queues account-scoped, idempotent provisioner.
// Called only by the explicitly approved Cloudflare deploy job.
// Never prints Cloudflare API credentials or response bodies.
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const QUEUE_NAMES = Object.freeze([
  "mathgraph-check-pr-events-v0",
  "mathgraph-check-pr-events-dlq-v0"
]);
function requireOK(ok,code){if(!ok)throw new Error(code);}
export async function ensureQueues({accountId,apiToken,fetcher=fetch}={}){
  requireOK(/^[0-9a-f]{32}$/i.test(String(accountId||"")) &&
    typeof apiToken==="string" && apiToken.length>=10,
    "CLOUDFLARE_DEPLOY_CREDENTIALS_MISSING");
  const path="/client/v4/accounts/"+accountId+"/queues";
  async function call(method,suffix="",payload){
    const headers={Authorization:"Bearer "+apiToken,Accept:"application/json"};
    if(payload!==undefined)headers["Content-Type"]="application/json";
    const resp=await fetcher("https://api.cloudflare.com"+path+suffix,{
      method,headers,body:payload===undefined?undefined:JSON.stringify(payload),
      signal:AbortSignal.timeout(15000)
    });
    if(!resp.ok)throw new Error("CLOUDFLARE_QUEUES_HTTP_"+resp.status);
    const data=await resp.json();
    requireOK(data?.success===true,"CLOUDFLARE_QUEUES_API_UNCONFIRMED");
    return data;
  }
  async function list(){
    const response=await call("GET","?page=1&per_page=100");
    requireOK(Array.isArray(response.result) &&
      (!response.result_info || response.result_info.total_pages<=1),
      "CLOUDFLARE_QUEUES_DISCOVERY_INCOMPLETE");
    return new Set(response.result.map(x=>x.queue_name));
  }
  const existing=await list(),created=[];
  for(const name of QUEUE_NAMES){
    if(existing.has(name))continue;
    const res=await call("POST","",{queue_name:name});
    requireOK(res.result?.queue_name===name,
      "CLOUDFLARE_QUEUE_CREATION_UNCONFIRMED");
    created.push(name);
  }
  const after=await list();
  requireOK(QUEUE_NAMES.every(n=>after.has(n)),
    "CLOUDFLARE_QUEUES_NOT_PRESENT_AFTER_PROVISION");
  return {scope:"mathgraph-check-queues-v0",created,
    alreadyPresent:QUEUE_NAMES.filter(x=>!created.includes(x))};
}
if(process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  try{
    const out=await ensureQueues({
      accountId:process.env.CLOUDFLARE_ACCOUNT_ID,
      apiToken:process.env.CLOUDFLARE_API_TOKEN
    });
    console.log("MATHGRAPH_CLOUDFLARE_QUEUES "+JSON.stringify(out));
  }catch(e){
    console.error("MATHGRAPH_CLOUDFLARE_QUEUES_BLOCKED "+
      (/^[A-Z_0-9]+$/.test(e.message)?e.message:"PROVISION_FAILED"));
    process.exitCode=1;
  }
}
