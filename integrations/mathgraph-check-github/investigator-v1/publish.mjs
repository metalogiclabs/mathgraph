import {readFile,writeFile} from 'node:fs/promises';
const dir=process.argv[2]??'investigation';
const r=JSON.parse(await readFile(`${dir}/assessment.json`,'utf8'));
if(r.context.verifier_sha!==process.env.GITHUB_SHA||r.context.run_id!==Number(process.env.GITHUB_RUN_ID))throw Error('STALE_ASSESSMENT');
const run=`https://github.com/metalogiclabs/mathgraph/actions/runs/${process.env.GITHUB_RUN_ID}`;
const rows=(r.probes??[]).map(p=>`| ${p.id} | ${p.base.execution} | ${p.head.execution} |`).join('\n');
const body={name:'MathGraph Check / generic Python investigation',head_sha:process.env.GITHUB_SHA,status:'completed',conclusion:'neutral',details_url:run,external_id:'investigator-v1:'+process.env.GITHUB_SHA,output:{title:'MathGraph Check: '+r.status,summary:[
 '**Advisory pilot. Model-generated probes; native execution observed separately. Meaning remains UNVERIFIED.**',
 r.subject?`Watched source: ${r.subject.source_repository} PR${r.subject.pr}@${r.subject.head_sha}. Owned fork: ${r.subject.repository}. This Check is attached to the MathGraph investigator commit, not to the watched PR.`:'No eligible source was investigated.',
 '| Generated probe | Base execution | Head execution |\n|---|---|---|\n'+rows,
 `Protected native suite: ${JSON.stringify(r.protected_suites??{})}.`,
 `Repair: ${r.repair?.status??'NOT_PROPOSED'}. A native pass covers only the frozen probes and declared protected suite; it does not certify the model-selected requirement.`,
 '**No automatic merge. No universal correctness or prospective superiority claim.**',
 `[Source snapshot, model proposals, usage, native logs and candidate patch](${run})`
 ].join('\n\n')}};
if(typeof process.env.GH_TOKEN!=='string'||process.env.GH_TOKEN.length<10)throw Error('REGISTERED_APP_TOKEN_REQUIRED');
const response=await fetch('https://api.github.com/repos/metalogiclabs/mathgraph/check-runs',{method:'POST',headers:{Authorization:`Bearer ${process.env.GH_TOKEN}`,Accept:'application/vnd.github+json','Content-Type':'application/json'},body:JSON.stringify(body),signal:AbortSignal.timeout(20000)});
if(!response.ok)throw Error('CHECK_PUBLISH_HTTP_'+response.status);
const c=await response.json();if(c.head_sha!==process.env.GITHUB_SHA||c.conclusion!=='neutral'||c.app?.id!==5308912||c.app?.slug!=='mathgraph-check')throw Error('PUBLISH_READBACK_MISMATCH');
await writeFile(`${dir}/published-check.json`,JSON.stringify({id:c.id,url:c.html_url,app:c.app.slug,head_sha:c.head_sha},null,2)+'\n');
console.log(JSON.stringify({id:c.id,url:c.html_url,app:c.app.slug}));
