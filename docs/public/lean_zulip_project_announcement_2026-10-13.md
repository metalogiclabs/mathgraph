# Proposed Lean Zulip project announcement — 13 October 2026

**Proposed topic:** MathGraph: source-pinned Mathlib objects and scoped verification evidence

**Publication gate:** Draft only. Check community channel norms and confirm that the Apache-2.0 license proposal has been legally reviewed and merged before asserting it is open-source licensed. Verify the live public links. Do not claim cooperation or endorsement from NASA/JPL or Tao.

---

Hi all,

I've been building [MathGraph](https://mathgraph.org), a research-stage project from **Metalogic Labs** for browsing source-pinned mathematics alongside separately qualified verification evidence. The [source is on GitHub](https://github.com/metalogiclabs/mathgraph) (Apache-2.0 for original MathGraph code, subject to the licensing release gate).

**A source index is not independent proof checking.** The current site offers:

- **A deliberately small Mathlib slice:** 2,345 declaration occurrences across 13 modules of pinned Mathlib v4.34.1, with permanent source pages and 3,571 typed structural relations. For example, `DECLARES` means a module declares an object, and `TYPE_REFERENCES` records a constant referenced in a declaration's type. Neither is a verified proof-dependency edge. [Try Explore](https://mathgraph.org/explore/).
- **A reproducible Lean case study:** We checked a pinned revision of [JPL's public L4YAML Lean 4 repository](https://github.com/nasa-jpl/L4YAML) as third-party code, replayed its named Lean proof-object receipts, and matched 48 selected decoded YAML test-suite cases plus four extra guards. The record publishes exact source and verifier pins, while general parser correctness remains unknown. This is not JPL/NASA sponsorship or endorsement. [Inspect the evidence](https://mathgraph.org/records/mg-l4yaml-source-check-20261010/).
- **Evidence status separate from mathematical truth:** In a historical dependency example, three withdrawn documentary support paths become `STALE`; the associated propositions stay `UNKNOWN`, not disproved. An unrelated bounded L4YAML result keeps its original historical scope. [See Resolve](https://mathgraph.org/resolve/).

Unlike doc-gen4, Loogle, LeanSearch, or module import graphs, this is not aimed at better declaration search. It's an experiment in **portable, scope-aware provenance and evidence lifecycle**. It does not yet contain an independently verified full-Mathlib dependency graph or hosted general Lean verifier.

This overlaps with questions raised by [Tao's recent Math 2.0 talk](https://terrytao.wordpress.com/2026/10/10/math-2-0/); [IEANTN](https://github.com/teorth/IEANTN) is relevant, independent prior work.

Two questions for Lean/Mathlib users:

1. Which proof dependencies and axiom assumptions should be captured beyond direct `TYPE_REFERENCES` without making the graph noisy or implying unearned proof support?
2. When a declaration or environment changes between Mathlib commits, what should make a *previously qualified* receipt stale, and what should still be reusable?

Source and reproductions: https://github.com/metalogiclabs/mathgraph

---

**Channel note:** A public Zulip web viewer did not expose recent topic traffic from this environment. Confirm the community's current preference for project announcements (often `#announce`) before posting. Do not post this draft automatically.
