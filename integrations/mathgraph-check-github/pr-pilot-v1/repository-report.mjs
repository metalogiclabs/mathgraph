export const CONTRACT_MODE='OWNED_FORK_REPOSITORY_CONTRACT';
export function contractTitle(report){return ({NO_FAILURE_IN_FROZEN_CORPUS:'Frozen regression checks pass',NEW_FROZEN_PROBE_FAILURE:'Frozen regression introduced',RESOLVED_FROZEN_PROBE_FAILURE:'Frozen regression resolved',FAILURE_ON_BOTH_REVISIONS:'Frozen probes fail on both revisions'})[report.status]??'Check incomplete';}
export function formatContractResult(report,request,runURL){
 const esc=x=>String(x??'').replace(/@/g,'&#64;').replace(/[\r\n`|<>]/g,' ');
 const lines=['### MathGraph Check',`PR: [${request.repository}#${request.number}](https://github.com/${request.repository}/pull/${request.number})`,`**${report.status==='STALE'?'Source changed — recheck required':contractTitle(report)}**`,`Revision: \`${request.head_sha}\` · Base: \`${request.base_sha}\``,
 'Requested scope: compile selected Scripts modules and transitive imports under a trusted build, then replay the unchanged 1,367-case regression corpus on both revisions. Only admitted evidence below establishes completed coverage. Whole-PR correctness: UNKNOWN.'];
 if(report.coverage&&contractTitle(report)!=='Check incomplete'&&report.status!=='STALE'){
  const c=report.coverage;lines.push(['| Native evidence | Base | Head |','|---|---|---|',`| Frozen probes passed | ${c.base.passed}/${c.base.cases} | ${c.head.passed}/${c.head.cases} |`,`| Compiled modules | ${c.base.compiled_modules.length} | ${c.head.compiled_modules.length} |`].join('\n'));
  for(const side of ['base','head'])lines.push(`Compiled roots (${side}): ${c[side].compiled_roots.map(p=>'`'+esc(p)+'`').join(', ')}`);
  for(const [key,label]of [['introduced','New failing witnesses'],['resolved','Resolved witnesses'],['inherited','Failing on both revisions']])if(report[key]?.length)lines.push(label+': '+report[key].slice(0,100).map(esc).join(', ')+(report[key].length>100?' (full list in evidence)':''));
  lines.push('Uncovered changed paths: '+(c.uncovered.length?c.uncovered.map(p=>'`'+esc(p)+'`').join(', '):'none outside the selected module scope.'));
  if(c.deleted_modules.length)lines.push('Removed/moved base modules retained in base evidence: '+c.deleted_modules.map(esc).join(', '));
 }
 if(report.reason)lines.push('Reason: '+esc(report.reason));
 lines.push('Uncovered obligations: intended theorem claims, new CLI runtime/parity behavior, scientific semantics and original project-wide gates. Compilation and finite regression evidence do not establish these obligations.',
  report.status==='STALE'?'Next: consult the Check for the current revision. Historical evidence does not authorize changed source.':report.status==='UNKNOWN'?'Next: inspect retained diagnostics and retry `@MathGraph -check` after resolving the missing evidence.':'Next: review any failing witnesses and the uncovered obligations. This contract does not generate a repair.',
  'Finite prior-behavior expectations are candidate regression requirements, not authority on intended semantics. Advisory only; no automatic merge.',`[Execution and evidence](${runURL})`);
 return lines.join('\n\n');
}
