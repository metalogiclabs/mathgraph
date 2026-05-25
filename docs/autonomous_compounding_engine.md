# Autonomous Compounding Engine

The autonomous compounding engine is a repo-native entry point for the serious
ETP finite-recovery path. It has two modes:

- `facade`: the stable compatibility path over the existing finite-core
  compounding runner.
- `native_v2`: the repo-native finite recovery, residual repair, and advisory
  Lawbook reuse loop.

It wraps `scripts/run_mathgraph_compounding_engine.py` rather than simulating
recovery in `facade` mode. The `native_v2` path uses the finite magma
satisfaction cache directly:

```text
constructor bank -> SAT cache -> generic route -> residual repair
-> PQ-IR obstruction naming -> advisory Lawbook reuse -> compact atlas route
```

## Boundary

- FALSE recovery is counted only when a constructor satisfies the source law and
  violates the target law.
- TRUE controls audit contamination.
- Failed finite search is residual evidence, never TRUE.
- PQ-IR, route policies, residual obstructions, and repair family memory are
  advisory until a verifier/checker boundary accepts a terminal form.

## Tiny demo

```bash
python scripts/run_autonomous_compounding_engine.py \
  --out-dir /tmp/mathgraph_autonomous_demo \
  --tiny-demo \
  --episodes 2 \
  --sample-pairs 80 \
  --repair-budget 20
```

Native v2 smoke:

```bash
python scripts/run_autonomous_compounding_engine.py \
  --out-dir /tmp/mathgraph_autonomous_v2_tiny \
  --tiny-demo \
  --finite-core-mode native_v2 \
  --episodes 3 \
  --sample-pairs 80 \
  --repair-budget 20 \
  --max-n 3 \
  --seed 20260524 \
  --write-report
```

## Real ETP / SAIR run

```bash
python scripts/run_autonomous_compounding_engine.py \
  --equations /content/equations.txt \
  --matrix /content/etp_matrix_full_best_bool.npy \
  --out-dir /content/drive/MyDrive/SAIR_MathGraph/Autonomous_Run \
  --episodes 4 \
  --sample-pairs 4000 \
  --repair-budget 40
```

Native v2 real ETP example:

```bash
python scripts/run_autonomous_compounding_engine.py \
  --equations /content/equations.txt \
  --matrix /content/etp_matrix_full_best_bool.npy \
  --out-dir /content/drive/MyDrive/SAIR_MathGraph/autonomous_v2_real \
  --finite-core-mode native_v2 \
  --episodes 4 \
  --sample-pairs 4000 \
  --repair-budget 40 \
  --max-n 4 \
  --constructor-limit 500 \
  --seed 20260524 \
  --write-report
```

The runner refuses real mode unless the equation and matrix files are supplied.
