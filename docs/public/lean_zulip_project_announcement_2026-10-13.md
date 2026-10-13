# Proposed Lean Zulip project announcement — 13 October 2026

**Topic:** MathGraph: source-pinned Mathlib objects and scoped verification evidence

**Publication gate:** Draft only. Confirm the channel norms, the pending Apache-2.0 rights review/merge, and live links before posting. JPL/NASA and Tao are cited as independent public sources, never collaborators or endorsers.

---

Hi all,

I've been building [MathGraph](https://mathgraph.org), a research-stage project from **Metalogic Labs** for inspecting source-pinned mathematics alongside separately qualified verification evidence. [Source on GitHub](https://github.com/metalogiclabs/mathgraph); an Apache-2.0 proposal for original MathGraph code is currently under rights review.

**Source indexing is not independent proof checking.** Today you can:

- **Explore a small Mathlib slice:** 2,345 declaration occurrences across 13 modules of pinned Mathlib v4.34.1, with 3,571 typed structural relations and permanent source pages. `DECLARES` links a module to its declaration; `TYPE_REFERENCES` records constants occurring in a declaration type. These are **not** proof-dependency edges. [Explore](https://mathgraph.org/explore/).
- **Inspect an actual Lean case study:** We used a pinned revision of [JPL's public L4YAML Lean 4 project](https://github.com/nasa-jpl/L4YAML) as third-party code, rechecked its scoped named Lean proofs, and matched 48 decoded YAML test-suite cases plus four additional guards. General parser correctness remains **unknown**; this is not JPL/NASA involvement or endorsement. [Evidence](https://mathgraph.org/records/mg-l4yaml-source-check-20261010/).
- **See what changes when evidence is withdrawn:** Three documentary support paths become `STALE`, while the associated mathematical propositions remain `UNKNOWN`, not disproved. The unrelated bounded JPL observation retains its historical status. [Resolve](https://mathgraph.org/resolve/).

Unlike doc-gen4, Loogle, LeanSearch or import graphs, MathGraph is **not** trying to improve theorem search. It's experimenting with evidence scope, provenance and status across revisions. Tao's recent [Math 2.0](https://terrytao.wordpress.com/2026/10/10/math-2-0/) talk prompted related questions; [IEANTN](https://github.com/teorth/IEANTN) is independent prior work.

Two questions for Lean/Mathlib users: **(1)** What should count as a proof dependency or axiom assumption beyond a simple type reference? **(2)** When a Mathlib declaration or its environment changes, which previously qualified receipts should become stale?

---

**Channel note:** Recent Lean Zulip channel traffic could not be confirmed from the public viewer in this environment. Check its `#announce` description or appropriate project-announcement channel before posting.
