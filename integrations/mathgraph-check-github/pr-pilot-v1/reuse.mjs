import {createHash} from 'node:crypto';import {admitLeanPlan} from '../lean-investigator-v1/contracts.mjs';
const hash=x=>createHash('sha256').update(x).digest('hex');
export function rebindFrozenPlan(prior,request,context){
 if(prior.context.verifier_sha!==context.verifier_sha||prior.context.attempt!==1||prior.context.run_id===context.run_id||prior.assessment.status!=='CANDIDATE_ASSERTION_FAILURE'||prior.state.state!=='PROBES_PROPOSED'||request.command!=='fix')throw Error('PRIOR_CHECK_NOT_REUSABLE');
 for(const k of ['repository','number','head_sha','base_sha'])if(prior.snapshot[k]!==request[k])throw Error('PRIOR_SUBJECT_MISMATCH');
 const plan=admitLeanPlan(prior.plan);
 if(hash(prior.snapshot.source)!==prior.snapshot.source_sha256||hash(JSON.stringify(plan.tests))!==prior.state.test_digest)throw Error('PRIOR_SOURCE_OR_PROBES_CHANGED');
 return {snapshot:{...prior.snapshot,command:'fix',comment_id:request.comment_id},plan,state:{context,state:'PROBES_PROPOSED',test_digest:prior.state.test_digest,model_calls:0,proposal_origin:prior.context}};
}
