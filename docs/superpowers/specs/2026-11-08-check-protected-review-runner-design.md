# MathGraph Check protected review runner — bounded design

## Intent

Make the already tested signed-review plus historical-proof-ZIP gate callable
from a separately administered operator context. The runner is a **read-only
admission tool**, not a new source of reviewer approval, Lean proof validity,
or universal YAML correctness.

## Approaches

1. **Selected:** Node host qualifier that checks the workflow context,
   separately trusted policy, authenticated GitHub artifact/job metadata,
   exact signed packet, actual artifact ZIP, and the PR head again. Fail closed
   on missing credentials or evidence. A thin CLI can read private policy/key
   files from a protected host and emit neutral JSON only.
2. A `pull_request_target` CI host could access policy but risks executing
   PR-authored code with elevated secrets. Rejected.
3. A new hosted service or production deployment adds an unnecessary security
   surface before there is a real external reviewer. Deferred.

## Boundary

- Host context must be an explicit default-branch `workflow_dispatch` run. A
  string naming a protected branch is not cryptographic proof of protection;
  the operator must actually run vetted code and administer reviewer keys
  independently of PR content.
- GitHub REST binds the evidence ZIP digest to the original source run and
  successful proof job, including a required qualification step. The ZIP is
  supplied separately as a file; byte identity must match GitHub metadata
  and the out-of-band receipt policy.
- Exact signed source packet and PR head are checked before and after evidence
  verification to catch replacement during the run. No publication, merge,
  replay, or secret logging occurs.
- Only `BLOCKED` / advisory finite `NAMED_OBSTRUCTION` is promotable. Failed
  evidence, missing human review, changed heads, and incomplete metadata are
  `UNKNOWN`. Full YAML-language equivalence and fresh kernel replay remain
  `UNKNOWN` even when the historical artifact corroborates.

## Qualification

Synthetic signer/ZIP fixtures prove mechanics, never independence. A live run
will require administrator-controlled reviewer key, receipt policy and
cross-repository evidence-read credential before promotion.
