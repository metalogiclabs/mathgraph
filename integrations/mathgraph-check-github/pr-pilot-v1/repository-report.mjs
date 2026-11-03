export const CONTRACT_MODE='OWNED_FORK_REPOSITORY_CONTRACT';
const esc=x=>String(x??'').replace(/@/g,'&#64;').replace(/[\r\n`|<>]/g,' ').slice(0,2000);
export function contractTitle(report){
 if(report.status==='STALE')return 'Source changed — recheck required';
 if(report.status!=='UNKNOWN'&&report.introduced?.length)return 'Frozen regression introduced';
 return ({NO_FAILURE_IN_FROZEN_CORPUS:'Frozen regression checks pass',NEW_FROZEN_PROBE_FAILURE:'Frozen regression introduced',RESOLVED_FROZEN_PROBE_FAILURE:'Frozen regression resolved',FAILURE_ON_BOTH_REVISIONS:'Frozen probes fail on both revisions'})[report.status]??'Check incomplete';
}
export function diagnosticText(report){
 const lines=[],d=report.diagnostics??{};
 if(/403.*rate limit|rate limit exceeded/i.test(d.setup??''))lines.push('GitHub API rate limit prevented source metadata acquisition. No native comparison was admitted.');
 else if(d.setup)lines.push('The checking setup did not complete; retained diagnostics explain the acquisition failure.');
 for(const side of ['base','head']){const reason=d[side]?.reason??'',missing=reason.match(/EXPECTED_MODULE_ABSENT:([A-Za-z0-9_.]+)/);
  if(missing)lines.push(`The ${side} revision lacks required regression module \`${missing[1]}\`; this fixed corpus cannot compare that revision.`);
  else if(reason.includes('SOURCE_BUILD_FAILED'))lines.push(`The selected ${side} source did not compile under the trusted build. See the native build log.`);
  else if(reason)lines.push(`The ${side} native evidence is incomplete; see retained diagnostics.`);
 }
 for(const side of ['base','head'])if(report.observations?.[side])lines.push(`${side==='head'?'Head':'Base'} revision independently passed ${report.observations[side].passed}/${report.observations[side].cases} frozen probes; the PR comparison remains unavailable.`);
 if(report.status==='UNKNOWN')lines.push('This is not a confirmed PR regression. Whole-PR correctness remains UNKNOWN.');
 return lines;
}
export function formatContractResult(report,request,runURL){
 const good=report.coverage&&report.status!=='UNKNOWN'&&report.status!=='STALE',c=good?report.coverage:null;
 const lines=['### MathGraph Check',`**${contractTitle(report)}**`,`[${request.repository}#${request.number}](https://github.com/${request.repository}/pull/${request.number}) · revision \`${request.head_sha.slice(0,12)}\``];
 if(c){
  lines.push(`${report.introduced?.length??0} new failing frozen expectations; ${report.resolved?.length??0} resolved; ${report.inherited?.length??0} failing on both revisions. Head: ${c.head.passed}/${c.head.cases} frozen probes passed.`);
  for(const w of highlightedWitnesses(report)){
   const recovered=report.resolved?.includes(w.id),revision=recovered?request.base_sha:request.head_sha;
   const link=`https://github.com/${request.repository}/blob/${revision}/${w.path}`;
   lines.push(`**${recovered?'Resolved expectation (failed at base)':'Failed expectation'} \`${esc(w.id)}\`** — [${esc(w.path)}](${link})\n\nInput: \`${esc(JSON.stringify(w.inputs))}\`\n\nExpectation: \`${esc(w.expression)} == ${esc(w.expected)}\`. Native assertion failure is retained; runtime value not recorded.`);
  }
  if(!report.witnesses?.length)for(const [key,label]of [['introduced','New failing witnesses'],['resolved','Resolved witnesses'],['inherited','Failing on both revisions']])if(report[key]?.length)lines.push(label+': '+report[key].slice(0,20).map(esc).join(', '));
 }else lines.push(...diagnosticText(report));
 const action=nextAction(report);
 lines.push(action,'**Review boundary:** selected Scripts compilation and a fixed prior-behavior corpus only. Whole-PR correctness: UNKNOWN. Intended theorem claims, new CLI runtime/parity behavior and original project-wide gates remain unchecked.',`[Execution and evidence](${runURL})`);
 const details=[`Base: \`${request.base_sha}\` · Head: \`${request.head_sha}\``, 'Requested scope: selected Scripts modules and transitive imports, plus the unchanged 1,367-case frozen regression corpus on both revisions. Prior-behavior expectations are candidate regression requirements, not authority on intended semantics.'];
 if(c){
  details.push(['| Native evidence | Base | Head |','|---|---|---|',`| Frozen probes passed | ${c.base.passed}/${c.base.cases} | ${c.head.passed}/${c.head.cases} |`,`| Compiled modules | ${c.base.compiled_modules.length} | ${c.head.compiled_modules.length} |`].join('\n'));
  for(const side of ['base','head'])details.push(`Compiled roots (${side}): ${c[side].compiled_roots.map(p=>'`'+esc(p)+'`').join(', ')}`);
  for(const [key,label]of [['introduced','All new failing witnesses'],['resolved','All resolved witnesses'],['inherited','All inherited failing witnesses']])if(report[key]?.length)details.push(label+': '+report[key].map(esc).join(', '));
  details.push('Uncovered changed paths: '+(c.uncovered.length?c.uncovered.map(p=>'`'+esc(p)+'`').join(', '):'none outside selected modules.'));
  if(c.deleted_modules?.length)details.push('Removed/moved base modules retained in base evidence: '+c.deleted_modules.map(esc).join(', '));
 }
 if(!c&&report.declared_scope?.uncovered?.length)details.push('Uncovered changed paths: '+report.declared_scope.uncovered.map(esc).join(', '));
 if(report.reason)details.push('Reason: '+esc(report.reason));
 details.push('Uncovered obligations: proof intent, CLI runtime semantics and scientific claims. Results are advisory; no automatic merge.');
 lines.push('<details>\n<summary>Evidence, coverage and limits</summary>\n\n'+details.join('\n\n')+'\n\n</details>');
 return lines.join('\n\n');
}

export function nextAction(report){
 return report.status==='STALE'?'Next: consult the current revision’s Check; applicability of this historical result is withdrawn.':report.status==='UNKNOWN'?'Next: inspect the reported missing module or setup failure. Retry only after that blocker is resolved; no source repair is justified by this result.':report.introduced?.length?'Next: review the failed expectation against intended behavior, then inspect the linked source. Repair generation is not enabled for this contract.':report.resolved?.length?'Next: review the recovered expectation and the remaining unchecked obligations.':'Next: review the unchecked proof and CLI obligations before deciding whether to merge.';
}

export function highlightedWitnesses(report){
 const rank=w=>report.introduced?.includes(w.id)?0:report.resolved?.includes(w.id)?1:2;
 return [...(report.witnesses??[])].sort((a,b)=>rank(a)-rank(b)).slice(0,3);
}
