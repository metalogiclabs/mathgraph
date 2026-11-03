// Trusted method-specific admission of the qualified research native artifact.
// Artifact digest and API responses are authenticated by captureProducer.
import {readFileSync} from 'node:fs';import {createHash} from 'node:crypto';
import {expectationSubject} from './expectations.mjs';
import {leadingReferenceOK} from './leading-obligation.mjs';
import {planFor} from '../../../experiments/check-expectation-admission-v1/binding-native.mjs';
import {inspectArm,guardBlocks} from '../lean-investigator-v1/contracts.mjs';
const policy=JSON.parse(readFileSync(new URL('../../../experiments/check-leading-redirection-v1/binding.json',import.meta.url)));
const hash=x=>createHash('sha256').update(x).digest('hex'),same=(a,b)=>JSON.stringify(a)===JSON.stringify(b),need=(b,c)=>{if(!b)throw Error(c);};
export function admitNativeRecheck(e,r){
 need(e&&r?.repository==='metalogiclabs/L4YAML','NATIVE_PRODUCER_REPOSITORY');
 const {run,artifact,pr,raw,commit,comparison}=e;
 need(run?.repository?.full_name==='metalogiclabs/mathgraph'&&run.path==='.github/workflows/check-leading-redirection-recheck.yml'&&run.event==='push'&&run.head_branch==='research/check-leading-redirection-v1'&&run.head_sha==='87bab75b5670b53c06adabf0b7686ec8511132b5'&&run.status==='completed'&&run.conclusion==='success'&&run.run_attempt===1,'NATIVE_PRODUCER_RUN');
 need(artifact?.name==='leading-redirection-recheck'&&artifact.expired===false&&artifact.workflow_run?.id===run.id&&artifact.workflow_run.head_sha===run.head_sha&&artifact.digest==='sha256:'+e.archive_sha256&&/^[a-f0-9]{64}$/.test(e.archive_sha256??''),'NATIVE_PRODUCER_ARTIFACT');
 need(pr?.state==='open'&&pr.number===r.number&&pr.head?.sha===r.head_sha&&pr.base?.sha===r.base_sha&&['head','base'].every(k=>pr[k].repo?.full_name===r.repository),'NATIVE_PRODUCER_PR');
 const m=JSON.parse(raw['manifest.json']),read=n=>JSON.parse(raw[n+'.json']);
 need(same(Object.keys(raw).filter(n=>n!=='manifest.json').sort(),Object.keys(m.hashes).sort()),'NATIVE_PRODUCER_MANIFEST');
 for(const[n,h]of Object.entries(m.hashes))need(/^[a-z][a-z0-9_-]*\.json$/.test(n)&&hash(raw[n])===h,'NATIVE_PRODUCER_BYTES');
 const s=read('snapshot'),plan=read('plan'),state=read('state'),native=read('native'),reference=read('expectation-admission').reference;
 need(m.context.verifier_sha===run.head_sha&&m.context.run_id===run.id&&m.context.attempt===1&&same(native.context,m.context)&&same(state.context,m.context),'NATIVE_PRODUCER_CONTEXT');
 need(s.repository===r.repository&&s.head_sha===r.head_sha&&s.path===policy.subject.path&&s.toolchain===policy.toolchain&&s.source===e.source&&s.source_sha256===hash(e.source)&&s.cli_source===e.cli_source&&hash(e.cli_source)===policy.cli_sha256,'NATIVE_PRODUCER_SUBJECT');
 need(same(plan,planFor(policy))&&native.source_sha===r.head_sha&&native.test_digest===state.test_digest&&state.test_digest===hash(JSON.stringify(plan.tests))&&leadingReferenceOK(reference?.records,true),'NATIVE_PRODUCER_EXPECTATIONS');
 const arm=inspectArm(native.arm,{profile:s,plan,source:s.source});need(arm.complete&&arm.rows.every(p=>p.execution==='GUARD_PASSED')&&guardBlocks(s.source).length===160,'NATIVE_PRODUCER_OBSERVATION');
 const f=comparison?.files?.[0],blob=createHash('sha1').update('blob '+Buffer.byteLength(e.source)+'\0'+e.source).digest('hex');
 need(commit?.sha===r.head_sha&&commit.parents?.length===1&&commit.parents[0].sha===r.base_sha&&comparison.base_commit?.sha===r.base_sha&&comparison.total_commits===1&&comparison.commits?.length===1&&comparison.commits[0].sha===r.head_sha&&comparison.files.length===1&&f.filename===s.path&&f.status==='modified'&&f.sha===blob,'NATIVE_PRODUCER_PUBLICATION');
 need(/^[a-f0-9]{40}$/.test(e.consumer_controller??''),'NATIVE_CONSUMER_CONTEXT');
 const subject=expectationSubject(s);
 return {subject,plan,facts:{subject,artifact_sha256:e.archive_sha256,requirement_sha256:hash(JSON.stringify(policy.proposals.map(p=>p.expression))),plan_sha256:hash(JSON.stringify(plan)),producer_parent:r.base_sha,producer_controller:m.context.verifier_sha,consumer_controller:e.consumer_controller,policy_sha256:hash(JSON.stringify(policy)),assumptions:['Authenticated exact research workflow and immutable native artifact','Operator-adopted finite obligations; customer approval UNKNOWN','Fresh hosted native/reference replay remains necessary'],limits:['Five frozen native input cases; not general shell conformance or a formal theorem','Source provenance does not broaden any historical receipt'],request:{repository:r.repository,number:r.number,head_sha:r.head_sha,base_sha:r.base_sha,comment_id:r.comment_id}}};
}
