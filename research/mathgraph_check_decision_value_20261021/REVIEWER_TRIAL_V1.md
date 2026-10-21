# MathGraph Check — external reviewer decision-value trial (2026-10-21)

## Decision gate
**UNKNOWN / NOT EXECUTED.** This is a preregistered trial, not evidence of reviewer-time savings. Previous source-native go-yaml PR #958 is an **exposed calibration** target and CANNOT establish prospective superiority.

## Objective
Determine whether an evidence-scoped MathGraph Check presentation helps a competent reviewer make the same or a more correct consequential decision with less total investigation time than conventional GitHub + CI + provenance metadata, with *identical information rights*.

## Frozen reference calibration (not scored)
- External subject: `goccy/go-yaml` PR #958; base `edee2f91616c6d73112a13e7c0dbde72ce938877`; head `a34b94ecb553bb5a693296c30232a89026db79ca`.
- Pinned report: `heathsanchez/test@20864090c084efc0511cffcf47aae556b4003fea:research/mathgraph_pr958_one_finding_20261015/ONE_FINDING_REPORT.json`.
- Native PR run: https://github.com/heathsanchez/test/actions/runs/38559572638 (130-case matrix); repair: https://github.com/heathsanchez/test/actions/runs/38560167831; independent follow-up: https://github.com/heathsanchez/test/actions/runs/38560825707.
- Real result: 69 repaired, 0 introduced regressions in declared matrix, 20 inherited failures; separate issue #872, repaired 20→0→20 by isolated native patch/ablation. Correct scope-limited action is not to block #958 solely for inherited issue #872. Original native suite pass is not general merge approval.
- First-party live Check that displays the evidence: https://github.com/metalogiclabs/go-ethereum/runs/115974666180. The carrier PR is NOT the studied repository.
- Existing equal-information graph ledger regression has **TIED** MathGraph over all 16 receipt configurations in https://github.com/metalogiclabs/mathgraph/actions/runs/39528298334.

## Prospective scored target selection
**Do not use #958, Geth V19, goldmark-meta PR #8, gookit/config PR #225, or any source opened in previous experiments.**
Before reading PR body/diff/source, freeze in a separate commit:
- repository, base/head SHAs and all external authority identities;
- one source-native consequence method and its calibration controls;
- a competent equal-information baseline, same tools and time budget;
- an objective independently replayable oracle, including UNKNOWN outcomes;
- permitted scope and a stop rule for no applicable issue.

If no eligible unopened case with independently qualified consequence evidence exists, record `BLOCKED_NO_PROSPECTIVE_TARGET`. Do not substitute synthetic cases and do not claim commercial usefulness.

## Equal-information reviewer experiment
Randomize assignment to conventional GitHub/CI ledger (A) or MathGraph Check evidence-scoped presentation (B) with balanced task order, using consenting competent reviewers. Both arms must be able to open the same source, raw CI and artifacts, reports, and receipt authority. Arm B may organize and maintain this evidence, not withhold it from A. Freeze the content and start each arm from a clean context. Record:
- decision: merge / block / defer / request specific evidence;
- exact-source claim(s), invalid or stale dependencies, independent controls;
- false PR attribution and unjustified assurance promotions;
- elapsed time, hands-on time, interruptions, tool calls, investigation cost and reviewer confidence;
- verifier replay outcome and ground-truth discrepancies.

Scored analysis is paired per task, records all null/negative outcomes and follows the predeclared stop rule. A faster but incorrect decision loses. A tie is a tie.

## Explicit limitations
The existing MathGraph resolver does not authenticate `Receipt` value objects. Signed provenance does not establish semantic correctness. A MathGraph summary generated from a known answer is not independent discovery. No external outreach, review comments, installation, or merge policy changes are authorized by this file. No customer ROI or product advantage is warranted without measured human/organization outcomes.

## Promotion rule
Promote only with an independently reproducible consequential decision improvement or a measured material reduction in reviewer effort at noninferior correctness versus the competent equal-information baseline, including full lifecycle setup/admission overhead. If this is not observed, `COMMERCIAL_ADVANTAGE=UNKNOWN` or `NOT_DEMONSTRATED`.
