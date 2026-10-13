# MathGraph public release status — 13 October 2026

This document updates the older [living-network release-candidate checkpoint](../mathgraph_living_knowledge_network_release_candidate_2026-10-12.md), which is preserved as a pre-merge historical report.

## Git identity and release history

- [PR #160 — Living knowledge network](https://github.com/metalogiclabs/mathgraph/pull/160) merged on 12 October 2026 UTC, merge commit `61ef2879120e1c9e54d11368196d69e47ae437df`.
- [PR #161 — Resolve presentation hotfix](https://github.com/metalogiclabs/mathgraph/pull/161) merged on 12 October 2026 UTC, merge commit `231514a18bce8740124a4f519c415f37c77b399f`.
- The exact reported release qualification for PR #160 is recorded in its PR body, including [website and browser CI](https://github.com/metalogiclabs/mathgraph/actions/runs/38310982717), [catalogue regeneration and independent consumer](https://github.com/metalogiclabs/mathgraph/actions/runs/38310982768), [offline Resolve replay](https://github.com/metalogiclabs/mathgraph/actions/runs/38310982801), and [finite capability conformance](https://github.com/metalogiclabs/mathgraph/actions/runs/38310982729).
- A GitHub Vercel deployment status was `success` for merge commit `231514a18bce8740124a4f519c415f37c77b399f`. This is not an independently performed public-route/browser smoke test of `https://mathgraph.org`. Production alias parity and live availability require a separate check.

## Evidence boundary

- Pinned Mathlib v4.34.1: 2,345 source declaration occurrences across 13 modules and 3,571 `DECLARES`/`TYPE_REFERENCES`/`IMPORTS_MODULE` structural relations. All are `SOURCE_INDEXED` / `NOT_CHECKED` for independent proof verification, not verified theorem counts.
- Record 001: separately replayed, source-pinned original JPL Lean proof objects, 48 decoded YAML suite cases and 4 additional guards. Whole-language correctness remains `UNKNOWN`; no JPL/NASA endorsement.
- Record 002: three original publisher-documented support paths become `STALE`; the related propositions remain `UNKNOWN`; the unrelated exact JPL historical finite observation stays `WARRANTED_BOUNDED`.
- One exact finite reusable capability is qualified, not general capability-family compilation.
- Independent static/offline consumers validate their declared structural and historical scopes but do not rerun the original Lean proof, establish freshness/current applicability, or authorize actions.

## Qualification boundaries retained

The focused living-network gate recorded **654 passed Python tests and 72 subtests** plus the documented Astro/browser/consumer build gates at its exact candidate commit. The broader repository research diagnostic recorded **2,187 passed, 1 skipped, 13 failed and 19 setup errors**; these are retained research/environment/fixture residuals, not silently relabeled green.

This October outreach branch changes presentation, onboarding, documentation, and proposes root licensing. It does not mutate the two immutable records, verifier receipts, exact source catalogue, historical pins, policy bytes, or qualified trust contracts. New commit CI, a production smoke test, and owner approval of rights to apply Apache-2.0 are separate gates.
