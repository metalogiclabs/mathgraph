# MathGraph Check owned-fork PR pilot

This integration is under qualification. It is not yet a public install-and-run release.

## Supported initial capability

Public same-repository PRs on `metalogiclabs/L4YAML` changing only `Scripts/Ledger.lean`. The reviewed Lean 4.35.0 module/CLI adapter generates 1–3 independent Boolean probes, executes the same probes on actual base and head, preserves original guards, and reports finite observations. It does not review arbitrary theorems, validate model-inferred requirements, or run full L4YAML CI. Metaprogramming, unsafe execution, altered original guards, unreviewed CLI and unsupported file changes return UNKNOWN.

## Maintainer operation after activation

1. Select the repository when installing MathGraph Check. A repository administrator controls installation; the hosted pilot additionally needs an enabled capability profile. Installing alone does not enable arbitrary repositories.
2. A user with write/maintain/admin permission comments exactly `@MathGraph -check` on an open PR. The source-repository Check reports progress and links the execution/artifact evidence. A second identical request reuses completed applicable evidence.
3. Review the probe's contract and outcome. A false guard is a reproduced candidate discrepancy, not proof that the model interpreted intent correctly. Base/head labels distinguish inherited failure from introduced regression only when both native arms qualify.
4. If a repair is wanted, comment exactly `@MathGraph -fix`. It reuses the preceding Check's frozen probes, tries a bounded model patch and at most one compiler-feedback revision, and verifies the original/repair/withdrawal sequence. Only a qualified patch may become a draft PR. Nothing merges automatically.
5. A new commit or changed base withdraws old applicability and schedules a new Check for an opted-in PR. Closing the PR withdraws and disables its subscription. A prior Check record remains historical evidence.

## Hosting and source handling

Trusted hosted GitHub Actions jobs use the existing OpenAI account; native jobs receive neither model nor App keys and run offline with read-only source/probes. Only public source within the configured capability is sent to the model; requests set `store:false`. This is not a promise about provider retention or support for private repositories. Do not send private/unreleased FGM, manuscripts, credentials or scientific data through this pilot.

The pilot sponsor pays model usage and hosted compute. Model reservations are capped per installation and UTC day; reservations are conservative and are not refunded after uncertain failures. Compiler-feedback retries are explicitly bounded; paid HTTP retries are disabled. Token usage is retained with the evidence. Actions artifacts are retained for30days by the workflow; longer-lived research records require separate retention. Cancelling a run does not undo already incurred usage.

Removing the installation revokes repository access. The hosted service must refuse unsupported/uninstalled repositories; uninstalling does not delete historical public Check records or previously generated artifacts. No automatic merge or required branch-protection gate is configured.

## Activation requirements

The registered App's selected repositories currently cover only MathGraph and Geth; L4YAML must be selected. App metadata currently subscribes only to `pull_request`; `issue_comment` must be enabled for commands. The trusted repository-dispatch workflow must be released on the central default branch. The existing Cloudflare worker must be deployed with its preserved queue/secrets, the budget coordinator binding/migration, and `PR_PILOT_ENABLED=true` only after review and owned-fork qualification. Do not move App private keys into source repositories or source execution jobs.

Required acceptance: authentic command → installed repository/maintainer reauthorization → model/native admission → exact-source App Check; explicit frozen-probe fix; clean and unsupported controls; base/head changes and stale publication; duplicate/retry and spending limits; second-operator install/run without founder interventions. Until those pass, reports may claim adapter qualification only.
