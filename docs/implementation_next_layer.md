# MathGraph Next Implementable Layer

This layer adds closed, testable infrastructure that is ready now. It does not
attempt unresolved research problems, and it does not change MathGraph's truth
boundary.

## What Was Added

1. **Terminal schema compatibility**: `mathgraph.terminal_schema` maps legacy
   terminal vocabulary into a canonical proof/refutation/obstruction schema.
2. **External certificate envelope**: `mathgraph.external_certificates` records
   outputs from Lean, Coq, Isabelle, Z3, CVC5, MiniSAT, finite checkers, and
   other tools as advisory objects until replayed or revalidated.
3. **Closed verification loop**: `mathgraph.closed_loop` connects pending pairs,
   route outcomes, the existing route learner, and the H-Tilt scheduler.
4. **Smoothed route prior**: `mathgraph.route_priors` avoids sparse-data route
   collapse with smoothing, exploration mass, and entropy flooring.
5. **Causal IR**: `mathgraph.causal_ir` adds explicit causal claim records and
   conservative obstruction hooks.
6. **Grounding IR**: `mathgraph.grounding` records continuous-to-symbolic
   grounding attempts as advisory denotation payloads.

## Truth Boundary

Models propose. MathGraph constrains. Verifiers decide. The Lawbook remembers.
Projection scales.

Advisory artifacts cannot promote truth. External certificates, causal checks,
grounding records, route priors, and closed-loop scheduling pressure remain
advisory unless a verifier, trusted importer, finite validator, or chain audit
creates explicit boundary evidence.

## Deferred Research Hooks

The following are intentionally not implemented here:

- principled `V` discovery
- abstraction formation law
- portable survivor geometry
- one-channel emergence law
- real do-calculus
- real sensor grounding
- learned proof constructor synthesis

Those should remain research hooks until they can be encoded as small,
auditable, verifier-bound components.

## Contact Promotion Follow-On

The next implementable layer after the advisory/control-plane work is Reason
Atlas contact promotion. It turns Lean probe rows into:

- `STRICT_CONTACT_SEED`
- `SIGNATURE_ATLAS_RECORD`
- `REPAIRABLE_OBSTRUCTION`
- `TRANSFER_TEST`
- `PROMOTED_ROUTE_LAW`
- `NEXT_EXPANSION_QUEUE`

A single clean contact remains a seed. MathGraph promotes a route law only
after repeated clean transfer across compatible declarations or target
instantiations. Promoted route laws are advisory scheduling and construction
guides, not proof certificates.

## Root Operator Induction

The next implemented layer lifts repeated verified trace survivals into typed,
parameterized root operator schemas. Literal macros remain useful examples, but
schemas such as `move(axis, distance=2); recolor(color)` are the reusable
constructor candidates that can compress residual families and close part of an
oracle gap.

Root operator schemas are still advisory. They guide proof search, program
synthesis, countermodel search, constructor selection, and route scheduling;
they do not emit `VERIFIED_PROOF`, `REFUTATION_CERTIFICATE`, `TRUE`, or `FALSE`.

## Reason Atlas Persistence And Feedback

Reason Atlas persistence is now implemented as the compounding memory layer for
advisory structures. Promoted contacts, root operator schemas, constructor
hints, and repairable obstructions can be stored in SQLite, receive transfer and
verifier feedback, rescore priorities, and emit next advisory queue rows.

## Closed Verification Loop And Promotion Gate

The current implemented bridge connects advisory Reason Atlas queue rows to
verifier-bound Lawbook candidates through a central `PromotionGate`.
`ExternalCertificate` objects can carry proposed terminal forms and boundary
evidence, but they remain advisory until the gate confirms a valid verifier,
trusted-importer, finite-validator, or chain-audit boundary.

The callback-based closed verification loop can run in smoke tests without Lean:
it consumes advisory queue rows, calls a verifier callback, gates the resulting
certificate, records feedback in the Reason Atlas, rescales priorities, and
exports the next advisory queue.

## Breakthrough Loop Demo

The first functioning metabolism is now implemented in
`mathgraph.breakthrough_loop`. It runs unresolved finite magma implication
tasks through advisory constructor hints, evaluates concrete finite tables with
a deterministic checker, wraps successful refutations as `ExternalCertificate`
objects, gates them through `PromotionGate`, records failures as Reason Atlas
feedback, and uses the rescored queue in later episodes.

The demo is small but semantic: accepted certificates include a finite magma
table and witness environment proving that the source equation holds globally
and the target equation fails. Failed searches remain residual feedback, not
truth.

## SAIR Breakthrough Loop

The same metabolism now has a SAIR-compatible runner. When `equations.txt` and
`etp_matrix_full_best_bool.npy` are available, MathGraph samples matrix-labeled
FALSE pairs, normalizes SAIR binary-operation syntax, tries finite magma
constructor banks, and admits only checker-validated finite countermodels
through `PromotionGate`. If the files are absent, the runner falls back to the
built-in breakthrough corpus.

## SAIR Motif Hygiene And Held-Out Scheduler Evaluation

The immediate empirical validation layer now cleans real-corpus SAIR
finite-countermodel traces into mechanism-only atoms, mines advisory constructor
motifs only from `PromotionGate`-accepted traces, and evaluates motif-guided
scheduling on held-out pairs with the real finite checker. The result is no
longer "motifs exist"; it is certificate yield and residual compression versus
baseline constructor scheduling.

## Persistent SAIR Reason Atlas Scale Evaluation

The next scale step admits clean SAIR motifs and root schemas into persistent
Reason Atlas memory as advisory entries, then loads those entries in later
held-out evaluations. This turns a successful run into reusable constructor
priority without crossing the truth boundary.

The scale runner compares baseline constructor ordering, clean in-run motifs,
persistent Reason Atlas priors, combined priors, and oracle ordering. Its value
claim is empirical and replayable: certificate yield, residual compression,
attempt efficiency, oracle-gap capture, and advisory-boundary preservation.

## Spectral H-Tilt Reason Atlas Scheduling

Spectral H-Tilt is now wired into persistent Reason Atlas scheduling. Reason
Atlas entries and feedback events become advisory route telemetry, the spectral
estimator computes survivor mass, support, survival, tilted measure, and killing
pressure, and those values rescore Reason Atlas queue priority.

The SAIR H-Tilt scale evaluator checks the only claim that matters here:
whether H-Tilt-augmented advisory priors preserve or improve held-out
finite-countermodel certificate yield or attempt efficiency. H-Tilt remains
strictly advisory; `PromotionGate`-accepted checker certificates are still the
only route to terminal candidates.

## Principled V Discovery And H-Tilt Calibration

The next empirical layer compares candidate killing/viability operators for
H-Tilt. Training feedback traces induce V scores such as failure density,
rejection pressure, residual persistence, constructor dead-end pressure, attempt
cost, novelty, and composite variants. Multi-seed held-out SAIR evaluation then
selects the operator that improves certificate yield, residual compression, or
attempt efficiency.

The geometry is not the claim. The held-out finite-checker result is the claim.
All V operators remain advisory scheduling pressure and never emit terminal
truth.

## Compounding Lawbook Engine

The canonical v0 compounding layer now stores verifier-directed experience in a
LawbookStore, retrieves sparse context with Lawbook attention, coagulates
repeated attempts into candidate reasons, tests those reasons with
decode-to-verify, and reports whether memory improved the next
verifier-directed episode.

This is the persistent metabolism layer: V/H-Tilt calibration supplies
scheduling pressure inside the loop, while the Lawbook remembers terminal
artifacts and the Reason Atlas compresses action-changing patterns.

## Real SAIR Compounding Benchmark

The real-SAIR-capable benchmark compares baseline static scheduling,
persistent atlas scheduling, best-V H-Tilt scheduling, Lawbook attention,
Lawbook attention plus H-Tilt, and decode-filtered Lawbook attention plus
H-Tilt on held-out FALSE finite-countermodel recovery.

It is the first production-facing test of whether MathGraph memory compounds:
episode memory should improve future verifier-directed search.  The benchmark
is explicit about fallback mode versus real SAIR mode, and only
PromotionGate-backed finite-countermodel recoveries count.

## Production Lawbook Admission

The production admission layer is the fixation step for compounding memory. It
classifies run artifacts as rejected, advisory, candidate, bounded verified,
finite verified, Lean verified, or durable Lawbook entries. Durable admission
requires provenance, verifier/audit boundary evidence, replayability or scoped
bounded evidence, contradiction checks, and non-fallback source.

This keeps the Lawbook verifier-grade: fallback smoke, failed-search TRUE
claims, unverified decode success, and heuristic motifs cannot become durable
memory.

## Multi-Episode Lawbook Compounding

The multi-episode evaluator is the next validation layer: it runs repeated
episodes over one Lawbook, admits or blocks artifacts after each episode, makes
durable memory available to later episodes, and measures residual shrinkage,
certificate yield per attempt, Lawbook action changes, durable-only retrieval,
and artifact reuse.

Fallback smoke remains explicitly labeled as fallback. Real compounding evidence
requires real SAIR files and verifier-backed durable artifact reuse or residual
improvement.

## Real SAIR Artifact Pack

The artifact pack is the current real-run validation layer. It packages the
multi-episode compounding run with configuration, environment metadata, git
metadata, admission reports, Lawbook growth, durable reuse, residual shrinkage,
machine-readable summary, human-readable report, and an optional archive.

Strict mode fails when real SAIR files are absent. Explicit fallback smoke packs
remain clearly labeled and cannot be interpreted as real compounding evidence.

## Canonical Compounding Loop Runner

The canonical compounding runner is the repo-level command for the narrow
memory-becomes-capacity loop. It compares baseline search with memory, Lawbook
attention, Reason Atlas-style routing, and controls; writes metric-labelled
reports; preserves the verifier boundary; and refuses to silently claim real
SAIR results when real corpus files are absent.

## Lawbook Boundary And Façade Hygiene

The Lawbook boundary façade adds a small canonical front door for terminal
admission and low-risk wrappers for ingest, query, export, and reuse signals.
The large `lawbook_store.py` module remains import-compatible as a public
façade; new code should prefer `lawbook_boundary.py`, `lawbook_ingest.py`,
`lawbook_query.py`, `lawbook_export.py`, and `lawbook_reuse.py`.

## Recursive Residual Compounding Benchmark

The recursive residual benchmark ports the Colab residual-mining experiments
into a repo-level runner. It evaluates whether generic finite-countermodel
routes can mine residual constructors, compact those constructors into an
advisory atlas, and improve held-out transfer while preserving zero TRUE
contamination.

## Polarized Quotient-Continuation IR

PQ-IR adds the symbolic quotient/continuation feature layer for ETP implication
pairs. It extracts source quotient pressure, target separation pressure,
fresh-variable escape, projection boundary behavior, repeat/tail continuation
pressure, advisory constructor-family recommendations, and residual obstruction
names. These records are routing signals only.

## Multi-Episode ETP Compounding Engine

The multi-episode ETP engine is the first repo-native PQ-IR-to-Lawbook
metabolism. It builds finite magma constructors, caches equation satisfaction,
evaluates advisory policies, names residual obstructions, selects residual
repair constructors, writes a lightweight SQLite Lawbook, and measures
episode-to-episode lift while keeping finite-search failure separate from TRUE.

## TRUE-Side Proof Inventory

The TRUE-side inventory adds bounded proof-producing congruence traces and
Lean-ready skeleton generation for ETP TRUE candidates. These records are
candidate proof templates until Lean or another proof verifier accepts them.

Implemented:

- Reason Atlas Contact Promotion
- Root Operator Induction
- Reason Atlas Persistence + Feedback Loop
- Closed Verification Loop + Promotion Gate
- Breakthrough Loop Demo
- SAIR Breakthrough Loop
- SAIR Motif Hygiene + Held-Out Scheduler Evaluation
- Persistent SAIR Reason Atlas Scale Evaluation
- Spectral H-Tilt Reason Atlas Scheduling
- Principled V Discovery + H-Tilt Calibration
- Compounding Lawbook Engine v0
- Real SAIR Compounding Benchmark v0
- Production Lawbook Admission v0
- Multi-Episode Lawbook Compounding Evaluation v0
- Real SAIR Multi-Episode Artifact Pack v0
- Canonical Compounding Loop Runner
- Lawbook Boundary And Façade Hygiene
- Recursive Residual Compounding Benchmark
- Polarized Quotient-Continuation IR
- Multi-Episode ETP Compounding Engine
- TRUE-Side Proof Inventory
- Autonomous Compounding Engine v2

Still future work:

- scale native v2 autonomous recovery on full real ETP/SAIR splits
- persistent Lawbook admission for native v2 finite countermodel certificates
- compact obstruction-atlas route selection over multiple seeds
- persistent Lawbook admission for accepted finite countermodel certificates generated by compounding runs
- production Reason Atlas entries from compact atlas routes
- TRUE-side Lean proof-route compounding
- obstruction atlas naming for residual basins
- H-Tilt calibration over recursive residual generations
- full all-FALSE-pair recovery run
- real Lean/finite-checker job runner integration
- H-Tilt scheduling over persistent schema families
- multi-seed large-scale H-Tilt evaluation
- H-Tilt over proof traces
- H-Tilt over finite countermodel root schemas
- H-Tilt over Lawbook closure graphs
- root operator induction over finite countermodel traces
- proof-constructor root induction
- second-order root operators
- principled V discovery
- TRUE-side Lean proof executor
- stochastic multi-armed constructor scheduling
- learned schema proposal models
- learned V operators
- V over proof traces
- V over Lawbook closure graphs
- H-Tilt over Mathlib digest traces
- multi-verifier external certificate envelope
