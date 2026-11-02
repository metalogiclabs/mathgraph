// Explicit single-call integration test. It is not a mathematics benchmark.
import {mkdtemp,rm,writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {openAIModel,runMention,reservationCents} from './mention-agent-v1.mjs';
export async function liveSmoke({env=process.env,fetcher=fetch}={}){
 if(typeof env.OPENAI_API_KEY!=='string'||!env.OPENAI_API_KEY.trim())throw Error('OPENAI_API_KEY_REQUIRED');
 const policy={repositories:['metalogiclabs/mathgraph'],userIds:[32909488],handle:'MathGraph',model:'gpt-6.1-sol',inputCentsPerMillion:500,outputCentsPerMillion:2000,maxOutputTokens:4096,maxInputBytes:8000,jobCapCents:25,totalCapCents:25};
 const sha=/^[a-f0-9]{40}$/.test(env.GITHUB_SHA??'')?env.GITHUB_SHA:'a'.repeat(40);
 const snapshot={repository:'metalogiclabs/mathgraph',number:232,sha,files:[{filename:'SYNTHETIC_CONTROL.lean',patch:'+-- Constructed integration control, not an upstream defect.\n+-- Advertised claim: every natural number is even.\n+theorem every_nat_even (h : ∀ n : Nat, n % 2 = 0) : ∀ n : Nat, n % 2 = 0 := h'}],runs:[],files_visibility:'COMPLETE',ci_visibility:'COMPLETE'};
 let apiCalls=0,usage=null,responseModel=null,httpStatus=null,providerCode=null;
 const model=openAIModel({apiKey:env.OPENAI_API_KEY,policy,fetcher:async(url,options)=>{
  apiCalls++;if(apiCalls>1)throw Error('PAID_RETRY_REFUSED');
  const response=await fetcher(url,options);httpStatus=response.status;
  if(response.ok){const data=await response.clone().json();responseModel=typeof data.model==='string'?data.model.slice(0,100):null;usage={input_tokens:data.usage?.input_tokens,output_tokens:data.usage?.output_tokens};}
  if(!response.ok){try{const error=await response.clone().json();if(/^[a-z_]{1,60}$/.test(error.error?.code??''))providerCode=error.error.code.toUpperCase();}catch{}}
  return response;
 }});
 const stateDir=await mkdtemp(join(tmpdir(),'mathgraph-live-'));let comment='';
 try{
  const result=await runMention({action:'created',repository:{full_name:snapshot.repository},sender:{id:32909488,type:'User'},issue:{number:232,pull_request:{}},comment:{id:1,body:'@MathGraph -check',user:{id:32909488,type:'User'}}},{policy,stateDir,github:{snapshot:async()=>snapshot,head:async()=>sha,publish:async body=>{comment=body;return 1;}},model});
  if(result.state!=='COMPLETED')throw Error(httpStatus&&httpStatus!==200?'MODEL_HTTP_'+httpStatus+(providerCode?'_'+providerCode:''):'LIVE_RESPONSE_NOT_VALIDATED');
  if(env.GITHUB_STEP_SUMMARY)await writeFile(env.GITHUB_STEP_SUMMARY,'## Live model connection test\n\nConstructed control; no upstream defect or native proof verdict is established.\n\n'+comment+'\n',{flag:'a'});
  return {status:'LIVE_MODEL_RESPONSE_VALIDATED',model:responseModel??policy.model,api_calls:apiCalls,usage,reserved_cents:reservationCents(policy),proof:'NOT_REPLAYED',meaning:'UNVERIFIED',scope:'SYNTHETIC_CONNECTIVITY_CONTROL_ONLY'};
 }finally{await rm(stateDir,{recursive:true,force:true});}
}
if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
 try{console.log(JSON.stringify(await liveSmoke()));}
 catch(e){console.error(/^[-A-Z0-9_]+$/.test(e.message)?e.message:'LIVE_MODEL_TEST_FAILED');process.exitCode=1;}
}
