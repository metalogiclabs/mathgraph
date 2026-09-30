# DiscoveryScheduler v0: Taste Policy Ledger

Curiosity finds pressure. Taste chooses continuation. Attention spends verification. Discovery compresses the residual.

DiscoveryScheduler is a bounded deterministic scheduler for ranking testable
continuation candidates. It records curiosity pressure, taste scoring, attention
allocation, invalid candidates, and trust-boundary status.

It is not H-tilt math, theorem proving, proof synthesis, or an autonomous
discovery engine.

## Purpose

The scheduler turns residual pressure and evidence gaps into auditable
continuation queues. It helps decide where scarce verifier attention should go
next.

## Doctrine

- Curiosity is pressure emitted by unresolved residuals, obstructions, and
  evidence gaps.
- Taste is deterministic ranking by expected verified compression value.
- Attention is budget allocation to ranked candidates.
- Discovery is a verifier-backed or boundary-backed outcome that changes future
  search geometry.

Curiosity without descension is fantasy. Taste without verification is
preference. Attention without residual compression is wasted compute. Discovery
without projection is sterile.

## Candidate Lifecycle

1. Candidate enters the ledger.
2. Candidate is validated against trust-boundary and descension rules.
3. Eligible candidates receive deterministic taste scores.
4. Softmax attention probabilities are assigned.
5. Top candidates are selected for verifier-contact or boundary-backed work.
6. Outcomes can later update taste statistics.

## Descension Targets

No descension target, no attention.

Allowed descension targets:

- `finite_countermodel_attempt`
- `verifier_contact`
- `lean_verifier_contact_candidate`
- `obstruction_naming_attempt`
- `constructor_synthesis_attempt`
- `projection_test`
- `representation_repair`
- `evidence_replay`
- `lawbook_ingestion`
- `reason_atlas_route_test`

## Taste Scoring

The score is deterministic and interpretable:

```text
taste_score =
    + w_certificate * expected_certificate_value
    + w_obstruction * expected_obstruction_value
    + w_compression * expected_residual_compression
    + w_projection * expected_projection_gain
    + w_reuse * expected_reuse
    + w_novelty * novelty_score
    - w_cost * verification_cost
    - w_duplicate * duplicate_risk
    - w_overfit * overfit_risk
    - w_foreign * foreign_moisture_risk
```

Modes are `harvest`, `frontier`, `architectonic`, and `balanced`.

## Attention Allocation

Eligible candidates receive:

```text
P(candidate) proportional to exp(beta * taste_score)
```

Selection is deterministic by attention probability, taste score, then
candidate id.

## Trust Boundary

DiscoveryScheduler is advisory only. It cannot promote truth, cannot produce
`VERIFIED_PROOF`, cannot turn textual Lean digest entries into proofs, cannot
turn failed search into TRUE, and cannot turn route scores into certificates.

Only verifier-backed or finite-checker-backed systems may promote terminal
forms.

## CLI Usage

```bash
python scripts/run_discovery_scheduler.py \
  --fallback-demo \
  --out-dir /tmp/mathgraph_discovery_scheduler_demo
```

```bash
python scripts/run_discovery_scheduler.py \
  --fallback-demo \
  --mode frontier \
  --top-k 3 \
  --beta 1.5 \
  --out-dir /tmp/mathgraph_discovery_scheduler_frontier_demo
```

```bash
python scripts/run_discovery_scheduler.py \
  --candidates-jsonl /path/to/candidates.jsonl \
  --mode balanced \
  --top-k 10 \
  --out-dir /tmp/mathgraph_discovery_scheduler_custom
```

## Outputs

- `discovery_candidates.csv`
- `ranked_attention.csv`
- `selected_attention.csv`
- `invalid_candidates.csv`
- `taste_policy.json`
- `trust_boundary_audit.json`
- `discovery_scheduler_summary.json`
- `discovery_scheduler_report.md`

## What This Proves

It proves the repository can deterministically rank and audit continuation
candidates while enforcing descension and verifier boundary rules.

## What This Does Not Prove

It does not discover new mathematics, verify claims, synthesize proofs, run
H-tilt, or establish terminal truth.
