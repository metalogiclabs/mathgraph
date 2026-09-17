# A/B/G/P Pre-Freeze Methodological Qualification — v1

> **SUPERSEDED — PROVISIONAL DESIGN ONLY**
>
> This document is retained for audit history. It should not be used as a freeze-ready qualification report.

## Why this was superseded

The original v1 headline used `QUALIFIED` too broadly. The completed DEV/QUAL checks established that the statistical analyzers, frozen synthetic challenge fixtures, exact-reference checks, replay, and confirmatory-namespace firewall behaved as specified. They did **not** establish that every experimental arm was implemented end to end.

In particular:

- B still contained development placeholders for recovered structure and for the posterior/bisimulation control;
- the A/P power figures described paired-test power over the declared nuisance envelope, not power of the complete multi-control plus hard-gate PASS event;
- G's DP/brute-force agreement validated the numerical calculation, not the design-level joint-exchangeability assumption;
- A/P independence still requires an audit back to the earliest shared stochastic ancestor.

No confirmatory run occurred. `ABGP-CONFIRM-v1` remained untouched.

## Replacement review package

Use **A/B/G/P Pre-Freeze Design & Implementation Review v2**:

- [v2 Markdown](../abgp-prefreeze-design-implementation-review-v2/README.md)
- [v2 PDF](../abgp-prefreeze-design-implementation-review-v2/ABGP_PreFreeze_Design_Implementation_Review_v2.pdf)

The v2 package preserves the agreed scientific criteria. It corrects only implementation-status and power interpretation, and records Qiming (Bill) Bao's 17 September review points as explicit pre-freeze blockers.

The original v1 figures remain in repository history for provenance. This superseding notice is a reporting correction, not a change to the preregistered hypotheses, effect floors, source-distinctness requirements, or confirmatory criteria.
