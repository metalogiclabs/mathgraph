import {formatReportIntegrity} from './report-integrity-view.mjs';
import {REPORT_METHOD,REPORT_PROFILE} from './report-integrity.mjs';
import {isFiniteMethod,finiteProfile} from './finite-methods.mjs';
import {formatGeneratorResult} from './generator-report.mjs';
import {GENERATOR_PROFILE,GENERATOR_METHOD} from './traceof-comments.mjs';
import {formatUnifiedResult,reportView} from './report-view.mjs';
import {claimProfileFor} from './claim-profile.mjs';
import {expectationProfileFor} from './expectations.mjs';
import {CLI_MODE,cliProfileFor} from './cli-profiles.mjs';
import {cliTitle,formatCliResult} from './cli-report.mjs';
import {CONTRACT_MODE,contractTitle,formatContractResult} from './repository-report.mjs';
// Hosted pilot policy is trusted release code; source PRs cannot edit it.
const SHA=/^[a-f0-9]{40}$/;const requireFact=(b,c)=>{if(!b)throw Error(c);};
const LEDGER=Object.freeze({path:'Scripts/Ledger.lean',module:'Scripts.Ledger',namespace:'Scripts.Ledger',cli_path:'Scripts/Main/CheckScriptsLedger.lean',cli_module:'Scripts.Main.CheckScriptsLedger',toolchain:'leanprover/lean4:v4.35.0',mode:'OWNED_FORK_PR_PILOT'});
export function profileFor(repository,method){requireFact(repository==='metalogiclabs/L4YAML','REPOSITORY_NOT_ENABLED');requireFact(method===undefined||isFiniteMethod(method),'METHOD_NOT_ENABLED');return {...(finiteProfile(method)??LEDGER),repository};}
export function modelReservationCents(r){
 if(!r.support?.supported||[CONTRACT_MODE,CLI_MODE].includes(r.profile?.mode))return 0;
 if(r.command==='check'&&(r.profile?.expectation_profile||r.profile?.expectation_candidate))return 0;
 if(isFiniteMethod(r.profile?.method)&&r.profile?.repair_template)return 0;
 return r.command==='check'?49:98;
}
export function commandOf(body){return typeof body==='string'?body.trim().match(/^@MathGraph -(check|fix)$/)?.[1]??null:null;}
export function classifyDiff(files){
 const supported=Array.isArray(files)&&files.length===1&&files[0].filename===LEDGER.path&&files[0].status==='modified';
 return {supported,reason:supported?'SUPPORTED_LEDGER_MODULE':'UNSUPPORTED_CHANGED_FILE_SCOPE'};
}
export function admitRequest({repository,pr,comment,permission,files,filesComplete=true,pilotOperators=[]}){
 const profile=profileFor(repository),command=commandOf(comment?.body);
 requireFact(command&&Number.isSafeInteger(comment?.id)&&comment.id>0&&comment.user?.type==='User'&&Number.isSafeInteger(comment.user.id)&&comment.user.id>0&&/^[a-zA-Z0-9-]{1,39}$/.test(comment.user.login??''),'COMMAND_INVALID');
 requireFact(['write','maintain','admin'].includes(permission)||Array.isArray(pilotOperators)&&pilotOperators.includes(comment.user.id)&&Array.isArray(files)&&(command==='check'||files.some(f=>[GENERATOR_PROFILE.path,REPORT_PROFILE.path].includes(f.filename)&&['added','modified'].includes(f.status))),'MAINTAINER_REQUIRED');
 requireFact(pr?.state==='open'&&Number.isSafeInteger(pr.number)&&pr.number>0&&SHA.test(pr.head?.sha??'')&&SHA.test(pr.base?.sha??''),'PR_INVALID');
 for(const side of ['head','base'])requireFact(pr[side].repo?.full_name===repository&&pr[side].repo?.private===false,'PUBLIC_SAME_REPOSITORY_REQUIRED');
 requireFact(filesComplete===true,'INCOMPLETE_CHANGED_FILES');
 const support=classifyDiff(files);
 if(!support.supported&&command==='check'&&Array.isArray(files)&&files.some(f=>/^(Scripts\/)([A-Za-z_][A-Za-z0-9_]*\/)*[A-Za-z_][A-Za-z0-9_]*\.lean$/.test(f.filename)&&['added','modified','removed','renamed','copied'].includes(f.status))){profile.mode=CONTRACT_MODE;support.supported=true;support.reason='SUPPORTED_REPOSITORY_CONTRACT';}
 const cli=command==='check'?cliProfileFor(files):null;if(cli){profile.mode=CLI_MODE;profile.cli_profile=cli.id;support.supported=true;support.reason='SUPPORTED_CLI_PARITY';}
 if(files.some(f=>f.filename===GENERATOR_PROFILE.path&&['added','modified'].includes(f.status))){Object.assign(profile,GENERATOR_PROFILE);support.supported=true;support.reason='SUPPORTED_FINITE_GENERATOR_COMMENTS';profile.expectation_profile=GENERATOR_METHOD;if(pr.head.sha==='1153d648425fb15f6fe49061544f7ffe4bdcb520'||files.some(f=>f.filename===GENERATOR_PROFILE.path&&f.sha==='9ed75df29bedd67dd14883be30409ca9b5959b95'))profile.repair_template='traceof-nested-depth-v1';}
 if(files.some(f=>f.filename===REPORT_PROFILE.path&&['added','modified'].includes(f.status))){Object.assign(profile,REPORT_PROFILE);support.supported=true;support.reason='SUPPORTED_FINITE_REPORT_INTEGRITY';profile.expectation_profile=REPORT_METHOD;profile.repair_template='junit-report-refusal-v1';}
 profile.report_version=isFiniteMethod(profile.method)?profile.method:'passport-v1';
 if(profile.mode===LEDGER.mode&&!isFiniteMethod(profile.method)){profile.report_version='expectations-v2-complete';const expectations=expectationProfileFor({repository,head_sha:pr.head.sha,profile});const locator=pr.user?.id===32909488&&pr.user.type==='User'&&pr.draft===true&&/https:\/\/github.com\/metalogiclabs\/mathgraph\/actions\/runs\/[1-9][0-9]*/.test(pr.body??'');if(expectations)profile.expectation_profile='ledger-shell-v2';else if(support.supported&&(pr.user?.id===342263476&&pr.user.type==='Bot'&&pr.user.login==='mathgraph-check[bot]'||locator)){profile.expectation_candidate=true;}else if(command==='fix'&&support.supported){support.supported=false;support.reason='REPAIR_EXPECTATION_REVIEW_REQUIRED';}}
 if(!['write','maintain','admin'].includes(permission)&&!isFiniteMethod(profile.method)){support.supported=false;support.reason='UNSUPPORTED_CHANGED_FILE_SCOPE';}
 const claim=claimProfileFor({repository,command,base_sha:pr.base.sha,head_sha:pr.head.sha,profile});if(claim)profile.claim_profile=claim.id;
 return {schema:'mathgraph.pr-pilot.request.v1',repository,number:pr.number,head_sha:pr.head.sha,base_sha:pr.base.sha,command,comment_id:comment.id,actor_id:comment.user.id,actor_login:comment.user.login,actor_authorization:['write','maintain','admin'].includes(permission)?'REPOSITORY_MAINTAINER':'PILOT_OPERATOR',profile,support,changed_paths:files.map(f=>f.filename)};
}
const esc=x=>String(x??'').replace(/@/g,'&#64;').replace(/[\r\n`|<>]/g,' ');
const REPAIR_VERIFIED='PATCH_PASSES_FROZEN_GUARDS_AND_REPOSITORY_GATE';
export function resultTitle(report,request){return reportView(report,request).title;}
export function formatResult(report,request,runURL){return formatUnifiedResult(report,request,runURL,formatLegacyResult(report,request,runURL));}
function formatLegacyResult(report,request,runURL){
 if(request.profile?.method===REPORT_METHOD)return formatReportIntegrity(report,request,runURL);
 if(request.profile?.method===GENERATOR_METHOD)return formatGeneratorResult(report,request,runURL);
 if(request.profile?.mode===CLI_MODE)return formatCliResult(report,request,runURL);
 if(request.profile?.mode===CONTRACT_MODE)return formatContractResult(report,request,runURL);
 if(report.status==='UNKNOWN'&&report.reason==='UNSUPPORTED_CHANGED_FILE_SCOPE')return ['### MathGraph Check','**No reviewed checking contract for this change**',`PR: [${request.repository}#${request.number}](https://github.com/${request.repository}/pull/${request.number})`, 'No native result is claimed. Whole-PR correctness: UNKNOWN.', 'Next: review these changes using the repository’s normal process, or define a reviewed contract for this source category. Do not split the PR merely to obtain a passing Check.', 'Available scope: selected Scripts modules with fixed regressions; generated check/fix is limited to `Scripts/Ledger.lean`. Proof intent, documentation correctness and arbitrary workflows remain unchecked.', 'Changed paths: '+(request.changed_paths??[]).map(esc).join(', '), `[Execution and evidence](${runURL})`].join('\n\n');
 const names={NO_COUNTEREXAMPLE_IN_GENERATED_GUARDS:'No counterexample found in the generated probes',CANDIDATE_ASSERTION_FAILURE:'A generated probe fails on this revision',UNKNOWN:'Check incomplete',STALE:'Source changed — this result no longer applies'};
 const repaired=report.status==='CANDIDATE_ASSERTION_FAILURE'&&report.expectations?.status==='ADMITTED'&&report.expectations.repair_eligible===true&&report.repair?.status===REPAIR_VERIFIED;
 const lines=['### MathGraph Check',`PR: [${request.repository}#${request.number}](https://github.com/${request.repository}/pull/${request.number})`,`**${repaired?resultTitle(report,{...request,command:'fix'}):report.expectations?.status==='ADMITTED'?resultTitle(report,request):names[report.status]??'Evidence incomplete'}**`,`Revision: \`${request.head_sha}\` · Base: \`${request.base_sha}\``, 'Scope: selected ledger module, original guards and repository gate. This does not establish whole-PR correctness.'];
 const headQualified=['CANDIDATE_ASSERTION_FAILURE','NO_COUNTEREXAMPLE_IN_GENERATED_GUARDS'].includes(report.status)&&report.head_complete!==false&&report.baseline?.complete!==false;
 const execution={GUARD_PASSED:'Pass',CANDIDATE_ASSERTION_FAILURE:'Fail (reproduced)',UNKNOWN:'Unknown'};
 const changes={PRE_EXISTING_FAILURE:'Present before this PR',NEW_FAILURE:'Introduced by this PR',RESOLVED_FAILURE:'Resolved by this PR',BOTH_PASS:'Pass on both revisions',BASE_UNKNOWN:'Base not qualified',HEAD_UNKNOWN:'Head not qualified'};
 if(report.original?.length){const table=['| Probe | Expectation | Head | Base | Comparison |','|---|---|---|---|---|'];for(const p of report.original){const base=report.base?.find(b=>b.id===p.id),comparison=report.comparison?.find(b=>b.id===p.id),admission=report.expectations?.probes?.find(b=>b.id===p.id)?.status??'UNKNOWN';table.push(`| ${esc(p.id)} | ${esc(admission)} | ${headQualified?(execution[p.execution]??'Unknown'):'Unknown'} | ${execution[base?.execution]??'Not observed'} | ${headQualified?(changes[comparison?.change]??'Not established'):'Head not qualified'} |`);}lines.push(table.join('\n'));}
 if(repaired)lines.push(`The candidate passes the frozen probes${Number.isSafeInteger(report.repair.protected_guards)?`, preserves ${report.repair.protected_guards} original guards`:''} and passes the repository gate. Withdrawal reproduces the original failures.`);
 else if(report.repair?.status==='UNKNOWN')lines.push('Repair remains UNKNOWN; see retained diagnostics.');
 if(report.reason)lines.push('Reason: '+esc(report.reason));if(report.expectation_review_reason)lines.push(esc(report.expectation_review_reason));
 if(report.repair_pr&&new RegExp('^https://github.com/'+request.repository+'/pull/[1-9][0-9]*$').test(report.repair_pr))lines.push('[Review the draft repair]('+report.repair_pr+')');
 if(report.status==='UNKNOWN'&&report.reason==='UNSUPPORTED_CHANGED_FILE_SCOPE')lines.push('Next: this pilot checks PRs modifying only `Scripts/Ledger.lean`. Split out that change or request a separately reviewed capability for the other files.');
 else if(report.reason==='REPAIR_EXPECTATION_REVIEW_REQUIRED'||headQualified&&report.expectations?.status!=='ADMITTED')lines.push('Next: review expected behavior against an independent requirement and reference. An unadmitted expectation cannot authorize repair.');
 else if(report.status==='UNKNOWN')lines.push(`Next: inspect the retained diagnostics. A repository maintainer can retry with \`${request.command==='fix'&&report.reason!=='RUN_CHECK_BEFORE_FIX'?'@MathGraph -fix':'@MathGraph -check'}\` after the missing evidence or execution problem is resolved.`);
 else if(report.status==='STALE')lines.push('Next: use the Check for the current revision; historical evidence below does not authorize the changed source.');
 else if(repaired)lines.push('Next: review the expected behavior and draft diff before deciding whether to merge.');
 else if(report.status==='CANDIDATE_ASSERTION_FAILURE'&&request.command==='check')lines.push('Next: review each probe’s expected behavior. If it is intended, comment `@MathGraph -fix` to test a candidate repair against these same frozen probes.');
 lines.push(report.expectations?.status==='ADMITTED'?(report.expectations.expectation_set==='ledger-shell-v2'?'The three finite requirements cover five inputs and are operator-adopted and independently replayed. Customer approval remains UNKNOWN. Results are advisory; no automatic merge.':'The two finite expectations are operator-adopted and independently replayed. Other model-inferred requirements remain unverified. Results are advisory; no automatic merge.'):'Model-inferred requirements remain unverified. Results are advisory; no automatic merge.',`[Execution and evidence](${runURL})`);
 return lines.join('\n\n');
}
