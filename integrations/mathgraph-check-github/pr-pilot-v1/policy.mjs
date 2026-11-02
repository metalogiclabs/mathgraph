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
const REPAIR_VERIFIED='PATCH_PASSES_FROZEN_GUARDS_AND_REPOSITORY_GATE';
export function resultTitle(report,request){
 if(report.status==='STALE')return 'Source changed — recheck required';
 if(request.command==='fix')return report.status==='CANDIDATE_ASSERTION_FAILURE'&&report.repair?.status===REPAIR_VERIFIED?'Candidate repair verified on frozen probes':'Repair incomplete';
 return report.status==='UNKNOWN'?'Check incomplete':report.status==='CANDIDATE_ASSERTION_FAILURE'?'Generated probe failure reproduced':report.status==='NO_COUNTEREXAMPLE_IN_GENERATED_GUARDS'?'No counterexample in generated probes':'Check incomplete';
}
export function formatResult(report,request,runURL){
 const names={NO_COUNTEREXAMPLE_IN_GENERATED_GUARDS:'No counterexample found in the generated probes',CANDIDATE_ASSERTION_FAILURE:'A generated probe fails on this revision',UNKNOWN:'Check incomplete',STALE:'Source changed — this result no longer applies'};
 const repaired=report.status==='CANDIDATE_ASSERTION_FAILURE'&&report.repair?.status===REPAIR_VERIFIED;
 const lines=['### MathGraph Check',`**${repaired?resultTitle(report,{...request,command:'fix'}):names[report.status]??'Evidence incomplete'}**`,`Revision: \`${request.head_sha}\` · Base: \`${request.base_sha}\``, 'Scope: selected ledger module, original guards and repository gate. This does not establish whole-PR correctness.'];
 const headQualified=['CANDIDATE_ASSERTION_FAILURE','NO_COUNTEREXAMPLE_IN_GENERATED_GUARDS'].includes(report.status)&&report.head_complete!==false&&report.baseline?.complete!==false;
 const execution={GUARD_PASSED:'Pass',CANDIDATE_ASSERTION_FAILURE:'Fail (reproduced)',UNKNOWN:'Unknown'};
 const changes={PRE_EXISTING_FAILURE:'Present before this PR',NEW_FAILURE:'Introduced by this PR',RESOLVED_FAILURE:'Resolved by this PR',BOTH_PASS:'Pass on both revisions',BASE_UNKNOWN:'Base not qualified',HEAD_UNKNOWN:'Head not qualified'};
 if(report.original?.length){const table=['| Probe | Head | Base | Comparison |','|---|---|---|---|'];for(const p of report.original){const base=report.base?.find(b=>b.id===p.id),comparison=report.comparison?.find(b=>b.id===p.id);table.push(`| ${esc(p.id)} | ${headQualified?(execution[p.execution]??'Unknown'):'Unknown'} | ${execution[base?.execution]??'Not observed'} | ${headQualified?(changes[comparison?.change]??'Not established'):'Head not qualified'} |`);}lines.push(table.join('\n'));}
 if(repaired)lines.push(`The candidate passes the frozen probes${Number.isSafeInteger(report.repair.protected_guards)?`, preserves ${report.repair.protected_guards} original guards`:''} and passes the repository gate. Withdrawal reproduces the original failures.`);
 else if(report.repair?.status==='UNKNOWN')lines.push('Repair remains UNKNOWN; see retained diagnostics.');
 if(report.reason)lines.push('Reason: '+esc(report.reason));
 if(report.repair_pr&&new RegExp('^https://github.com/'+request.repository+'/pull/[1-9][0-9]*$').test(report.repair_pr))lines.push('[Review the draft repair]('+report.repair_pr+')');
 if(report.status==='UNKNOWN'&&report.reason==='UNSUPPORTED_CHANGED_FILE_SCOPE')lines.push('Next: this pilot checks PRs modifying only `Scripts/Ledger.lean`. Split out that change or request a separately reviewed capability for the other files.');
 else if(report.status==='UNKNOWN')lines.push(`Next: inspect the retained diagnostics. A repository maintainer can retry with \`${request.command==='fix'&&report.reason!=='RUN_CHECK_BEFORE_FIX'?'@MathGraph -fix':'@MathGraph -check'}\` after the missing evidence or execution problem is resolved.`);
 else if(report.status==='STALE')lines.push('Next: use the Check for the current revision; historical evidence below does not authorize the changed source.');
 else if(repaired)lines.push('Next: review the expected behavior and draft diff before deciding whether to merge.');
 else if(report.status==='CANDIDATE_ASSERTION_FAILURE'&&request.command==='check')lines.push('Next: review each probe’s expected behavior. If it is intended, comment `@MathGraph -fix` to test a candidate repair against these same frozen probes.');
 lines.push('Model-inferred requirements remain unverified. Results are advisory; no automatic merge.',`[Execution and evidence](${runURL})`);
 return lines.join('\n\n');
}
