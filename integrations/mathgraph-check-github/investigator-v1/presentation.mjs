const NAME='MathGraph Check / generic Python investigation';
export function buildCheck(r,{sha,runId}={}){
 if(!/^[a-f0-9]{40}$/.test(sha??'')||r?.context?.verifier_sha!==sha||r.context.run_id!==runId)throw Error('STALE_ASSESSMENT');
 const run=`https://github.com/metalogiclabs/mathgraph/actions/runs/${runId}`;
 const rows=(r.probes??[]).map(p=>`| ${p.id} | ${p.base.execution} | ${p.head.execution} |`).join('\n');
 const reason=String(r.reason??'See individual probe and protected-suite outcomes').replace(/[`\r\n]/g,' ').slice(0,350);
 return {name:NAME,head_sha:sha,status:'completed',conclusion:'neutral',details_url:run,external_id:'investigator-v1:'+sha,output:{title:'MathGraph Check: '+r.status,summary:[
 '**Advisory pilot. Model-generated probes; native execution observed separately. Meaning remains UNVERIFIED.**',
 r.subject?`Watched source: ${r.subject.source_repository} PR${r.subject.pr}@${r.subject.head_sha}. Owned fork: ${r.subject.repository}. This Check is attached to the MathGraph investigator commit, not to the watched PR.`:'No eligible source snapshot is available.',
 `Stage: ${r.stage??'assessment'}. Reason: \`${reason}\`.`,
 '| Generated probe | Base execution | Head execution |\n|---|---|---|\n'+rows,
 `Protected native suite: ${JSON.stringify(r.protected_suites??{})}.`,
 `Repair: ${r.repair?.status??'NOT_PROPOSED'}. A native pass covers only the frozen probes and declared protected suite; it does not certify the model-selected requirement.`,
 '**No automatic merge. No universal correctness or prospective superiority claim.**',
 `[Source snapshot, model proposals, usage, native logs and candidate patch](${run})`
 ].join('\n\n')}};
}
export function admitPublication(c,sha){
 if(c?.head_sha!==sha||c?.conclusion!=='neutral'||c?.name!==NAME||c?.app?.id!==5308912||c?.app?.slug!=='mathgraph-check')throw Error('REGISTERED_APP_READBACK_MISMATCH');return true;
}
