# Holdout 001 — gookit/config PR #225 — outcome

Selection was frozen before PR diff/source inspection at commit `14d3e78450cbd1039cb49b21d095b1638749b767`.
On inspection the exact PR base/head were:
- base `621a48781a4229be0a3d1ce6b6339eb1ed25d541`
- head `5623891c086d24664a2affb441fd676cb720ebd4`
- https://github.com/gookit/config/pull/225

The author's own PR body and diff explicitly identify the reentrant getter deadlock and add `TestSetHookCanReadUpdatedValue` for top-level, nested and literal dotted keys. Author reports `go test ./...`, `go vet ./...` and repeated native race test green on macOS/arm64. These statements are **author claims, not independently rerun by this experiment**.

Our precommitted primary candidate obligation was reentrant getter and visibility of updated value. Since the author's supplied tests already cover it, it is **BASELINE_VISIBLE / NO NOVEL FINDING**, not a MathGraph win. Secondary concurrent consistency and ablation have not been executed: UNKNOWN. No external CI run or direct code mutation was performed.

Comparison decision: do NOT promote H1 superiority or accuse the PR. Preserve outcome as a prospective negative/low-value selection. Next target must use a separate source-blind preregistration; never retrospectively count previously exposed PRs.
