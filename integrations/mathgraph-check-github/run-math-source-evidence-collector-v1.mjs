/** Read-only GitHub App job entry. Never reads credentials from PR content. */
import {readFileSync,lstatSync} from 'node:fs';
import {ARTIN_PIN} from './proofnet-artin-replay-v1.mjs';
import {collectMathSourceEvidence}
  from './math-source-evidence-collector-v1.mjs';

const SHA40=/^[a-f0-9]{40}$/;
const SHA256=/^[a-f0-9]{64}$/;
const REPO=/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
const CLAIM='a908ad4a14106793dec67703b4051fd3587be202fcd94c5778981cab409051a0';
const plain=x=>x!==null&&typeof x==='object'&&!Array.isArray(x)&&
  Object.getPrototypeOf(x)===Object.prototype;
const valid=o=>plain(o)&&Object.keys(o).length===4&&
  REPO.test(o.repository??'')&&Number.isSafeInteger(o.pr)&&o.pr>0&&
  Number.isSafeInteger(o.runId)&&o.runId>0&&plain(o.trusted)&&
  o.trusted.repository===o.repository&&o.trusted.pr===o.pr&&
  SHA40.test(o.trusted.headSha??'')&&SHA256.test(o.trusted.workflowSha256??'')&&
  SHA256.test(o.trusted.environmentSha256??'')&&
  Number.isSafeInteger(o.trusted.workflowId)&&o.trusted.workflowId>0&&
  o.trusted.workflowPath==='.github/workflows/mathgraph-check-proofnet-artin-replay-v1.yml'&&
  o.trusted.jobName==='pinned-artin-replay'&&
  o.trusted.artifactName==='mathgraph-proofnet-artin-evidence'&&
  o.trusted.sourceSha256===ARTIN_PIN.sourceSha256&&
  o.trusted.claimSha256===CLAIM&&
  o.trusted.formalSha256===ARTIN_PIN.formalSha256&&
  Array.isArray(o.trusted.approvedReviewerIds)&&
  o.trusted.approvedReviewerIds.length<=32&&
  o.trusted.approvedReviewerIds.every(n=>Number.isSafeInteger(n)&&n>0)&&
  new Set(o.trusted.approvedReviewerIds).size===o.trusted.approvedReviewerIds.length;

async function main(){
  if(process.argv.length!==3){
    process.stderr.write('USAGE: node run-math-source-evidence-collector-v1.mjs TRUST_FILE\n');
    process.exitCode=2;return;
  }
  const token=process.env.MATHGRAPH_GITHUB_APP_TOKEN;
  if(typeof token!=='string'||token.length<8){
    process.stderr.write('MISSING_INSTALLATION_TOKEN\n');
    process.exitCode=2;return;
  }
  let config;
  try{
    const st=lstatSync(process.argv[2]);
    if(!st.isFile()||st.size>65536||st.size<2)throw Error('INVALID');
    config=JSON.parse(readFileSync(process.argv[2],'utf8'));
    if(!valid(config))throw Error('INVALID');
  }catch{
    process.stderr.write('INVALID_ADMIN_MANIFEST\n');
    process.exitCode=2;return;
  }
  try{
    const result=await collectMathSourceEvidence({...config,token});
    process.stdout.write(JSON.stringify(result,null,2)+'\n');
    if(result.status!=='EVIDENCE_BYTES_CORRELATED')process.exitCode=2;
  }catch{
    process.stderr.write('OBSERVATION_ERROR\n');
    process.exitCode=2;
  }
}

await main();
