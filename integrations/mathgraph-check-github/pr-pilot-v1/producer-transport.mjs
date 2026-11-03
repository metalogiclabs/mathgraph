// Trusted host-only adapter. No source-repository code executes here.
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {admitProducer} from './producer-admission.mjs';
import {qualifyProducerSubject} from './expectations.mjs';
const need=(b,c)=>{if(!b)throw Error(c);};
const hash=b=>createHash('sha256').update(b).digest('hex');
const root='integrations/mathgraph-check-github/pr-pilot-v1/';
function python(name,input){const r=spawnSync('python3',[root+name+'.py'],{input,maxBuffer:45*1024*1024,timeout:15000});need(!r.error&&r.status===0,'PRODUCER_'+name.toUpperCase().replaceAll('-','_'));return JSON.parse(r.stdout);}
export function resolveProducer(envelope,request,context){
 need(envelope.consumer_controller===context.verifier_sha,'CONSUMER_CONTROLLER_CHANGED');
 const admitted=admitProducer(envelope,request),graph=python('producer-warrant',JSON.stringify({facts:admitted.facts}));
 need(graph.status==='WARRANTED_BOUNDED_NATIVE'&&graph.native_status==='WARRANTED_BOUNDED_NATIVE','PRODUCER_WARRANT_UNKNOWN');
 return {...admitted,graph,token:qualifyProducerSubject(admitted.subject)};
}
async function bytes(response,max=20*1024*1024){
 need(response.ok&&response.body,'PRODUCER_DOWNLOAD');let size=0;const chunks=[];
 for await(const c of response.body){size+=c.length;need(size<=max,'PRODUCER_DOWNLOAD_TOO_LARGE');chunks.push(c);}
 return Buffer.concat(chunks);
}
export async function downloadProducerArtifact(id,token,fetcher=fetch){
 need(Number.isSafeInteger(id)&&id>0,'PRODUCER_ARTIFACT_ID');
 const response=await fetcher(`https://api.github.com/repos/metalogiclabs/mathgraph/actions/artifacts/${id}/zip`,{redirect:'manual',headers:{Authorization:'Bearer '+token,Accept:'application/vnd.github+json'},signal:AbortSignal.timeout(20000)});
 if(response.status===200)return bytes(response);
 need(response.status===302,'PRODUCER_DOWNLOAD_REDIRECT');
 const url=new URL(response.headers.get('location'));
 need(url.protocol==='https:'&&!url.username&&!url.password&&(url.hostname.endsWith('.blob.core.windows.net')||url.hostname.endsWith('.actions.githubusercontent.com')),'PRODUCER_DOWNLOAD_HOST');
 // Signed storage requests must never receive the GitHub credential.
 return bytes(await fetcher(url.href,{redirect:'error',signal:AbortSignal.timeout(30000)}));
}
export async function captureProducer(request,context,sourceAPI,centralAPI,token){
 const repo='/repos/'+request.repository,pr=await sourceAPI(repo+'/pulls/'+request.number);
 const matches=[...new Set([...(pr.body??'').matchAll(/https:\/\/github.com\/metalogiclabs\/mathgraph\/actions\/runs\/([1-9][0-9]*)/g)].map(m=>Number(m[1])))];
 need(matches.length===1&&Number.isSafeInteger(matches[0]),'PRODUCER_LOCATOR_REQUIRED');
 const central='/repos/metalogiclabs/mathgraph',run=await centralAPI(central+'/actions/runs/'+matches[0]);
 const listed=await centralAPI(central+'/actions/runs/'+run.id+'/artifacts?per_page=100');
 need(listed.total_count===listed.artifacts?.length,'PRODUCER_ARTIFACT_LIST_INCOMPLETE');
 const artifacts=listed.artifacts.filter(a=>a.name==='pr-pilot-publication');need(artifacts.length===1,'PRODUCER_ARTIFACT_AMBIGUOUS');
 const artifact=artifacts[0],archive=await downloadProducerArtifact(artifact.id,token);
 need(artifact.digest==='sha256:'+hash(archive),'PRODUCER_DOWNLOAD_DIGEST');
 const raw=python('producer-artifact',archive),publication=JSON.parse(raw['publication.json']);
 const getText=async(api,path)=>{const f=await api(path);need(f.encoding==='base64'&&typeof f.content==='string','PRODUCER_CONTENT_ENCODING');return Buffer.from(f.content,'base64').toString('utf8');};
 const envelope={pr,run,artifact,raw,archive_sha256:hash(archive),consumer_controller:context.verifier_sha,
  workflow:await getText(centralAPI,central+'/contents/.github/workflows/check-pr-pilot.yml?ref='+run.head_sha),
  check:await sourceAPI(repo+'/check-runs/'+publication.check_id),
  commit:await sourceAPI(repo+'/git/commits/'+request.head_sha),
  comparison:await sourceAPI(repo+'/compare/'+request.base_sha+'...'+request.head_sha),
  source:await getText(sourceAPI,repo+'/contents/Scripts/Ledger.lean?ref='+request.head_sha),
  cli_source:await getText(sourceAPI,repo+'/contents/Scripts/Main/CheckScriptsLedger.lean?ref='+request.head_sha)};
 resolveProducer(envelope,request,context);return envelope;
}
