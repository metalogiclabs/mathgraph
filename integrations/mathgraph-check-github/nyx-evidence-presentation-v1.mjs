// Render a neutral preview for human review. This module does not post a Check.
// A CANDIDATE_BOUNDED verdict is not equivalent to authenticated CI evidence.
const FULL_SHA = /^[0-9a-f]{40}$/;

function safe(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('@', '＠')
    .replace(/([\\`*_{}\[\]()#+.!|>~-])/g, '\\$1')
    .replace(/[\r\n]+/g, ' ');
}

function shortSha(sha) {
  return FULL_SHA.test(sha ?? '') ? sha.slice(0, 12) : 'UNKNOWN';
}

export function renderNyxEvidenceV1(verdict, githubCiSnapshot = null) {
  const status = verdict?.status === 'CANDIDATE_BOUNDED' ? 'CANDIDATE_BOUNDED' : 'UNKNOWN';
  const authority = 'ADVISORY_ONLY';
  const base = verdict?.source?.baseSha;
  const head = verdict?.source?.headSha;
  const lines = [
    `### MathGraph Check / Nyx event-frame retrospective`,
    `**${status} · ${authority}**`,
    '',
    'A first-party, retrospective test of Nyx #613. It does not establish that MathGraph discovered the defect, reviewed it independently, or outperformed a maintainer.',
    '',
    `- **Scope:** one Earth-fixed longitude event regression; not a general Rust correctness result.`,
    `- **Base:** \`${shortSha(base)}\` · **PR head:** \`${shortSha(head)}\`.`,
    `- **Pinned regression blob:** \`${shortSha(verdict?.source?.testBlobSha)}\`.`,
  ];

  if (status === 'CANDIDATE_BOUNDED' && verdict.evidence) {
    lines.push(`- **Base observation:** ${safe(verdict.evidence.base?.regressionMarker ?? verdict.evidence.base?.reason ?? 'UNKNOWN')}; **head:** ${safe(verdict.evidence.head?.reason ?? 'UNKNOWN')}.`);
    if (verdict.evidence.runner?.workflowRunUrl && /^https:\/\/github\.com\/metalogiclabs\/mathgraph\/actions\/runs\/[1-9]\d*$/.test(verdict.evidence.runner.workflowRunUrl)) {
      lines.push(`- **Proposed replay:** ${verdict.evidence.runner.workflowRunUrl} (run and artifact authenticity still require independent readback).`);
    }
  } else {
    lines.push('- **Observation:** UNKNOWN; required evidence is absent or mismatched.');
  }

  lines.push('', '**Other CI (context, not MathGraph verification):**');
  if (githubCiSnapshot && githubCiSnapshot.headSha !== head) {
    lines.push('- CI_HEAD_MISMATCH: no checks from a different commit are treated as current.');
  } else if (Array.isArray(githubCiSnapshot?.checks) && githubCiSnapshot.checks.length) {
    for (const check of githubCiSnapshot.checks.slice(0, 20)) {
      lines.push(`- ${safe(check.name)}: ${safe(check.conclusion ?? 'pending')}`);
    }
    if (githubCiSnapshot.checks.length > 20) lines.push('- Further checks omitted from this preview.');
  } else {
    lines.push('- No head-matched CI snapshot supplied.');
  }

  lines.push('', '**Open evidence boundaries:**');
  for (const unknown of verdict?.unknowns ?? ['EVIDENCE_INCOMPLETE_OR_MISMATCHED']) {
    lines.push(/^[A-Z][A-Z0-9_]{1,100}$/.test(unknown) ? `- \`${unknown}\`` : `- ${safe(unknown)}`);
  }
  lines.push('', 'Informational only. No merge approval, certification, customer use, or external adoption is implied.');
  const markdown = lines.join('\n');
  return {
    markdown,
    checkOutput: {
      name: 'MathGraph Check / Nyx event-frame research',
      status: 'completed',
      conclusion: 'neutral',
      output: { title: `Nyx event-frame: ${status}`, summary: markdown }
    }
  };
}
