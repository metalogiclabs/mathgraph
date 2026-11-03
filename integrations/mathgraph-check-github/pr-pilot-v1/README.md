# MathGraph Check — maintainer pilot

MathGraph Check is live on the owned public `metalogiclabs/L4YAML` fork. Use one PR comment to request an advisory Check, then inspect the requirement, source revision and native evidence. External install-and-run operation is not yet qualified. Installing the App alone does not enable a repository or checking method.

## What the current App checks

| Change / method | Evidence it can support | Boundary |
| --- | --- | --- |
| `Scripts/Ledger.lean`, reviewed shell expectations | Three operator-adopted requirements across five inputs, replayed in Lean4.35 with independent Bash observations; protected original guards and repository gate | Finite behavior only; whole-PR and general shell correctness remain UNKNOWN |
| Selected changed `Scripts/*.lean` modules | Compilation of selected roots/imports and a frozen regression corpus on base/head, with uncovered paths reported | Compilation and tested regressions do not establish intended semantics |
| Reviewed Python→Lean CLI migrations | Fixed native differential fixtures for traceof, ledger-diff and the read-only residue-classes subcommand | Only the registered entry points, fixtures and comparison policies; proof rewriting is excluded |
| Exact registered empty-tail constructor calibration | The same declared consumer accepts the required capability and rejects its deletion or a weakened offer | Exact retrospective source calibration, with `propext` explicit; not generic claim discovery or proof necessity |

An unsupported source, missing reference, unqualified producer, changed source or incomplete native run retains UNKNOWN. A behavior difference is not automatically a defect. Model-generated expectations remain hypotheses until admitted against an independent requirement/reference. Historical expectation sets keep their original scope; adding an obligation requires new admission and replay.

## Check, fix, inspect

1. On an open public, same-repository PR (both head and base in `metalogiclabs/L4YAML`), a user with write/maintain/admin permission comments exactly `@MathGraph -check`. Progress and results appear in the PR's Checks tab. The report states the exact base/head, selected method, requirement and recommended action.
2. Review the requirement and the evidence. Reviewed shell checks use fixed expectations and no model test generation. An unfamiliar ledger audit may propose hypotheses, but native failure alone does not authorize a repair. Base/head comparison attributes an introduced regression only when both arms qualify.
3. For a qualified ledger failure, comment exactly `@MathGraph -fix`. It reuses the preceding Check's frozen probes, proposes a bounded model patch, and allows at most one compiler-feedback revision. Native jobs test the original, candidate and withdrawn candidate, preserving original guards and repository gates. Only a qualified candidate becomes an unmerged draft; an exact existing draft can be reused.
4. Review the draft diff and normal CI. A finite pass is not merge approval. The raw downloadable repair report retains the authenticated draft link; the Check remains advisory.
5. When a supported PR update webhook reports a changed head or base, the App withdraws old applicability and schedules a new Check for an opted-in PR. A target-base-branch push alone is not handled by this event adapter; request a new Check rather than assuming it was automatically rechecked. A closed PR withdraws and disables its subscription. Historical records remain inspectable. Duplicate completed requests reuse applicable evidence rather than creating another Check or dispatch.

Repair is qualified only for the admitted ledger route. Other methods report their bounded evidence and uncovered obligations; they do not silently inherit repair permission.

## One inspectable example

- [Fork PR27](https://github.com/metalogiclabs/L4YAML/pull/27) fails the leading-output requirement on both base and head: it is an existing discrepancy, not a regression introduced by this PR. Both `>out python3 scripts/a.py` and `> out python3 scripts/a.py` should preserve the script command. In `> python3 echo scripts/a.py`, `python3` is a redirect filename and must not become a command.
- [App repair29](https://github.com/metalogiclabs/L4YAML/pull/29) passes the admitted five inputs. The authentic [model-repair run41724109428](https://github.com/metalogiclabs/mathgraph/actions/runs/41724109428) preserves160original guards and repository gates; withdrawal restores the failure.
- [Final-release check27](https://github.com/metalogiclabs/mathgraph/actions/runs/41738771424) reproduces the failure; [check29](https://github.com/metalogiclabs/mathgraph/actions/runs/41738781363) passes the same finite boundary. Both make zero model calls and skip repair jobs. Source and native bytes are bound independently of PR prose.
- [Unqualified producer example3](https://github.com/metalogiclabs/mathgraph/actions/runs/41738802484) returns UNKNOWN with an actionable diagnostic and no native/model work.

This is an owner-selected, operator-adopted demonstration, not blind defect discovery or customer approval. Consult the current PR Check for applicability after later changes.

## Budget, source handling and retained evidence

Reviewed fixed/candidate checks, registered CLI/repository checks and unsupported requests reserve no model spend. A producer candidate either receives authenticated fixed expectations or blocks; it cannot fall back to model generation. Generic model checks reserve49budget cents, fixes98, with a1000cent daily reservation cap per installation. The cap resets at UTC midnight. Reservations are conservative, are not actual billed usage, and are not refunded after uncertain failures. No-model reviewed checks remain available when model capacity is exhausted. Paid HTTP retries are disabled; compiler feedback is bounded.

The sponsor pays model usage and hosted compute. Only public source within an enabled method may be sent to the model, with `store:false`; this is not a promise about provider retention or support for private source. Native jobs receive neither model nor App credentials and run against pinned source/probes. Do not submit private manuscripts, credentials or unreleased scientific data through this pilot.

Reports retain source identity, requirement/admission, verifier context, native observations, assumptions and explicit UNKNOWNs. GitHub Actions artifacts are normally retained30days by the pilot workflow; separately retained research bundles preserve longer-lived evidence. A hash or prose result alone does not authenticate execution. Cancelling a run does not undo incurred usage.

Removing the installation revokes repository access; it does not delete historical public Checks or artifacts. The runtime reauthorizes installation, maintainer and source identities for each request. Source PRs cannot choose native commands, change the frozen corpus, grant their own checking method, or supply central publisher credentials. No automatic merge or branch-protection approval is configured.

## What remains outside this pilot

Nicolas/customer approval, second-operator self-service, arbitrary repositories, full-PR correctness, general shell conformance, formal statement equivalence and generic proof necessity remain unqualified. Before external operation, qualify the target repository/method, a different maintainer's install/command/uninstall flow, cost sponsorship and source handling. Do not share App private keys.

Equal-information review comparison is preregistered in `experiments/check-review-increment-v1/PROTOCOL.md`; its actual Devin arm remains pending. No superiority or10xperformance result is claimed. The current implementation and evidence are linked from [draft PR265](https://github.com/metalogiclabs/mathgraph/pull/265).
