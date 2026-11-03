// Read-only qualification of the real hosted driver; no App credentials or publication.
import {readFile,writeFile,readdir,mkdir,copyFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {executionContext} from '../../integrations/mathgraph-check-github/pr-pilot-v1/context.mjs';
import {admitRequest} from '../../integrations/mathgraph-check-github/pr-pilot-v1/policy.mjs';
import {admitLeanPatch} from '../../integrations/mathgraph-check-github/lean-investigator-v1/contracts.mjs';
import {admitExpectations,expectationSubject} from '../../integrations/mathgraph-check-github/pr-pilot-v1/expectations.mjs';
const [phase,root,prNumber]=process.argv.slice(2),context=executionContext(),hash=s=>createHash('sha256').update(s).digest('hex');
const ensure=(b,r)=>{if(!b)throw Error(r);},load=async n=>JSON.parse(await readFile(`${root}/${n}.json`)),save=async(n,v)=>writeFile(`${root}/${n}.json`,JSON.stringify(v,null,2)+'\n');
async function seal(){const hashes={};for(const n of(await readdir(root)).filter(n=>n.endsWith('.json')&&n!=='manifest.json').sort())hashes[n]=hash(await readFile(root+'/'+n));await save('manifest',{context,hashes});}
if(phase==='prepare'){
 await mkdir(root,{recursive:true});
 const repository='metalogiclabs/L4YAML',number=Number(prNumber);
 const api=async path=>{const r=await fetch('https://api.github.com/repos/'+repository+path,{redirect:'error',headers:{Authorization:'Bearer '+process.env.GITHUB_TOKEN,Accept:'application/vnd.github+json','User-Agent':'MathGraph-Hosted-Expectation-Qualification'},signal:AbortSignal.timeout(30000)});ensure(r.ok,'SOURCE_METADATA_HTTP_'+r.status);return r.json();};
 const pr=await api('/pulls/'+number),comparison=await api('/compare/'+pr.base.sha+'...'+pr.head.sha);
 const request=admitRequest({repository,pr,files:comparison.files,filesComplete:comparison.files.length===pr.changed_files,permission:'admin',comment:{id:context.run_id,body:'@MathGraph -check',user:{id:32909488,login:'heathsanchez',type:'User'}}});
 ensure(request.profile.expectation_profile==='ledger-shell-v1','QUALIFIED_SUBJECT_REQUIRED');request.qualification_only=true;
 await save('request',request);await save('publication',{state:'QUALIFICATION_ONLY',context,run_url:'https://github.com/metalogiclabs/mathgraph/actions/runs/'+context.run_id});await seal();
}else if(phase==='stage-patch'){
 const request=await load('request'),snapshot=await load('snapshot'),plan=await load('plan'),state=await load('state'),check=await load('assessment');
 ensure(request.number===2&&state.model_calls===0&&check.head_complete===true&&check.expectations?.status==='ADMITTED','QUALIFIED_CHECK_REQUIRED');
 ensure(admitExpectations(expectationSubject(snapshot),plan,await load('expectation-reference'),context).repair_eligible,'EXPECTATION_NOT_ADMITTED');
 await save('qualification-check',check);await copyFile(root+'/MathGraph-Check.html',root+'/MathGraph-Check-check.html');
 const policy=JSON.parse(await readFile(new URL('./binding.json',import.meta.url))),content=admitLeanPatch(policy.patch,snapshot.source);
 request.command='fix';snapshot.command='fix';await save('request',request);await save('snapshot',snapshot);
 await save('patch',{...policy.patch,content,path:snapshot.path,original_sha256:hash(snapshot.source),patched_sha256:hash(content)});
 await save('repair-state',{state:'PATCH_PROPOSED',model_calls:0,origin:'FROZEN_QUALIFICATION_CANDIDATE_NOT_MODEL_REPAIR',patched_sha256:hash(content)});await seal();
}else throw Error('UNKNOWN_QUALIFICATION_PHASE');
