# SorryDB v4.4.5 Controlled Source Registration Planner

## Purpose

v4.4.5 turns the four v4.4.4 `SOURCE_CHECKOUT_PATH_UNSTABLE` rows into explicit source-registration requirements. It recovers repository identity and immutable commit information from checked-in certificates, verifies snippet hashes, checks for already-controlled source files, and plans either later hydration, manual registration, or a small exact-context fixture experiment.

The planner does not hydrate source, run Lean, or replay patches. Historical `/tmp` paths remain provenance only.

## Current result

All four rows identify `siddhartha-gadgil/MetaExamples` at commit `edbb75e784db19846a1c19841e182b797afc18bb`. The repository URL is deterministically derived as `https://github.com/siddhartha-gadgil/MetaExamples` from that checked-in owner/repository identity.

The primary registration status is `REGISTRATION_NEEDS_NETWORK_HYDRATION` for all four rows. This is a future input requirement, not a network action performed by v4.4.5.

All four snippet/hash records also qualify as fixture-plan candidates. No actual fixture is created, and snippet fixtures are explicitly not replay-ready unless a later experiment defines and verifies fixture replay semantics.

## Outputs

- `artifacts/sorrydb/source_registration_v4_4_5/summary.json`
- `artifacts/sorrydb/source_registration_v4_4_5/registration_plan.json`
- `artifacts/sorrydb/source_registration_v4_4_5/fixture_plan.json`

## Boundary

Bounded claim: v4.4.5 classifies unstable source rows into controlled source registration statuses and emits registration/fixture plans.

Snippets and hashes are controlled evidence, not full source checkouts. Fixture candidates and hydration requirements are not accepted claims.

The planner does not claim:

- source hydration;
- Lean replay success;
- new proof discovery;
- general SorryDB mining;
- arbitrary proof repair; or
- upstream submission.

## Next frontier

Proceed with v4.4.6 controlled source hydration/registration if network hydration is explicitly authorized, or run a controlled snippet fixture experiment if full checkout policy remains blocking. If repository identity is insufficient, require a manual registration step instead.
