import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {BRAHE_SOURCE_V1,transplantBraheTestsV1} from './brahe-endpoint-v1.mjs';
import {buildBraheRunReceiptV1,combineBraheReceiptsV1} from './run-brahe-endpoint-v1.mjs';

function parseArgs(args) {
  if (args.length%2!==0) throw Error('INVALID_ARGUMENT_PAIRS');
  const out=new Map();
  for (let i=0;i<args.length;i+=2) {
    if (!args[i].startsWith('--')||out.has(args[i])) throw Error('INVALID_ARGUMENT');
    out.set(args[i],args[i+1]);
  }
  return key=>{
    const value=out.get('--'+key);
    if (!value)throw Error('MISSING_'+key.toUpperCase().replaceAll('-','_'));
    return value;
  };
}

export async function runBraheCliV1(args=[]) {
  const get=parseArgs(args),mode=get('mode');
  if (mode==='transplant') {
    const basePath=get('base'),headPath=get('head');
    const [baseSource,headSource]=await Promise.all([readFile(basePath,'utf8'),readFile(headPath,'utf8')]);
    const {patchedBaseSource,baseProductionBytes,headTestModuleBytes}=transplantBraheTestsV1({baseSource,headSource});
    const manifest={
      source:{...BRAHE_SOURCE_V1},
      baseProductionBytes,headTestModuleBytes,
      patchedSourceSha256:createHash('sha256').update(patchedBaseSource).digest('hex')
    };
    await writeFile(basePath,patchedBaseSource);
    await writeFile(get('manifest'),JSON.stringify(manifest,null,2)+'\n');
    return manifest;
  }
  if (mode==='base'||mode==='head') {
    const [stdout,stderr]=await Promise.all([readFile(get('stdout'),'utf8'),readFile(get('stderr'),'utf8')]);
    const result=buildBraheRunReceiptV1({mode,sourceSha:get('source-sha'),exitCode:Number(get('exit')),stdout,stderr});
    await writeFile(get('out'),JSON.stringify(result,null,2)+'\n');
    return result;
  }
  if (mode==='finalize') {
    const [base,head]=await Promise.all([readFile(get('base'),'utf8'),readFile(get('head'),'utf8')]);
    const result=combineBraheReceiptsV1({
      base:JSON.parse(base),head:JSON.parse(head),rustc:get('rustc'),
      cargoLockSha256:get('cargo-lock-sha256'),workflowRunUrl:get('run-url'),
      basePatchedBlobSha:get('base-patched-blob-sha')
    });
    await writeFile(get('out'),JSON.stringify(result,null,2)+'\n');
    return result;
  }
  throw Error('INVALID_MODE');
}

if (process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const result=await runBraheCliV1(process.argv.slice(2));
  console.log(JSON.stringify(result.verdict?{
    status:result.verdict.status,unknowns:result.verdict.unknowns
  }:result.reason?{
    reason:result.reason,testCount:result.testCount,regressionCount:result.regressionCount
  }:{source:result.source,patchedSourceSha256:result.patchedSourceSha256}));
  if (result.verdict?.status==='UNKNOWN') process.exitCode=1;
}
