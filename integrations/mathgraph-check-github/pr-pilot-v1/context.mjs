export function executionContext(env=process.env){
 const context={verifier_sha:env.MATHGRAPH_CONTROLLER_SHA??env.GITHUB_SHA,run_id:Number(env.GITHUB_RUN_ID),attempt:Number(env.GITHUB_RUN_ATTEMPT)};
 if(env.MATHGRAPH_CONTROLLER_SHA)context.scheduler_sha=env.GITHUB_SHA;
 if(!/^[a-f0-9]{40}$/.test(context.verifier_sha??'')||context.scheduler_sha&&!/^[a-f0-9]{40}$/.test(context.scheduler_sha)||!Number.isSafeInteger(context.run_id)||context.run_id<1||context.attempt!==1)throw Error('INVALID_EXECUTION_CONTEXT');return context;
}
