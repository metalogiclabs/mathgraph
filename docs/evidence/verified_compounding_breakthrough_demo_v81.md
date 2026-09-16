# V81 Verified Compounding Intelligence Breakthrough Demo

This is the canonical end-to-end demonstration for the current MathGraph developmental programme.

It has two deliberately separate evidence lanes:

1. **Historical authoritative lineage validation** — validates repository-local contracts and public GitHub workflow/artifact metadata for the V66–V80 evidence chain. Historical results are never relabeled as fresh V81 evidence.
2. **Fresh V81 prospective experiment** — freezes the entire V81 protocol before generating any ten-operation source law, then executes the developmental controller through consequence horizons 2 through 7.

## Run

The GitHub Actions workflow is:

```text
.github/workflows/verified-compounding-breakthrough-demo-v81.yml
```

Equivalent command after fetching the pinned opened-law universe:

```bash
python scripts/run_verified_compounding_breakthrough_demo.py \
  --opened-laws /path/to/eq_size5.txt \
  --out-dir /tmp/mathgraph_v81_breakthrough
```

Do not use `--skip-remote-history` or `--skip-release-check` for an authoritative final run. Those options exist only for local diagnostics.

## Frozen fresh protocol

Before any V81 source is generated, the run freezes and hashes:

- frozen V72 source-ID-agnostic proposer;
- developer SHA;
- fresh-stream seed;
- exactly ten binary operations per fresh source;
- retained capability budget of five;
- one-swap developmental action grammar;
- consequence horizons 2 through 7;
- deterministic consequence-layer caps;
- exact positive-delta admission rule;
- exact exhaustive global-optimality rule;
- warm/cold compounding comparison rule;
- pass/fail gates.

Fresh sources are generated only after the freeze record is written.

## Developmental objects

The evidence pack emits three first-class objects:

- **Verified Capability Block** — persistent admitted capability plus applicability, verifier boundary, provenance, scope, dependencies, causal evidence, and persistence hash.
- **Verified Obstruction** — exact positive gap between a persistent state and the new exact global optimum under a lawful consequence extension.
- **Verified Development Transition** — a proposed state change admitted only when the exact verifier delta is strictly positive.

## Warm/cold compounding test

For each horizon after the initial one:

- **warm** starts from the previously persisted globally-certified capability state;
- **cold** deletes that retained state and restarts from the original declared baseline;
- both use the same learned proposer, exact verifier, consequence graph, fixed budget, and one-swap action language;
- both must reach the same exact globally-certified endpoint quality for a valid comparison.

The classification is:

- `VERIFIED_COMPOUNDING_SIGNAL` when aggregate warm verifier work is no worse than cold, at least one warm comparison strictly saves verifier checks, and the cold-state ablation restores that cost while endpoint quality remains equal;
- `ACCUMULATION_ONLY` when development succeeds but the frozen compounding economics do not support the stronger claim;
- `FAIL` when endpoint equality or a mandatory developmental/trust gate fails.

## Required evidence pack

The workflow uploads:

- `breakthrough_manifest.json`
- `breakthrough_report.md`
- `capability_blocks.jsonl`
- `verified_obstructions.jsonl`
- `development_transitions.jsonl`
- `historical_evidence_validation.json`
- `v81_fresh_result.json`
- `compounding_economics.json`
- `claim_boundary.json`
- `artifact_hashes.json`

`artifact_hashes.json` SHA-256 hashes every required evidence output except itself and records a digest of the full hash set.

## Top-level verdicts

The strongest allowed verdict is:

```text
PASS_VERIFIED_COMPOUNDING_INTELLIGENCE_BREAKTHROUGH_DEMO_V81
```

It is emitted only when all mandatory trust, historical-lineage, fresh-development, autonomous reuse/expand, and exact-global-optimality gates pass **and** the frozen economics classify as `VERIFIED_COMPOUNDING_SIGNAL`.

If verified development passes but compounding economics are neutral, the bounded verdict is:

```text
PASS_VERIFIED_DEVELOPMENT_DEMO_V81_ACCUMULATION_ONLY
```

## Claim boundary

A passing run is bounded evidence that, in the declared deterministic equational graph model, a verifier-gated developmental system can persist admitted capability, certify exact fixed-budget sufficiency, identify exact obstructions under lawful consequence extensions, admit only strictly improving repairs, autonomously choose state reuse versus verifier-only expansion, and test whether retained admitted capability reduces verifier work needed to reach later equally globally-certified capability.

It does not establish AGI, universal self-improvement, unbounded adequacy, universal sufficiency of one-swap actions, or equivalence between synthetic equational transfer and arbitrary natural-world intelligence.
