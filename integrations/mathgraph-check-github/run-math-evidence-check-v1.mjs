/** Operator-only, fail-closed GitHub App check job. No webhook or auto-install. */
import {lstatSync,readFileSync} from 'node:fs';
import {collectAndPublishMathEvidence} from './math-evidence-check-run-v1.mjs';

const SHA40=/^[a-f0-9]{40}$/;
const SHA256=/^[a-f0-9]{64}$/;
const REPO=/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
const required=['repository','pr','runId','trusted'];
const trustedKeys=[
  'repository','pr','headSha','workflowPath','workflowSha256','workflowId',
  'jobName','artifactName','approvedReviewerIds','sourceSha256',
  'claimSha256','formalSha256','environmentSha256'];
const plain=x=>x&&typeof x==='object'&&!Array.isArray(x)&&
  Object.getPrototypeOf(x)===Object.prototype;
const exact=(o,ks)=>plain(o)&&Object.keys(o).length===ks.length&&
  ks.every(k=>Object.hasOwn(o,k));
const valid=o=>exact(o,required)&&
  REPO.test(o.repository)&&Number.isSafeInteger(o.pr)&&o.pr>0&&
  Number.isSafeInteger(o.runId)&&o.runId>0&&
  exact(o.trusted,trustedKeys)&&
  o.trusted.repository===o.repository&&o.trusted.pr===o.pr&&
  SHA40.test(o.trusted.headSha)&&SHA256.test(o.trusted.workflowSha256)&&
  Number.isSafeInteger(o.trusted.workflowId)&&o.trusted.workflowId>0&&
  o.trusted.workflowPath==='.github/workflows/mathgraph-check-proofnet-artin-replay-v2.yml'&&
  o.trusted.jobName==='pinned-artin-replay'&&
  o.trusted.artifactName==='mathgraph-proofnet-artin-evidence'&&
  ['sourceSha256','claimSha256','formalSha256','environmentSha256']
    .every(k=>SHA256.test(o.trusted[k]))&&
  Array.isArray(o.trusted.approvedReviewerIds)&&
  o.trusted.approvedReviewerIds.length<=32&&
  o.trusted.approvedReviewerIds.every(n=>Number.isSafeInteger(n)&&n>0)&&
  new Set(o.trusted.approvedReviewerIds).size===o.trusted.approvedReviewerIds.length;

async function main(){
  if(!([3,4].includes(process.argv.length))||
    (process.argv.length===4&&process.argv[3]!=='--publish')){
    process.stderr.write('USAGE: node run-math-evidence-check-v1.mjs TRUST_FILE [--publish]\n');
    process.exitCode=2;return;
  }
  const token=process.env.MATHGRAPH_GITHUB_APP_TOKEN;
  if(typeof token!=='string'||token.length<10){
    process.stderr.write('MISSING_REPOSITORY_SCOPED_INSTALLATION_TOKEN\n');
    process.exitCode=2;return;
  }
  let config;
  try{
    const st=lstatSync(process.argv[2]);
    if(!st.isFile()||st.size<2||st.size>65536||
      (process.platform!=='win32'&&(st.mode&0o077)!==0))throw Error('INVALID');
    config=JSON.parse(readFileSync(process.argv[2],'utf8'));
    if(!valid(config))throw Error('INVALID');
  }catch{
    process.stderr.write('INVALID_PRIVATE_ADMIN_TRUST_FILE\n');
    process.exitCode=2;return;
  }
  try{
    const report=await collectAndPublishMathEvidence({...config,token},{
      publish:process.argv[3]==='--publish'});
    process.stdout.write(JSON.stringify(report,null,2)+'\n');
    if(report.mode!=='PREVIEW'&&report.mode!=='PUBLISHED')process.exitCode=2;
  }catch{
    process.stderr.write('MATH_EVIDENCE_COLLECTION_OR_PUBLICATION_FAILED\n');
    process.exitCode=2;
  }
}
await main();
