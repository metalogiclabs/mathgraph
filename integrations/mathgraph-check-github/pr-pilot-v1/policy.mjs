// Hosted pilot policy is trusted release code; source PRs cannot edit it.
const SHA=/^[a-f0-9]{40}$/;const requireFact=(b,c)=>{if(!b)throw Error(c);};
const LEDGER=Object.freeze({path:'Scripts/Ledger.lean',module:'Scripts.Ledger',namespace:'Scripts.Ledger',cli_path:'Scripts/Main/CheckScriptsLedger.lean',cli_module:'Scripts.Main.CheckScriptsLedger',toolchain:'leanprover/lean4:v4.35.0',mode:'OWNED_FORK_PR_PILOT'});
export function profileFor(repository){requireFact(repository==='metalogiclabs/L4YAML','REPOSITORY_NOT_ENABLED');return {...LEDGER,repository};}
export function commandOf(body){return typeof body==='string'?body.trim().match(/^@MathGraph -(check|fix)$/)?.[1]??null:null;}
export function classifyDiff(files){
 const supported=Array.isArray(files)&&files.length===1&&files[0].filename===LEDGER.path&&files[0].status==='modified';
 return {supported,reason:supported?'SUPPORTED_LEDGER_MODULE':'UNSUPPORTED_CHANGED_FILE_SCOPE'};
}
export function admitRequest({repository,pr,comment,permission,files,filesComplete=true}){
 const profile=profileFor(repository),command=commandOf(comment?.body);
 requireFact(command&&Number.isSafeInteger(comment?.id)&&comment.id>0&&comment.user?.type==='User'&&Number.isSafeInteger(comment.user.id)&&comment.user.id>0&&/^[a-zA-Z0-9-]{1,39}$/.test(comment.user.login??''),'COMMAND_INVALID');
 requireFact(['write','maintain','admin'].includes(permission),'MAINTAINER_REQUIRED');
 requireFact(pr?.state==='open'&&Number.isSafeInteger(pr.number)&&pr.number>0&&SHA.test(pr.head?.sha??'')&&SHA.test(pr.base?.sha??''),'PR_INVALID');
 for(const side of ['head','base'])requireFact(pr[side].repo?.full_name===repository&&pr[side].repo?.private===false,'PUBLIC_SAME_REPOSITORY_REQUIRED');
 requireFact(filesComplete===true,'INCOMPLETE_CHANGED_FILES');
 return {schema:'mathgraph.pr-pilot.request.v1',repository,number:pr.number,head_sha:pr.head.sha,base_sha:pr.base.sha,command,comment_id:comment.id,actor_id:comment.user.id,actor_login:comment.user.login,profile,support:classifyDiff(files)};
}
const esc=x=>String(x??'').replace(/@/g,'&#64;').replace(/[\r\n`|<>]/g,' ');
export function formatResult(report,request,runURL){
 const names={NO_COUNTEREXAMPLE_IN_GENERATED_GUARDS:'No counterexample found in the generated probes',CANDIDATE_ASSERTION_FAILURE:'A generated probe fails on this revision',UNKNOWN:'Check incomplete',STALE:'Source changed — this result no longer applies'};
 const lines=['### MathGraph Check',`**${names[report.status]??'Evidence incomplete'}**`,`Revision: \`${request.head_sha}\` · Base: \`${request.base_sha}\``, 'Scope: selected ledger module, original guards and repository gate. This does not establish whole-PR correctness.'];
 if(report.original?.length){lines.push('| Probe | Head | Base |','|---|---|---|');for(const p of report.original)lines.push(`| ${esc(p.id)} | ${esc(p.execution)} | ${esc(report.base?.find(b=>b.id===p.id)?.execution??'not observed')} |`);}
 if(report.repair?.status==='PATCH_PASSES_FROZEN_GUARDS_AND_REPOSITORY_GATE')lines.push('**Candidate repair passes the frozen probes and protected gate.** Withdrawal reproduces the failures.');
 else if(report.repair?.status==='UNKNOWN')lines.push('Repair remains UNKNOWN; see retained diagnostics.');
 if(report.reason)lines.push('Reason: '+esc(report.reason));
 if(report.repair_pr&&new RegExp('^https://github.com/'+request.repository+'/pull/[1-9][0-9]*$').test(report.repair_pr))lines.push('[Review the draft repair]('+report.repair_pr+')');
 if(report.comparison?.length)lines.push('Base/head comparison: '+report.comparison.map(p=>esc(p.id)+': '+esc(p.change)).join('; '));
 lines.push('Model-inferred requirements remain unverified. Results are advisory; no automatic merge.',`[Execution and evidence](${runURL})`);
 return lines.join('\n\n');
}
