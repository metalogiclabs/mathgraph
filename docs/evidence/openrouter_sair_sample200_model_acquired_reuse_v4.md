# OpenRouter × MathGraph — Public SAIR Model-Acquired Verified Reuse V4

## Result

This is the first experiment in the series that combines all four pieces:

1. a **real model** upstream;
2. **model-generated acquisition artifacts** rather than a preloaded bank;
3. **independent verification before promotion**;
4. **untouched public SAIR Stage 2 problems** downstream.

Configuration:

- public source: `SAIRcompetition/equational-theories-lean-stage2`
- pinned commit: `817a4653bf762584931d49c6714c9fcfab7df66a`
- public set: official `examples/problems/sample_200.json`
- model: `google/gemma-4-31b-it`
- route: OpenRouter → DeepInfra
- temperature: `0`
- seed: `0`
- qualification run: https://github.com/metalogiclabs/mathgraph/actions/runs/35402264089
- artifact: `openrouter-sair-sample200-model-acquired-reuse-v4`

The public answer field was used only to select the 100 known-FALSE problems.
It was not included in any model prompt.

## Frozen split

The 100 public FALSE implications were kept in official sample order:

- first **25**: acquisition;
- remaining **75**: untouched fresh evaluation.

Gemma was allowed at most two independently checked proposals per acquisition
task. A proposal was promoted only if the finite checker established:

```text
source equation holds globally
AND
target equation fails at a concrete witness
```

Finite misses were never interpreted as TRUE.

## Acquisition

Across the 25 acquisition tasks:

- **6 tasks** yielded a verified model-generated countermodel;
- exact-table deduplication produced **4 distinct promoted capabilities**;
- rejected proposals remained rejected.

Acquisition cost:

- **44 model calls**
- **6,864 tokens**
- **$0.00071386 OpenRouter cost**
- **49.46 s model latency**

The bank was serialized and reloaded before fresh evaluation.

## Fresh 75-task result

One cold OpenRouter response was frozen for every fresh task. Warm, restart, and
ablation all use that same frozen response as fallback, so the comparison is
paired rather than based on independent model samples.

| condition | verified results | verified reuse hits | model calls | tokens | OpenRouter cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| cold | 21/75 | 0 | 75 | 10,829 | $0.00124434 |
| warm | 49/75 | 48 | 27 | 3,888 | $0.00045214 |
| restart | 49/75 | 48 | 27 | 3,888 | $0.00045214 |
| ablation | 21/75 | 0 | 75 | 10,829 | $0.00124434 |

Fresh-set effect:

- **64.0% fewer model calls**
- **64.10% fewer tokens**
- **63.66% lower OpenRouter cost**
- **62.10% less model latency**
- verified terminal yield improved from **28.0% → 65.33%**

The gain is not merely cheaper inference. The verified bank resolves many tasks
that the single cold model call fails to solve.

## Causal controls

**Restart** reproduces warm exactly on substantive metrics.

**Targeted ablation** removes every promoted capability that independently
solves the current fresh task. It restores the complete cold behavior:

- 75 model calls;
- 10,829 tokens;
- $0.00124434 cost;
- 21/75 verified outcomes.

Thus the observed warm improvement disappears when the causally relevant
verified artifacts are removed.

## Full acquisition + fresh economics

Charging the acquisition work to both systems:

| | cold / no retained reuse | developmental verified reuse |
| --- | ---: | ---: |
| model calls | 119 | 71 |
| tokens | 17,693 | 10,752 |
| OpenRouter cost | $0.00195820 | $0.00116600 |
| model latency | 109.69 s | 72.28 s |

Amortized reduction:

- **40.34% fewer model calls**
- **39.23% fewer tokens**
- **40.46% lower OpenRouter cost**
- **34.10% less model latency**

So the cost of discovering and verifying the reusable state is already repaid
within the same 100-problem public stream.

## What this establishes

On this pinned public SAIR distribution:

> **A real model can generate mathematical artifacts, independent verification
> can promote the successful ones into persistent capability, and after restart
> those capabilities can solve untouched related problems while substantially
> reducing subsequent model use.**

The important transition is:

```text
probabilistic proposal
→ exact verification
→ promoted reusable artifact
→ persistent capability
→ deterministic reuse before another model call
```

The model is therefore not required to remember or regenerate its earlier
successful work.

## What this does not establish

This is not:

- weight-level learning inside Gemma;
- a result on SAIR's private evaluation set;
- a TRUE-implication proof experiment;
- universal coverage of the 75 fresh problems;
- evidence that size-2/3 finite countermodels are sufficient in general;
- a claim that every verified artifact should be globally prioritized.

The prior cross-set transfer experiment already showed the last point is false:
verified artifacts can be mathematically valid yet economically irrelevant in a
different target regime. Scope still matters.

## Reproduction boundary

The experiment pins the public SAIR commit, records every acquisition attempt,
provider usage, every promoted table and witness, every cold response, every
fresh route, restart state, and the ablation result.

The complete evidence artifact is produced by GitHub Actions run
`35402264089`.
