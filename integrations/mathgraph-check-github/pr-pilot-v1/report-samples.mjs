// Re-render historical receipts with the current presenter. No Check publication.
import fs from 'node:fs/promises';import path from 'node:path';import {createHash} from 'node:crypto';
import {admitRepositoryResult} from './repository-contract.mjs';import {formatContractResult} from './repository-report.mjs';import {renderReport} from './report.mjs';
const root=process.argv[2],out=process.argv[3];await fs.mkdir(out,{recursive:true});
const css=await fs.readFile(new URL('./passport-base.css',import.meta.url),'utf8'),brand=JSON.parse(await fs.readFile(new URL('./passport-brand.json',import.meta.url),'utf8'));
const summaries=[];
for(const name of await fs.readdir(root)){
 const dir=path.join(root,name);if(!(await fs.stat(dir)).isDirectory())continue;
 const read=async n=>JSON.parse(await fs.readFile(path.join(dir,n+'.json'),'utf8'));
 const request=await read('request'),manifest=await read('manifest');
 for(const[n,h]of Object.entries(manifest.hashes)){if(!/^[a-z][a-z0-9_-]*\.json$/.test(n)||createHash('sha256').update(await fs.readFile(path.join(dir,n))).digest('hex')!==h)throw Error('SAMPLE_ARTIFACT_CHANGED');}
 const native=await read('contract-receipt');let corpus=null;try{corpus=await fs.readFile(path.join(dir,'contract-corpus.json'));}catch{try{corpus=await fs.readFile(path.join(dir,'contract-native/corpus.json'));}catch{}}
 const assessment=admitRepositoryResult(native,request,manifest.context,corpus);
 const url=`https://github.com/metalogiclabs/mathgraph/actions/runs/${manifest.context.run_id}`;
 await fs.writeFile(path.join(out,name+'.md'),formatContractResult(assessment,request,url)+'\n');
 await fs.writeFile(path.join(out,name+'.html'),renderReport({request,assessment,manifest,css,logo:brand.logo}));
 summaries.push({name,pr:request.number,status:assessment.status,reason:assessment.reason,witnesses:assessment.witnesses?.length??0,original_context:manifest.context,representation:'HISTORICAL_EVIDENCE_RENDERED_WITH_CURRENT_PRESENTER'});
}
await fs.writeFile(path.join(out,'samples.json'),JSON.stringify(summaries,null,2)+'\n');console.log(JSON.stringify(summaries.map(x=>({name:x.name,pr:x.pr,status:x.status,reason:x.reason,witnesses:x.witnesses}))));
