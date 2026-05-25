# Canonical Pipeline

MathGraph is a verification-routing kernel. The canonical path is intentionally
small:

```text
claim or task
-> semantic validation boundary when an informal claim is present
-> formal claim / artifact
-> advisory route and constructor selection
-> verifier / finite checker / trusted importer / chain audit
-> EvidenceManifest
-> replay
-> invariant checks
-> Lawbook acceptance
-> Reason Atlas routing memory
```

## Terminal Contract

Every accepted claim ends in exactly one terminal form:

- `VERIFIED_PROOF`
- `FINITE_COUNTERMODEL`
- `NAMED_OBSTRUCTION`

Finite-search failure is not proof. Raw verifier output is not boundary
evidence by itself. Advisory route pressure, H-Tilt scores, Reason Atlas entries,
semantic intake, and model output can guide work but cannot verify claims.

## Canonical Modules

- `mathgraph/certificates.py`: terminal forms and compact certificates
- `mathgraph/invariants.py`: executable trust-boundary checks
- `mathgraph/evidence_manifest.py`: replayable evidence manifest schema
- `mathgraph/evidence_replay.py`: manifest replay checks
- `mathgraph/lawbook.py`: Lawbook entry dataclasses and review surface
- `mathgraph/lawbook_acceptance.py`: manifest-backed acceptance contract
- `mathgraph/lawbook_boundary.py`: canonical terminal-admission façade
- `mathgraph/lawbook_ingest.py`: boundary-gated Lawbook ingest helpers
- `mathgraph/lawbook_query.py`: query façade for reusable artifacts
- `mathgraph/lawbook_export.py`: manifest, JSONL, and summary exports
- `mathgraph/lawbook_reuse.py`: reuse and action-change signals
- `mathgraph/reason_atlas.py`: advisory routing memory and verifier-backed metrics
- `mathgraph/semantic_validation.py`: informal/formal claim boundary
- `mathgraph/finite_magma_world.py`: small deterministic finite checker world
- `mathgraph/finite_magma.py`: finite magma representation and checked countermodel certificates
- `mathgraph/magma_constructors.py`: deterministic constructor families
- `mathgraph/sat_cache.py`: constructor satisfaction cache
- `mathgraph/policy_engine.py`: advisory route policy builder
- `mathgraph/proof_congruence.py`: bounded TRUE-side congruence traces
- `mathgraph/true_proof_templates.py`: proof-template family inventory
- `mathgraph/verifier_execution.py`: local verifier execution boundary
- `mathgraph/verification_loop.py`: stable loop façade
- `mathgraph/compounding_engine.py`: canonical memory-becomes-capacity runner
- `mathgraph/autonomous_compounding_engine.py`: autonomous finite-core façade and native v2 recovery loop
- `mathgraph/autonomous_finite_recovery.py`: native constructor/SAT-cache recovery adapter
- `mathgraph/kernel.py`: compact kernel acceptance surface

## Canonical Commands

```bash
python scripts/run_release_check.py --quick
python scripts/run_repo_architecture_audit.py
python scripts/run_mathgraph_compounding_loop.py --allow-fallback-demo --out-dir /tmp/mathgraph_compounding_demo
python scripts/run_mathgraph_compounding_engine.py --out-dir /tmp/mathgraph_compounding_demo --episodes 2 --tiny-demo
python scripts/run_autonomous_compounding_engine.py --out-dir /tmp/mathgraph_autonomous_v2_tiny --tiny-demo --finite-core-mode native_v2 --episodes 3 --sample-pairs 80 --repair-budget 20 --max-n 3 --seed 20260524 --write-report
python scripts/run_true_side_inventory.py --out-dir /tmp/mathgraph_true_inventory_demo --tiny-demo
```

The compounding command is the canonical repo-level loop. Fallback mode proves
the wiring without claiming real SAIR results; real SAIR mode requires explicit
equation and matrix paths.

The autonomous native v2 command is the finite recovery elevation path: it
builds a constructor bank, SAT cache, generic route, residual repair route,
PQ-IR obstruction names, and advisory Lawbook reuse. These objects guide search
only; they cannot promote TRUE or FALSE without checker/verifier evidence.

## Real-Corpus Compounding Benchmark

Recursive residual compounding is the first stronger real-corpus compounding
benchmark:

```text
generic finite-countermodel route
-> residual frontier
-> residual-mined advisory constructors
-> recursive memory generations
-> compact constructor atlas
-> held-out transfer evaluation
-> TRUE contamination controls
```

Run the fallback-safe path with:

```bash
python scripts/run_recursive_residual_compounding.py --profile smoke --allow-fallback-demo --out-dir /tmp/mathgraph_recursive_residual_smoke
```

Compact atlas routes are advisory scheduling objects. They do not verify claims
or enter terminal Lawbook memory without independent boundary-backed evidence.

## Polarized Quotient-Continuation IR

PQ-IR is the symbolic feature layer for ETP implications. It parses binary magma
equations, builds bounded quotient-state features, classifies residual basins,
and emits advisory constructor-family recommendations. It feeds compounding and
residual-routing code, but it is not a truth boundary.

## Multi-Episode ETP Compounding

The ETP compounding engine is the repo-native constructor/residual loop:

```text
episode -> constructors -> finite checking -> residuals -> obstruction atlas
-> repair constructors -> Lawbook update -> next episode
```

It writes a lightweight SQLite Lawbook plus CSV/JSON reports. Repair
constructors and obstruction rows are advisory; only concrete finite
countermodel certificates can support FALSE terminal candidates.

## TRUE-Side Inventory

The TRUE-side inventory generates bounded congruence traces and Lean skeletons.
These are candidate proof-template artifacts until a proof verifier accepts
them. Bounded closure can guide future proof routes, but it is not
`LEAN_VERIFIED`.
