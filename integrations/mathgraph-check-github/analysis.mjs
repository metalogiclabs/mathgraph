// Exact-source shared MathGraph Check advisory analyzer. No runtime/network/secret imports.
const REPO=/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
const SHA=/^[a-f0-9]{40}$/i;
const LIMIT=/\b([a-z][a-z0-9_]{2,79})\s*=\s*(UNKNOWN|NOT_TESTED|NOT_CHECKED)\b/g;
const TEST=/(^|\/)(test(s)?\/|[^/]*[._-](test|spec)\.[^/]+$)|_test\.go$/i;
const CODE=/\.(go|py|lean|rs|ts|tsx|js|jsx|java|c|cc|cpp|cs|sol)$/i;
export const VERSION="mathgraph.github-pr-evidence.v0";

export function analyze(s) {
  if (!s || !REPO.test(s.repository) || !Number.isSafeInteger(s.number) ||
      s.number<1 || !SHA.test(s.sha) || !Array.isArray(s.files) ||
      !Array.isArray(s.runs)) throw new Error("INVALID_PINNED_SNAPSHOT");
  const declared=new Map(), changed={code:0,test:0,workflow:0,files:s.files.length};
  for (const file of s.files) {
    const name=String(file.filename||"");
    if (name.startsWith(".github/workflows/")) changed.workflow++;
    else if (TEST.test(name)) changed.test++;
    else if (CODE.test(name)) changed.code++;
    for (const line of String(file.patch||"").split(/\r?\n/)) {
      if (!line.startsWith("+") || line.startsWith("+++")) continue;
      for (const m of line.slice(1).matchAll(LIMIT)) {
        declared.set(m[1].toLowerCase(),{name:m[1].toLowerCase(),state:m[2],
          source:name,authority:"AUTHOR_DECLARATION_ONLY"});
      }
    }
  }
  const latest=new Map();
  for (const r of s.runs) {
    if (!r || r.head_sha!==s.sha || !r.name ||
        /^(PR Format Validation|MathGraph Check(\s|\/|$))/i.test(r.name)) continue;
    const old=latest.get(r.name);
    if (!old || Number(r.id)>Number(old.id)) latest.set(r.name,r);
  }
  const current=[...latest.values()].map(r=>({
    name:r.name,run_id:r.id,status:r.status,conclusion:r.conclusion,
    head_sha:s.sha,url:"https://github.com/"+s.repository+"/actions/runs/"+r.id
  })).sort((a,b)=>String(a.name).localeCompare(String(b.name)));
  let ci="NO_SUBSTANTIVE_CI_AT_HEAD";
  if (s.ci_visibility!=="COMPLETE") ci="CI_VISIBILITY_UNKNOWN";
  else if (current.length && current.every(r=>r.status==="completed" && r.conclusion==="success"))
    ci="GITHUB_REPORTED_SUCCESS_AT_EXACT_HEAD";
  else if (current.length) ci="NOT_ALL_CURRENT_CI_GREEN";
  const limits=[...declared.values()].sort((a,b)=>a.name.localeCompare(b.name));
  let finding,action;
  if (s.files_visibility!=="COMPLETE") {
    finding="DIFF_SCOPE_INCOMPLETE";
    action="Fetch the complete changed-file list; this result cannot cover all changed lines.";
  } else if (ci==="NOT_ALL_CURRENT_CI_GREEN") {
    finding="CURRENT_HEAD_CI_UNRESOLVED";
    action="Inspect the failed or incomplete exact-head checks before promotion.";
  } else if (limits.length) {
    finding="DECLARED_VERIFICATION_RESIDUAL";
    action="Independently test "+limits.slice(0,3).map(x=>x.name).join(", ")+
      " at this exact source version; otherwise retain UNKNOWN.";
  } else if (ci!=="GITHUB_REPORTED_SUCCESS_AT_EXACT_HEAD") {
    finding="CURRENT_HEAD_CI_UNESTABLISHED";
    action="Obtain a substantive CI result for this exact PR head.";
  } else if (changed.code && !changed.test) {
    finding="TEST_DELTA_ABSENT";
    action="Check whether existing tests cover the change; no new test file is not proof of missing coverage.";
  } else {
    finding="BEHAVIORAL_SCOPE_UNKNOWN";
    action="Check the intended behavior against the actual tests; green CI alone is insufficient.";
  }
  return {
    schema:VERSION, authority:"ADVISORY_ONLY",
    source:{repository:s.repository,pr:s.number,sha:s.sha,
      url:"https://github.com/"+s.repository+"/pull/"+s.number},
    ci:{state:ci,exact_head_runs:current},changed,
    declared_limits:limits, finding:{code:finding,next_action:action},
    inputs:{files:s.files_visibility||"UNKNOWN",actions:s.ci_visibility||"UNKNOWN"},
    non_claims:["Green CI does not imply all claimed behavior was verified.",
      "An UNKNOWN marker is a source declaration, not an independent proof.",
      "No automated source-to-intent correctness or merge authority."]
  };
}

export function checkOutput(report) {
  const o=[
    "### "+report.finding.code,
    "**Next decisive action:** "+report.finding.next_action,
    "",
    "**Exact PR:** "+report.source.url,
    "**Head:** "+report.source.sha,
    "**CI:** "+report.ci.state,
    "",
    "**Source-declared open obligations (not independently verified):**"
  ];
  if (!report.declared_limits.length) o.push("- No explicit machine-readable added-line markers found.");
  for (const x of report.declared_limits.slice(0,20))
    o.push("- "+x.name+"="+x.state+" in "+x.source.replace(/[<>]/g,""));
  o.push("","**Exact-head CI runs:**");
  if (!report.ci.exact_head_runs.length) o.push("- None available.");
  for (const r of report.ci.exact_head_runs.slice(0,10))
    o.push("- "+String(r.name).replace(/[<>]/g,"")+": "+r.conclusion+
      " ([run]("+r.url+"))");
  o.push("","**Boundary:** ADVISORY_ONLY. CI conclusions and author declarations are not correctness proofs.");
  return {name:"MathGraph Check / evidence scope",status:"completed",
    conclusion:"neutral",output:{title:report.finding.code,summary:o.join("\n").slice(0,60000)}};
}

