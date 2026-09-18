# Open Math Model × MathGraph — Sustained-Use Evaluation V1

## Purpose

This branch starts a small, falsifiable contribution path for open mathematical AI.

The question is not only whether a model can solve a mathematical task once. The question is whether independently verified discoveries can become reusable capability so that later related work is cheaper **without weakening the verification boundary**.

The evaluation contract is:

```text
propose
→ independently verify/refute
→ promote only authorized evidence
→ restart
→ reuse on fresh tasks
→ compare cold vs warm cost
→ run sham-memory and targeted-ablation controls
```

This is intentionally model-agnostic. Any open or closed model can sit upstream. MathGraph evaluates what happens after proposals are produced.

## Phase 0: exact mechanistic fixture

Run:

```bash
python scripts/run_open_math_model_sustained_use_pilot.py \
  --out-dir /tmp/open_math_model_sustained_use_v1
```

The bounded fixture requires two capabilities to solve a fresh target. The first capability earns authority on source-distinct and held-out cases before promotion.

The evaluator measures:

- **COLD** — exhaustive two-step reconstruction;
- **WARM** — reuse the independently verified first capability, then audit one new capability;
- **SHAM** — retain a same-shaped but noncausal memory object;
- **ABLATION** — remove the promoted capability while preserving the warm one-new-capability budget;
- **RESTART** — serialize and reload the promoted capability before reuse;
- **TERMINAL AGREEMENT** — cold and warm must end at the same independently checked target.

Cost is counted in candidate verifier calls, not wall time or tokens. The report must not upgrade this bounded result into an external-model claim.

Expected bounded result:

```text
cold candidate-verifier calls: 784
warm candidate-verifier calls: 28
compression: 28x
relative reduction: 96.43%
sham solves under warm budget: 0
ablation solves under warm budget: 0
restart: exact
```

## Phase 0B: SAIR-capable adapter

The same command can call the existing real/fallback SAIR compounding benchmark:

```bash
python scripts/run_open_math_model_sustained_use_pilot.py \
  --run-sair \
  --equations-path /path/to/equations.txt \
  --matrix-path /path/to/etp_matrix_full_best_bool.npy \
  --out-dir /tmp/open_math_model_sustained_use_v1
```

If the real files are absent, fallback mode is explicitly labeled and must not be reported as a real SAIR result.

The SAIR adapter preserves the existing MathGraph authority boundary: routing, H-Tilt, Lawbook attention, model output, and search failure are advisory. Only verifier-backed terminal evidence may authorize a mathematical outcome.

## Phase 1: real model pilot

The next step is a small model-facing benchmark with a frozen train/fresh split.

For each task, record at minimum:

- model identifier and exact configuration;
- prompt/input hash;
- model tokens and wall time;
- candidate artifacts proposed;
- verifier calls;
- verifier-backed terminal outcome;
- promoted capability IDs and provenance;
- restart state;
- reuse hits on fresh tasks.

Then compare four conditions on the same fresh task set:

1. **COLD** — no promoted capability memory;
2. **WARM** — only independently verified promoted capabilities;
3. **SHAM** — matched memory volume with noncausal/shuffled capability content;
4. **ABLATION** — remove the promoted capability implicated by the causal ledger.

Primary sustained-use metrics:

- verifier calls per terminal result;
- model tokens per terminal result;
- wall time per terminal result;
- terminal yield at a fixed budget;
- residual count;
- restart-preserved reuse.

A positive result requires warm improvement with terminal correctness preserved, plus failure of the sham explanation and a targeted ablation that removes the gain.

## Claim boundary

This branch is an evaluation protocol and initial bounded fixture. It does **not** claim that an external Open Math Model, SAIR model, GPT model, or any other LLM already shows the same 28× gain.

The point is to make that future claim testable, reproducible, and difficult to fake.
