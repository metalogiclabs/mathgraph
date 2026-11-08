/**
 * Read-only operator entrypoint. Run ONLY from administrator-controlled code
 * with keys/policy files provisioned outside audited PR content. Never use a
 * `pull_request` merge checkout with credentials for this purpose.
 */
import {statSync,readFileSync} from 'node:fs';
import {eligibleProtectedContext,qualifyProtectedReview} from './protected-review-runner-v1.mjs';

const unknown=reason=>({schema:'mathgraph.protected-review-admission.v1',
 status:'UNKNOWN',reason,terminal_form:null,permission:'ADVISORY_ONLY',
 proof_replay:'NOT_PERFORMED',universal_sufficiency:'NOT_ESTABLISHED'});

const readJSON=(name,maxBytes)=>{
 const path=process.env[name];
 if(typeof path!=='string'||!path||path.length>1024)throw Error('INPUT_FILE_REQUIRED');
 const stat=statSync(path);
 if(!stat.isFile()||stat.size<2||stat.size>maxBytes)throw Error('INPUT_FILE_INVALID');
 return JSON.parse(readFileSync(path,'utf8'));
};

try{
 const context={event_name:process.env.GITHUB_EVENT_NAME,
  ref:process.env.GITHUB_REF,default_branch:process.env.MATHGRAPH_DEFAULT_BRANCH,
  repository:process.env.GITHUB_REPOSITORY,
  pr:Number(process.env.MATHGRAPH_PR_NUMBER),token:process.env.GITHUB_TOKEN,
  evidence_token:process.env.MATHGRAPH_EVIDENCE_TOKEN};
 if(!eligibleProtectedContext(context)){
  process.stdout.write(JSON.stringify(unknown('PROTECTED_DEFAULT_BRANCH_DISPATCH_REQUIRED'))+'\n');
  process.exitCode=3;
 }else{
 const report=await qualifyProtectedReview({context,
  signedProjectionReview:readJSON('MATHGRAPH_SIGNED_REVIEW_FILE',262144),
  trustedReviewerKeys:readJSON('MATHGRAPH_TRUSTED_REVIEWER_KEYS_FILE',32768),
  trustedProofReceipt:readJSON('MATHGRAPH_TRUSTED_PROOF_RECEIPT_FILE',8192),
  artifactPath:process.env.MATHGRAPH_PROOF_ARTIFACT_PATH,
  artifactId:Number(process.env.MATHGRAPH_PROOF_ARTIFACT_ID)});
 process.stdout.write(JSON.stringify(report,null,2)+'\n');
 if(report.status!=='BLOCKED')process.exitCode=3;
 }
}catch{
 process.stdout.write(JSON.stringify(unknown('EXTERNAL_POLICY_OR_REVIEW_UNAVAILABLE'))+'\n');
 process.exitCode=3;
}
