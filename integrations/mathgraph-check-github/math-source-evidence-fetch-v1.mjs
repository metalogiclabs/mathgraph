/**
 * Read-only, bounded transports for pinned mathematical evidence.
 * Authentication and authorisation of the GitHub App installation are the
 * caller's responsibility. No PR-supplied URL is ever fetched.
 */
import {ARTIN_PIN} from './proofnet-artin-replay-v1.mjs';

const MAX_ARTIFACT_BYTES=2*1024*1024;
const SOURCE_BYTES=64*1024;
const DATASET_BYTES=4*1024*1024;
const REPO=/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
const ensure=(ok,reason)=>{if(!ok)throw Error(reason);};

async function boundedBody(response,limit,errorCode){
  const readFailed=errorCode.startsWith('ARTIFACT_')?
    'ARTIFACT_DOWNLOAD_FAILED':'UPSTREAM_SOURCE_FETCH_FAILED';
  ensure(response?.status===200&&response.body?.getReader&&
    response.headers?.get,readFailed);
  const len=response.headers.get('content-length');
  if(len!==null){
    const n=Number(len);
    ensure(Number.isSafeInteger(n)&&n>=0&&n<=limit,errorCode);
  }
  const reader=response.body.getReader();
  const chunks=[];
  let size=0;
  let finished=false;
  try{
    for(;;){
      const {done,value}=await reader.read();
      if(done)break;
      ensure(value instanceof Uint8Array,errorCode);
      size+=value.length;
      ensure(size<=limit,errorCode);
      chunks.push(Buffer.from(value));
    }
    finished=true;
  }finally{
    if(!finished){try{await reader.cancel();}catch{/* Keep the original error. */}}
    reader.releaseLock();
  }
  ensure(size>0,readFailed);
  return Buffer.concat(chunks,size);
}

function acceptableArtifactHost(location){
  try{
    const u=new URL(location);
    return u.protocol==='https:'&&!u.username&&!u.password&&
      (u.hostname.endsWith('.blob.core.windows.net')||
      ['pipelines.actions.githubusercontent.com','objects.githubusercontent.com']
        .includes(u.hostname))&&u.port==='';
  }catch{return false;}
}

/**
 * Obtain artifact ZIP bytes from exactly the GitHub endpoint for an ID,
 * then follow only its one CDN redirect and never forward the bearer token.
 * The caller must compare these bytes against an independently read artifact
 * digest using verifyPinnedArtinArtifactBytes.
 */
export async function fetchPinnedArtifactZip({repository,artifactId,token,fetcher=fetch}={}){
  ensure(typeof repository==='string'&&REPO.test(repository)&&
    Number.isSafeInteger(artifactId)&&artifactId>0&&
    typeof token==='string'&&token.length>=8&&typeof fetcher==='function',
  'INVALID_ARTIFACT_DOWNLOAD_SCOPE');
  const endpoint=`https://api.github.com/repos/${repository}/actions/artifacts/${artifactId}/zip`;
  const first=await fetcher(endpoint,{method:'GET',redirect:'manual',
    headers:{Accept:'application/vnd.github+json',
      'X-GitHub-Api-Version':'2022-11-28',Authorization:'Bearer '+token},
    signal:AbortSignal.timeout(20000)});
  ensure(first?.status===302,'ARTIFACT_DOWNLOAD_FAILED');
  const location=first.headers?.get('location');
  ensure(acceptableArtifactHost(location),'UNTRUSTED_ARTIFACT_REDIRECT');
  const second=await fetcher(location,{method:'GET',redirect:'error',
    headers:{Accept:'application/octet-stream'},signal:AbortSignal.timeout(20000)});
  return boundedBody(second,MAX_ARTIFACT_BYTES,'ARTIFACT_DOWNLOAD_TOO_LARGE');
}

/** Original mathematical source from hard-coded, immutable upstream git SHA. */
export async function fetchPinnedArtinUpstream({fetcher=fetch}={}){
  ensure(typeof fetcher==='function','INVALID_UPSTREAM_FETCHER');
  const root=`https://raw.githubusercontent.com/${ARTIN_PIN.repository}/${ARTIN_PIN.commit}/`;
  const get=async(path,max)=>{
    const response=await fetcher(root+path,{method:'GET',redirect:'error',
      headers:{Accept:'application/octet-stream'},signal:AbortSignal.timeout(20000)});
    ensure(response?.status===200,'UPSTREAM_SOURCE_FETCH_FAILED');
    return boundedBody(response,max,'UPSTREAM_SOURCE_TOO_LARGE');
  };
  const sourceBytes=await get(ARTIN_PIN.sourcePath,SOURCE_BYTES);
  const jsonlBytes=await get(ARTIN_PIN.jsonlPath,DATASET_BYTES);
  return {sourceBytes,jsonlBytes,observedCommit:ARTIN_PIN.commit};
}
