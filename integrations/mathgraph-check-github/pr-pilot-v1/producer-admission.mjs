import {createHash} from 'node:crypto';
import {expectationSubject,admitExpectations,qualifyProducerSubject} from './expectations.mjs';
import {admitNativeRecheck} from './native-recheck-producer.mjs';
import {admitLeanPatch,inspectArm,guardBlocks} from '../lean-investigator-v1/contracts.mjs';
// Caller supplies authenticated GitHub responses and the downloaded artifact's
// exact bytes. PR prose is only a locator; neither it nor saved verdicts suffice.
export const PRODUCER_CONTROLLER='0ffe73933f3ea6b505c4862e43e0280d0160eacc';
const hash=x=>createHash('sha256').update(x).digest('hex');
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const need=(b,c)=>{if(!b)throw Error(c);};
export function producerRelease(run,context={}){
 if(run?.head_sha==='a6651de78193d70bbb72e59e868670e675981bf4')return PRODUCER_CONTROLLER;
 need(/^[a-f0-9]{40}$/.test(context.verifier_sha??'')&&/^[a-f0-9]{40}$/.test(context.scheduler_sha??'')&&run?.head_sha===context.scheduler_sha,'UNTRUSTED_PRODUCER_RELEASE');return context.verifier_sha;
}
export function admitProducer(e,request,runtimeContext={},depth=0){
 need(e&&request?.repository==='metalogiclabs/L4YAML','PRODUCER_REPOSITORY');
 const {run,artifact,raw,check,commit,comparison,pr}=e;
 const producerController=producerRelease(run,runtimeContext);
 need(run?.repository?.full_name==='metalogiclabs/mathgraph'&&run.path==='.github/workflows/check-pr-pilot.yml'&&run.event==='repository_dispatch'&&run.head_branch==='main'&&run.status==='completed'&&run.conclusion==='success'&&run.run_attempt===1&&Number.isSafeInteger(run.id),'PRODUCER_RUN');
 need(artifact?.name==='pr-pilot-publication'&&artifact.expired===false&&artifact.workflow_run?.id===run.id&&artifact.workflow_run.head_sha===run.head_sha&&artifact.digest==='sha256:'+e.archive_sha256&&/^[a-f0-9]{64}$/.test(e.archive_sha256??''),'PRODUCER_ARTIFACT');
 need(pr?.user?.id===342263476&&pr.user.login==='mathgraph-check[bot]'&&pr.user.type==='Bot'&&pr.state==='open'&&pr.number===request.number&&pr.head?.sha===request.head_sha&&pr.base?.sha===request.base_sha&&['head','base'].every(k=>pr[k]?.repo?.full_name===request.repository),'PRODUCER_TARGET_PR');
 need(typeof e.workflow==='string','PRODUCER_WORKFLOW');
 const pins=[...e.workflow.matchAll(/\bref: ([a-f0-9]{40})(?=[}\s])/g)].map(m=>m[1]);
 need(pins.length>=1&&pins.every(p=>p===producerController)&&e.workflow.includes('MATHGRAPH_CONTROLLER_SHA: '+producerController),'PRODUCER_WORKFLOW_PIN');
 const manifest=JSON.parse(raw['manifest.json']);
 need(same(Object.keys(raw).filter(n=>n!=='manifest.json').sort(),Object.keys(manifest.hashes).sort()),'PRODUCER_MANIFEST');
 for(const[n,h]of Object.entries(manifest.hashes))need(/^[a-z][a-z0-9_-]*\.json$/.test(n)&&hash(raw[n])===h,'PRODUCER_BYTES');
 const read=n=>JSON.parse(raw[n+'.json']);
 const s=read('snapshot'),p=read('plan'),state=read('state'),native=read('native'),fixed=read('native-repair'),patch=read('patch'),publication=read('publication'),published=read('publication-result'),r=read('request');
 const context=manifest.context;
 need(context.verifier_sha===producerController&&context.run_id===run.id&&context.scheduler_sha===run.head_sha&&context.attempt===1,'PRODUCER_CONTEXT');
 for(const o of [state,native,fixed,publication])need(same(o.context,context),'PRODUCER_CONTEXT');
 need(r.repository===request.repository&&r.command==='fix'&&r.head_sha===s.head_sha&&s.repository===r.repository&&r.number===s.number&&r.head_sha===request.base_sha&&s.path==='Scripts/Ledger.lean'&&s.source_sha256===hash(s.source),'PRODUCER_SUBJECT');
 let sourceToken;
 if(raw['producer-envelope.json']){
  need(depth<2,'PRODUCER_LINEAGE_TOO_DEEP');const prior=read('producer-envelope');need(prior.consumer_controller===context.verifier_sha,'PRODUCER_SOURCE_ADMISSION_CONTEXT');
  const admitted=prior.run?.path==='.github/workflows/check-leading-redirection-recheck.yml'?admitNativeRecheck(prior,r):admitProducer(prior,r,context,depth+1);
  need(same(admitted.subject,expectationSubject(s)),'PRODUCER_SOURCE_LINEAGE');sourceToken=qualifyProducerSubject(admitted.subject);
 }
 need(admitExpectations(expectationSubject(s),p,read('expectation-reference'),context,sourceToken,s.expectation_profile??'ledger-shell-v1').repair_eligible,'PRODUCER_EXPECTATIONS');
 const digest=hash(JSON.stringify(p.tests));
 need(state.test_digest===digest&&[native,fixed].every(n=>n.source_sha===s.head_sha&&n.test_digest===digest),'PRODUCER_PROBES');
 const patched=admitLeanPatch(patch,s.source),target={...s,head_sha:request.head_sha,source:e.source,cli_source:e.cli_source};
 need(patched===e.source&&hash(patched)===patch.patched_sha256&&fixed.patched_sha256===patch.patched_sha256&&hash(e.cli_source)===hash(s.cli_source),'PRODUCER_TARGET_BYTES');
 need(commit?.sha===request.head_sha&&commit.parents?.length===1&&commit.parents[0].sha===s.head_sha&&comparison.base_commit?.sha===s.head_sha&&comparison.commits?.length===1&&comparison.commits[0].sha===request.head_sha&&comparison.total_commits===1&&comparison.files?.length===1,'PRODUCER_COMMIT');
 const f=comparison.files[0],blob=createHash('sha1').update('blob '+Buffer.byteLength(patched)+'\0'+patched).digest('hex');
 need(f.filename===s.path&&f.status==='modified'&&f.sha===blob,'PRODUCER_TREE');
 const inspect=(arm,source)=>inspectArm(arm,{profile:s,plan:p,source});
 const initial=inspect(native.arm,s.source),old=inspect(fixed.original,s.source),after=inspect(fixed.repaired,patched),withdrawn=inspect(fixed.withdrawn,s.source);
 need([initial,old,after,withdrawn].every(a=>a.complete)&&old.rows.some(p=>p.execution==='CANDIDATE_ASSERTION_FAILURE')&&after.rows.every(p=>p.execution==='GUARD_PASSED')&&same(initial.rows,old.rows)&&same(old.rows,withdrawn.rows)&&guardBlocks(s.source).length===160,'PRODUCER_NATIVE');
 const runURL='https://github.com/metalogiclabs/mathgraph/actions/runs/'+run.id;
 need(published.state==='PUBLISHED'&&published.check_id===publication.check_id&&check?.id===published.check_id&&check.app?.id===5308912&&check.head_sha===s.head_sha&&check.details_url===runURL&&check.status==='completed'&&check.conclusion==='neutral'&&check.output?.summary?.includes('https://github.com/'+request.repository+'/pull/'+request.number),'PRODUCER_PUBLICATION');
 need(/^[a-f0-9]{40}$/.test(e.consumer_controller??''),'CONSUMER_CONTROLLER');
 const subject=expectationSubject(target);
 return {subject,plan:p,facts:{subject,artifact_sha256:e.archive_sha256,requirement_sha256:hash(JSON.stringify(p.tests.map(t=>t.contract))),plan_sha256:hash(JSON.stringify(p)),producer_parent:s.head_sha,producer_controller:context.verifier_sha,consumer_controller:e.consumer_controller,policy_sha256:hash('ledger-producer-transport:'+ (s.expectation_profile??'ledger-shell-v1')),limits:[p.tests.length+' recorded finite guards; not a formal theorem','Current expectation admission and fresh target replay remain separate'],assumptions:['Authenticated hosted producer and immutable scheduler pin','Native controls and repository gate within recorded environment','No whole-PR or general Bash correctness claim'],request:{repository:request.repository,number:request.number,head_sha:request.head_sha,base_sha:request.base_sha,comment_id:request.comment_id}}};
}
