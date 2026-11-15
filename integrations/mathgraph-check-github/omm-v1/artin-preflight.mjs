// Authenticated, fixed-cohort Artin input binding for the OMM *research*
// workflow. Never accepts an arbitrary PR number, source path or Lean program.
import {createHash} from 'node:crypto';
import {mkdir,writeFile} from 'node:fs/promises';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {artinStrongSource,artinRepairSource,bindPublishedArtin} from '../mention-artin-control-v1.mjs';

const digest=s=>createHash('sha256').update(s).digest('hex');
const REPO='metalogiclabs/mathgraph';
const ORIGINAL='https://raw.githubusercontent.com/marcusm117/ProofNet-Verified/14879cb23e078d122adecd9578dd26a7304f753b/data/archive/proofnet-verified-4.28/proofnet-1.lean';
const FILE='mathgraph-demo/ArtinGenerators.lean';
const PROFILES=Object.freeze({
  239:{head:'2f6aaba0d71f1c0b4c0db58618a8981ccd59dc17',base:'dfd87d1e921953badedcfae21ade76bb38f5c04a',
    candidate:artinStrongSource,source_hash:'e45efb73729fc98e45e66d216e792e70f67f8c43d4c12cbb753ac410b950e4d9',
    changed:['mathgraph-demo/ArtinGenerators.lean:added','mathgraph-demo/README.md:added']},
  240:{head:'06f09cd5aaa866365ceb6540cd06389bd37a727c',base:'2f6aaba0d71f1c0b4c0db58618a8981ccd59dc17',
    candidate:artinRepairSource,source_hash:'7153ebbaef33070b5b25ee3e8f3ba6dd35c6868f7a5dac07867255635ed85557',
    changed:['mathgraph-demo/ArtinGenerators.lean:modified']}
});

async function getBody(fetcher,url,parseJson){
 const response=await fetcher(url,{headers:{Accept:'application/vnd.github+json','User-Agent':'MathGraph-OMM-Bounded-Qualification'}});
 if(!response?.ok)throw Error('TRUSTED_SOURCE_FETCH_UNAVAILABLE');
 const raw=await response.text();
 if(raw.length>1_000_000)throw Error('TRUSTED_SOURCE_SIZE_EXCEEDED');
 try{return parseJson?JSON.parse(raw):raw;}catch{throw Error('TRUSTED_SOURCE_JSON_INVALID');}
}

export async function checkPublishedArtinInput({number,fetch:fetcher=globalThis.fetch,verifyReference=bindPublishedArtin}={}){
 if(!Number.isInteger(number)||!PROFILES[number])throw Error('UNREGISTERED_ARTIN_PR');
 if(typeof fetcher!=='function'||typeof verifyReference!=='function')throw Error('TRUSTED_SOURCE_FETCH_UNAVAILABLE');
 const profile=PROFILES[number];
 const root=`https://api.github.com/repos/${REPO}`;
 const pull=await getBody(fetcher,`${root}/pulls/${number}`,true);
 if(pull?.number!==number||pull?.state!=='open'||pull?.head?.sha!==profile.head||
   pull?.base?.sha!==profile.base||pull?.head?.repo?.full_name!==REPO||
   pull?.base?.repo?.full_name!==REPO||pull?.changed_files!==profile.changed.length)
  throw Error('PR_IDENTITY_CHANGED');
 const files=await getBody(fetcher,`${root}/pulls/${number}/files?per_page=100`,true);
 if(!Array.isArray(files)||files.length!==profile.changed.length||
   files.map(f=>`${f.filename}:${f.status}`).sort().join('|')!==profile.changed.slice().sort().join('|'))
  throw Error('PR_DIFF_SURFACE_CHANGED');
 const source=await getBody(fetcher,`https://raw.githubusercontent.com/${REPO}/${profile.head}/${FILE}`,false);
 if(digest(profile.candidate)!==profile.source_hash||source!==profile.candidate||digest(source)!==profile.source_hash)
  throw Error('SOURCE_BYTES_CHANGED');
 const publishedSource=await getBody(fetcher,ORIGINAL,false);
 try{if(!verifyReference(publishedSource))throw Error('PUBLISHED_TARGET_CHANGED');}
 catch(e){if(e.message==='PUBLISHED_TARGET_CHANGED')throw e;throw Error('PUBLISHED_TARGET_CHANGED');}
 return {request:{schema:'mathgraph.omm.request.v1',repository:REPO,number,command:'check',
   head_sha:profile.head,base_sha:profile.base,candidate_source_sha256:profile.source_hash},
  source,publishedSource};
}

if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
 try{
  const number=Number(process.argv[2]),directory=process.argv[3];
  if(process.argv.length!==4||!directory?.startsWith('/')||
    process.env.GITHUB_REPOSITORY!==REPO||
    !/^[1-9][0-9]*$/.test(process.env.GITHUB_RUN_ID??'')||
    !process.env.GITHUB_TOKEN)throw Error('QUALIFICATION_CONTEXT_REQUIRED');
  const authorizedFetch=(url,opts)=>fetch(url,{...opts,headers:{...opts?.headers,
   ...(url.startsWith(`https://api.github.com/repos/${REPO}/`)?{Authorization:`Bearer ${process.env.GITHUB_TOKEN}`}:{})}});
  const {request,source,publishedSource}=await checkPublishedArtinInput({number,fetch:authorizedFetch});
  const dir=resolve(directory);
  await mkdir(dir,{recursive:false});
  await Promise.all([
   writeFile(join(dir,'request.json'),JSON.stringify(request,null,2)+'\n',{flag:'wx'}),
   writeFile(join(dir,'candidate.lean.txt'),source,{flag:'wx'}),
   writeFile(join(dir,'published-exercise.lean.txt'),publishedSource,{flag:'wx'})
  ]);
  console.log(`OMM_ARTIN_PREFLIGHT_BOUND:${number}:${request.head_sha}`);
 }catch(e){console.error('OMM_ARTIN_PREFLIGHT_UNKNOWN:'+String(e.message));process.exitCode=1;}
}
