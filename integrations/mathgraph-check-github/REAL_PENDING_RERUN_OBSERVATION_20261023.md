# MathGraph Check — genuine pending same-SHA rerun observed

First-party GitHub Actions run: https://github.com/metalogiclabs/mathgraph/actions/runs/39878398161

Original source SHA: `63018d9accc5c05c153cfe1ac22fca1c032cbbb5`.

Previous successful native test job: `120170194613`, success, 17/17 tests.

The GitHub connector's rerun-job call on that job returned `success: true`, which means GitHub accepted the rerun request, **not** that verification succeeded.

Subsequent independent connector calls to the GitHub Actions jobs endpoint returned the following values for the *same* new job `120171814991`:

1. `status: queued, conclusion: null`
2. `status: in_progress, conclusion: null`
3. `status: completed, conclusion: success`

This is **authentic observed GitHub state** on one source-bound run, unlike earlier synthetic pending fixtures. At both pending observations, fresh verification had not yet completed and any claim requiring the fresh attempt remains `UNKNOWN`. The original completed success remains a historical observation, but must not be treated as the new attempt's result.

**Limitation:** The intermediate states were observed through live connector calls and transcribed into this report, not yet written by an independently timestamped GitHub Actions poller or authenticated append-only evidence service. This report itself is not an independently signed receipt. The transition has not yet been wired into Cloudflare's live downstream warrant store, and does not establish selective production withdrawal/requalification. The success is bounded to the workflow's 17 tests, not a semantic correctness proof. No third-party repository contacted.
