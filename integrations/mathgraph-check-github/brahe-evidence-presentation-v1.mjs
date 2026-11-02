// Neutral preview only; no GitHub Check API side effects.
const SHA=/^[a-f0-9]{40}$/;
const short=s=>SHA.test(s??'')?s.slice(0,12):'UNKNOWN';
const safe=x=>String(x??'').replaceAll('&','&amp;').replaceAll('<','&lt;')
  .replaceAll('>','&gt;').replaceAll('@','＠')
  .replace(/([\\`*_{}\[\]()#+.!|>~-])/g,'\\$1').replace(/[\r\n]+/g,' ');

export function renderBraheEvidenceV1(verdict,ciSnapshot=null) {
  const status=verdict?.status==='CANDIDATE_BOUNDED'&&verdict?.evidence?'CANDIDATE_BOUNDED':'UNKNOWN';
  const base=verdict?.source?.baseSha,head=verdict?.source?.headSha;
  const lines=[
    '### MathGraph Check · Brahe event direction (retrospective)',
    `**${status} · ADVISORY_ONLY**`,
    '',
    'Brahe maintainer confirmed the underlying bug and merged Heath’s #608 fix. This is external acceptance of the upstream fix, not external use of MathGraph Check.',
    '',
    `- **Base:** \`${short(base)}\`; **fixed head:** \`${short(head)}\`.`,
    '- **Bounded question:** can a direction-specific detector falsely accept an opposite-direction endpoint near the target?',
  ];
  if (status==='CANDIDATE_BOUNDED') {
    lines.push(`- **Native candidate:** ${safe(verdict.evidence.base?.regressionCount)}/${safe(verdict.evidence.base?.testCount)} expected wrong-direction tests failed on the base; ${safe(verdict.evidence.head?.testCount)} tests passed on the fixed head.`);
    lines.push('- These claims require independent replay-artifact and GitHub metadata readback before any verified label.');
  } else {
    lines.push('- **Native result:** UNKNOWN; no qualifying before/after observation is available.');
  }
  lines.push('', '**Other CI (separate context):**');
  if (ciSnapshot&&ciSnapshot.headSha!==head) {
    lines.push('- CI_HEAD_MISMATCH: checks from another revision are not current.');
  } else if (Array.isArray(ciSnapshot?.checks)&&ciSnapshot.checks.length) {
    for(const check of ciSnapshot.checks.slice(0,20))
      lines.push(`- ${safe(check.name)}: ${safe(check.conclusion??'pending')}`);
  } else lines.push('- No head-matched CI supplied.');
  lines.push('', '**Open boundaries:**');
  for(const unknown of verdict?.unknowns??['EVIDENCE_INCOMPLETE_OR_MISMATCHED']) {
    lines.push(/^[A-Z][A-Z0-9_]{1,100}$/.test(unknown)?`- \`${unknown}\``:`- ${safe(unknown)}`);
  }
  lines.push('', 'Informational only. External Check adoption, comparison to competent review, and general release safety remain unmeasured.');
  const markdown=lines.join('\n');
  return {markdown,checkOutput:{
    name:'MathGraph Check / Brahe endpoint retrospective',status:'completed',conclusion:'neutral',
    output:{title:`Brahe event direction: ${status}`,summary:markdown}
  }};
}
