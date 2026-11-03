import {readFile,writeFile,mkdir,readdir} from 'node:fs/promises';import {createHash} from 'node:crypto';import assert from 'node:assert/strict';
import {executionContext} from '../../integrations/mathgraph-check-github/pr-pilot-v1/context.mjs';
import {githubClient} from '../../integrations/mathgraph-check-github/pr-pilot-v1/github.mjs';
import {admitRequest} from '../../integrations/mathgraph-check-github/pr-pilot-v1/policy.mjs';
import {captureProducer,resolveProducer} from '../../integrations/mathgraph-check-github/pr-pilot-v1/producer-transport.mjs';
import {admitExpectations,expectationSubject} from '../../integrations/mathgraph-check-github/pr-pilot-v1/expectations.mjs';
import {admitLeanPatch} from '../../integrations/mathgraph-check-github/lean-investigator-v1/contracts.mjs';
const [phase,dir,number]=process.argv.slice(2),context=executionContext(),repository='metalogiclabs/L4YAML',hash=b=>createHash('sha256').update(b).digest('hex');
const save=async(n,v)=>writeFile(dir+'/'+n+'.json',JSON.stringify(v,null,2)+'\n'),get=async n=>JSON.parse(await readFile(dir+'/'+n+'.json'));
async function seal(){const hashes={};for(const n of(await readdir(dir)).filter(n=>n.endsWith('.json')&&n!=='manifest.json').sort())hashes[n]=hash(await readFile(dir+'/'+n));await save('manifest',{context,hashes});}
if(phase==='prepare'){
 await mkdir(dir,{recursive:true});const api=githubClient(process.env.GITHUB_TOKEN,{repository}),pr=await api('/repos/'+repository+'/pulls/'+number),files=await api('/repos/'+repository+'/pulls/'+number+'/files?per_page=100');
 const request=admitRequest({repository,pr,files,filesComplete:files.length===pr.changed_files,permission:'admin',comment:{id:context.run_id,body:'@MathGraph -check',user:{id:32909488,login:'heathsanchez',type:'User'}}});
 assert.equal(request.profile.expectation_candidate,true);const envelope=await captureProducer(request,context,api,api,process.env.GITHUB_TOKEN),admitted=resolveProducer(envelope,request,context);
 request.profile.expectation_profile='ledger-shell-v2';request.qualification_only=true;
 await save('request',request);await save('producer-envelope',envelope);await save('producer-warrant',admitted.graph);await save('publication',{context,state:'QUALIFICATION_ONLY',run_url:'https://github.com/metalogiclabs/mathgraph/actions/runs/'+context.run_id});await seal();
}else if(phase==='patch'){
 const request=await get('request'),snapshot=await get('snapshot'),envelope=await get('producer-envelope'),token=resolveProducer(envelope,request,context).token;
 assert.equal(request.number,27);assert.equal(admitExpectations(expectationSubject(snapshot),await get('plan'),await get('expectation-reference'),context,token,'ledger-shell-v2').repair_eligible,true);
 const patch=JSON.parse(await readFile(new URL('../check-leading-redirection-v1/patch.json',import.meta.url))),content=admitLeanPatch(patch,snapshot.source);
 await save('qualification-check',await get('assessment'));request.command='fix';snapshot.command='fix';await save('request',request);await save('snapshot',snapshot);await save('patch',{...patch,path:snapshot.path,content,original_sha256:hash(snapshot.source),patched_sha256:hash(content)});await save('repair-state',{state:'PATCH_PROPOSED',model_calls:0,origin:'FROZEN_RESEARCH_CANDIDATE_NOT_MODEL_OUTPUT'});await seal();
}else throw Error('UNKNOWN_PHASE');
