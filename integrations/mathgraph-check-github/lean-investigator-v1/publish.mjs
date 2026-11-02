import {readFile,writeFile} from 'node:fs/promises';
const dir=process.argv[2]??'lean-investigation',r=JSON.parse(await readFile(`${dir}/assessment.json`,'utf8'));
if(r.context.verifier_sha!==process.env.GITHUB_SHA||r.context.run_id!==Number(process.env.GITHUB_RUN_ID))throw Error('STALE_ASSESSMENT');
const run=`https://github.com/metalogiclabs/mathgraph/actions/runs/${process.env.GITHUB_RUN_ID}`;
const rows=(r.original??[]).map(p=>`| ${p.id} | ${p.execution} | ${r.repair?.repaired?.find(x=>x.id===p.id)?.execution??'not proposed'} | ${r.repair?.withdrawn?.find(x=>x.id===p.id)?.execution??'not run'} |`).join('\n');
const body={name:'MathGraph Check / generated Lean audit',head_sha:process.env.GITHUB_SHA,status:'completed',conclusion:'neutral',details_url:run,external_id:'lean-investigator-v1:'+process.env.GITHUB_SHA,output:{title:'MathGraph Check: '+(r.repair?.status&&r.repair.status!=='NOT_PROPOSED'?r.repair.status:r.status),summary:[
 '**Advisory retrospective source audit. Probes and localized edits were model-generated; native compilation is separate.**',
 r.subject?`Watched source: ${r.subject.repository}@${r.subject.head_sha}, ${r.subject.path}. The Check is attached to the investigator commit, not the watched repository.`:'Source acquisition incomplete.',
 '| Generated guard | Original | Model repair | Withdrawal |\n|---|---|---|---|\n'+rows,
 `Repair qualification: ${r.repair?.status??'NOT_PROPOSED'}. Original protected guards: ${r.repair?.protected_guards??r.source_guard_count??'see native logs'}. Repository gate exit codes: ${JSON.stringify(r.repair?.repository_gate_exits??[r.original_repository_gate_exit])}.`,
 `Reason: ${String(r.reason??r.scope??'see receipts').replace(/[`\r\n]/g,' ').slice(0,800)}`,
 '**Meaning remains UNVERIFIED. This tests a selected module/CLI and its repository gate, not the full L4YAML library, arbitrary shell extraction, a blind discovery benchmark or merge approval.**',
 `[Generated probes, native receipts, model patch, token usage and source identities](${run})`
 ].join('\n\n')}};
if(typeof process.env.GH_TOKEN!=='string'||process.env.GH_TOKEN.length<10)throw Error('REGISTERED_APP_TOKEN_REQUIRED');
const response=await fetch('https://api.github.com/repos/metalogiclabs/mathgraph/check-runs',{method:'POST',headers:{Authorization:`Bearer ${process.env.GH_TOKEN}`,Accept:'application/vnd.github+json','Content-Type':'application/json'},body:JSON.stringify(body),signal:AbortSignal.timeout(20000)});
if(!response.ok)throw Error('PUBLISH_HTTP_'+response.status);const c=await response.json();
if(c.head_sha!==process.env.GITHUB_SHA||c.app?.id!==5308912||c.app?.slug!=='mathgraph-check'||c.conclusion!=='neutral')throw Error('REGISTERED_APP_READBACK_MISMATCH');
await writeFile(`${dir}/published-check.json`,JSON.stringify({id:c.id,url:c.html_url,app:c.app.slug,head_sha:c.head_sha},null,2)+'\n');console.log(JSON.stringify({id:c.id,url:c.html_url}));
