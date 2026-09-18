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


## Phase 1 harness now implemented

The branch now includes a provider-neutral, model-facing benchmark:

```bash
python scripts/run_model_sustained_use_eval.py \
  --provider deterministic \
  --out-dir /tmp/open_math_model_sustained_use_v1/model-pilot
```

The deterministic provider is **CI qualification only**. It is explicitly marked
`provider_is_external_model=false` and must never be reported as an LLM result.

The model-facing protocol uses four training implications. A proposed finite
magma table is independently checked. Only a table for which the source equation
holds globally and the target equation is actually violated is promoted into the
capability bank.

Fresh tasks are then evaluated under five conditions:

- `cold`: no capability bank;
- `warm`: independently verified promoted capabilities are available by compact ID;
- `restart`: the capability bank is serialized, reloaded, and used again;
- `sham`: the same memory shape and summaries are supplied with deliberately
  corrupted payloads as a negative control;
- `ablation`: all promoted capabilities that independently solve the current
  fresh task are removed before the attempt.

A model may return either a new table or a compact reuse reference:

```json
{"table": [[0, 0], [1, 1]]}
```

or:

```json
{"reuse_id": "cap_0123456789abcdef"}
```

The second form is the key sustained-use mechanism: a model need not regenerate
a previously verified mathematical object. MathGraph resolves the identifier and
rechecks the object against the new task.

### Frozen external-model transcript format

External-model runs enter the evaluator as JSONL. One row is required for every
`(mode, task_id)` requested by the benchmark. This keeps the evidence immutable
and lets independent users replay the mathematical verification without access
to the original model.

A row has this shape:

```json
{
  "mode": "warm",
  "task_id": "fresh_assoc_not_comm",
  "model": "provider/model-version",
  "candidate": {"reuse_id": "cap_0123456789abcdef"},
  "raw": "{\"reuse_id\":\"cap_0123456789abcdef\"}",
  "usage": {
    "input_tokens": 210,
    "output_tokens": 12,
    "total_tokens": 222
  },
  "latency_ms": 840.4
}
```

Replay:

```bash
python scripts/run_model_sustained_use_eval.py \
  --provider transcript \
  --transcript /path/to/frozen_model_run.jsonl \
  --out-dir /tmp/open_math_model_sustained_use_v1/external-model
```

Token reduction is reported only when the transcript contains provider-reported
usage. Otherwise the evaluator reports exact prompt/response byte counts but
does not upgrade those proxies into token claims.

### Evidence required before contacting SAIR with a result

A sendable result should have all of the following:

1. a named model/version and frozen transcript;
2. independently verified terminal outcomes for every counted success;
3. exact cold/warm/restart/sham/ablation task manifests;
4. provider-reported token usage for any token-cost claim;
5. restart-preserved reuse;
6. a warm gain that is absent or reduced under sham/ablation;
7. the full claim boundary beside the headline number.

That produces an evaluation artifact rather than a demonstration that depends on
trusting either the model or MathGraph's routing heuristics.
