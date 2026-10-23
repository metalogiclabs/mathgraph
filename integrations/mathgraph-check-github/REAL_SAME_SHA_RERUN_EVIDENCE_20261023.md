# MathGraph Check — authentic same-SHA CI retry evidence (2026-10-23)

## Actual GitHub evidence
- Repository: `metalogiclabs/mathgraph`
- Workflow run: https://github.com/metalogiclabs/mathgraph/actions/runs/39878398161
- Source commit (workflow's original branch head): `63018d9accc5c05c153cfe1ac22fca1c032cbbb5`
- Original completed job: `120169578515` — `success`, 17/17 Node tests
- Rerun invoked through GitHub's rerun-job API (returned `success:true`)
- Latest attempt's completed job: `120170194613` — `success`, 17/17 Node tests

This is a real rerun of the **same workflow run**, not a fresh source commit. GitHub returned a distinct job ID. The native test summary in both job logs is green.

## What this actually demonstrates
- Authentic GitHub Actions run re-execution without changing source.
- Two successful completed job observations on one source-bound workflow.
- Repeat native verification can be retrieved and differentiated by job identity.

## What is NOT yet demonstrated
- A persisted, independently acquired *pending* observation during this rerun.
- A live failure/withdrawal or fresh evidence transition to UNKNOWN and back to OBSERVED.
- Deployment of the `same-head-ci-lifecycle-v1.mjs` adapter inside the Cloudflare queue consumer.
- Independent test of cross-attempt authority rules against native GitHub APIs.
- A new semantic correctness theorem or general CI performance improvement.

Do not use the green rerun as evidence that the whole claim was scientifically verified. Preserve the bounded source and run IDs for later readback.
