# Verified Developmental Navigation

A minimal verified controller for adaptive problem solving.

The core rule is:

> Keep the coarsest state that preserves lawful verified futures; seek the cheapest evidence that proves the state or continuation language inadequate; make the smallest justified repair; retain it only when it changes future reach.

The trusted Lean kernel is under `lean/`. Real case studies are under `case_studies/`.

## Core objects

- **Identity**: same protected verified futures (`FutureEq`).
- **Capability**: verified reachability.
- **Boundary**: explicit `CompleteCover`; absence licenses only boundary-relative impossibility.
- **Development**: conservative expansion that changes verified reach while retaining old capability.
- **Routing**: ACT if one action is lawful in all surviving worlds; otherwise PROBE if an admitted question resolves the commitment defect; otherwise EXTEND_QUESTIONS.

## Real cases

### 1. Lean kernel differential census — real checker data

Source: `heathsanchez/test` Actions run `32782797883`, commit `cfa4d1cbb838d3116808ea3a2babdc7f805a9d80`, artifact `v41-disagreement-atlas`.

The source run evaluated 141 tutorial tests across six independent Lean checkers (846 checker/test records). The case-study program recomputes the checker quotient from the full outcome matrix, then exhaustively searches for the smallest test subset preserving exactly that quotient.

Result: the full 141-test behavioral quotient has three classes, and **two tests suffice to preserve it exactly**: a 70.5× context compression. There are 14 distinct minimum two-test bases. This is a direct real-data example of future-relative quotienting and active separator compression.

### 2. UVRM Graph V6 — protected next-move benchmark

Source: `heathsanchez/test` Actions run `32691619972`, commit `d38055fd8790871ddfd4db7e082171d642bf2ede`, artifact `uvrm-graph-v6-protected`.

The case-study program recomputes aggregate scores from the raw 40 scored rows and checks the frozen matched-budget and wrong-semantics controls.

Result: `GRAPH` passes 7/8 cases with mean semantic score 0.7083; matched one-call `RECONSTRUCT_1` passes 4/8 with 0.3750; `GRAPH_PERMUTED`, which preserves the supplied evidence/topology while corrupting relation semantics, passes 4/8 with 0.5000. No arm has a forbidden hit. This is a real-data example in which retained typed state changes next-move quality and the relation labels carry causal information.

### 3. Palomar closure-capability seed — real Lean-certified phase change

Source: `metalogiclabs/mathgraph` Palomar submission commit `743fdf17213d9b3cfa29be51f9590f6c976f8de1`, project `palomar/closure-capability`.

`lean/VerifiedDevelopmentalNavigation/PalomarSeed.lean` embeds the submitted closure-capability witness into the generic VDN calculus: old reachability is obstructed; a conservative extension admits a new witness; old capabilities remain reachable. CI recompiles this seed together with the generic development certificate and routing kernel.

## Run

```bash
bash case_studies/scripts/fetch_sources.sh
python3 case_studies/scripts/run_all.py
cd lean
lake build
lake env lean VerifiedDevelopmentalNavigation/PalomarSeed.lean
lake env lean VerifiedDevelopmentalNavigation/DevelopmentCertificate.lean
lake env lean VerifiedDevelopmentalNavigation/Routing.lean
```

The case-study workflow downloads the original immutable GitHub Actions artifacts directly by run and artifact name, then recomputes results from those source files. `case_studies/PROVENANCE.json` records the source identities.
