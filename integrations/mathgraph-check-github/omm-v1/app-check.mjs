// OMM projection to the *existing* MathGraph Check GitHub App Check-run schema.
// This is a pure payload preview. Only the authenticated App publisher may
// create the Check run after independently verifying immutable evidence pins,
// exact live head and installation permissions. No PR code executes here.
import {assessOmmClaim} from './claim-admission.mjs';
import {formatOmmClaimReport,ommClaimView} from './report.mjs';
import {buildAdvisoryCheck} from '../advisory-publisher-v1.mjs';

export function buildOmmAppCheckPreview({request,expectedHeadSha,runUrl,...nativeInputs}={}){
 if(request?.command!=='check')throw Error('OMM_CHECK_ONLY');
 const assessment=assessOmmClaim({request,...nativeInputs});
 const view=ommClaimView(assessment,request);
 const qualified=assessment.status==='NATIVE_RECEIPT_BOUND';
 const results=[
  {id:'candidate-Lean-build',status:qualified&&view.candidate_proof==='LEAN_COMPILED'?'OBSERVED':'UNKNOWN'},
  {id:'original-claim-consumer',status:qualified&&view.original_target==='CONSUMER_ACCEPTED'?'OBSERVED':
   qualified&&view.original_target==='NOT_ESTABLISHED_IN_THIS_REPLAY'?'BLOCKED':'UNKNOWN'},
  {id:'paper-to-Lean-intent',status:'UNKNOWN'},
  {id:'independent-evidence-attestation',status:'UNKNOWN'}
 ];
 const generic={source:request,status:'UNKNOWN',permission:'ADVISORY_ONLY',
  scope:'GITHUB_CHECK_RUN_OBSERVATION_ONLY',results,
  evidence:results.filter(r=>r.status==='OBSERVED')};
 const base=buildAdvisoryCheck(generic,{repository:request.repository,sha:expectedHeadSha});
 const detail=formatOmmClaimReport(assessment,request,runUrl);
 return {assessment,payload:{...base,name:'MathGraph Check / OMM claim (advisory)',
  external_id:`mathgraph-omm-claim-v1:${request.repository}:${request.number}:${expectedHeadSha}`,
  output:{title:'OMM: '+view.title+' (advisory)',
   summary:[base.output.summary,detail,
     'Publication and exact-head App identity require separate GitHub readback. This Check conveys bounded native observations, not an independent mathematical-intent warrant.'].join('\n\n').slice(0,65000)}}};
}
