# Nebius × NVIDIA: Warranted Agent experiment

Status: CANDIDATE — no Nebius runtime inference or end-to-end verification claimed.

## Objective
Demonstrate a coding agent using NVIDIA Nemotron through Nebius Token Factory, with independent evidence checks before consequential release authorization.

## Required cases
1. Valid source revision, tests and artifact identity → WARRANTED only after verifier passes.
2. Stale revision or tampered artifact → REJECTED with exact mismatch witness.
3. Missing evidence → UNKNOWN; retrieve evidence (optionally Tavily), rerun independent verifier, then promote only if supported.

## Verification boundaries
- Record model ID, provider, request ID (if available), invocation timestamp and response hash.
- Record Git source SHA, test command, exit status and test artifact hash.
- Record deployment artifact hash and manifest, if deployment is in scope.
- Never treat model text, tool success or a green CI badge alone as warrant.
- No secrets in repo, trace, screenshot or logs.
- Distinguish synthetic fixtures from real Nebius calls and independent tests.

## Competition requirements
- Runtime Nebius Token Factory inference call using NVIDIA open-source model.
- Significant new work after 2026-08-26; document precise commits.
- Working public demo, open-source license, setup README, public YouTube demo under 3 minutes.
- Target: Coding and Agentic Engineering; Tavily bonus only if real functional runtime Tavily call.

## Cheapest decisive experiment
Run one authentic Nemotron inference on Nebius, independently verify its proposed repair against a pinned repository revision, then mutate the evidence revision and demonstrate fail-closed authorization.

Do not submit or advertise as completed until run logs and independently checkable artifacts exist.
