# OpenRouter × MathGraph — Compiled Verified Reuse V2

## Result

A real OpenRouter run was completed with:

- model: `google/gemma-4-31b-it`
- provider: `DeepInfra`
- temperature: `0`
- seed: `0`
- MathGraph branch: `open-math-model-sustained-use-v1`
- qualification run: https://github.com/metalogiclabs/mathgraph/actions/runs/35401390886
- evidence artifact: `openrouter-compiled-verified-reuse-v2`

The experiment uses a paired design: OpenRouter is called once for each of the
seven frozen fresh tasks to create the cold baseline. Warm, restart, sham, and
ablation reuse those exact same frozen model responses as fallback. This removes
cross-condition model-sampling noise.

## System boundary

MathGraph checks the verified capability bank before invoking the model.

```text
fresh task
→ inspect authorized verified capability bank
→ independently check candidate capability against this task
→ if valid: return verified artifact, no model call
→ otherwise: pay for the frozen OpenRouter fallback
```

This is compiled verified reuse. It is not weight-level learning by Gemma.

## Observed result

| condition | verified results | reuse hits | model calls | total tokens | OpenRouter cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| cold | 7/7 | 0 | 7 | 919 | $0.00010708 |
| warm | 7/7 | 7 | 0 | 0 | $0 |
| restart | 7/7 | 7 | 0 | 0 | $0 |
| sham | 7/7 | 6 | 1 | 133 | $0.00001538 |
| ablation | 7/7 | 0 | 7 | 919 | $0.00010708 |

The authorized warm bank therefore produced, on this bounded fixture:

- **100% fewer model calls**;
- **100% fewer model tokens**;
- **100% lower OpenRouter inference cost**;
- **100% less model latency**;
- exact terminal correctness preserved at **7/7**;
- exact restart preservation;
- targeted ablation restored the complete cold cost.

The controller itself performed 15 exact finite-verifier checks across the seven
warm tasks. Those local deterministic checks replace seven external model calls.

The sham control is intentionally same-shaped but payload-corrupted memory. It
still happened to contain tables that independently solve six of the seven
tasks, so the checker legitimately reused those six artifacts. It therefore
cost 133 tokens for the one residual task rather than zero. This is useful:
MathGraph does not reject a capability because it came from a sham control;
it accepts only the concrete mathematical behavior that independently verifies.

## Relation to OpenRouter V1

The first direct prompt-memory experiment used 35 OpenRouter calls across
cold/warm/restart/sham/ablation. It showed that putting verbose capability
summaries directly into the model prompt was the wrong interface:

- cold: 887 tokens, 6/7 verified;
- warm: 3574 tokens, 7/7 verified, 4 explicit reuse IDs;
- restart: 3568 tokens, 7/7 verified;
- sham: 3577 tokens, 5/7 verified;
- ablation: 2401 tokens, 5/7 verified.

So direct prompt injection improved terminal yield but cost roughly 4× the cold
token budget. That failure motivated V2.

V2 compiles verified capability outside the LLM context. The model is used only
for unresolved work. This changes the sustained-use economics from
"tell the LLM everything we learned again" to "do not call the LLM when an
already-authorized capability settles the task."

## Claim boundary

This is a bounded seven-task system experiment with a preauthorized verified
finite-magma bank and a real OpenRouter/DeepInfra Gemma baseline.

It establishes that, on this fixture, compiling verified artifacts into the
controller can eliminate repeated model calls while preserving independently
checked results.

It does **not** establish:

- weight-level learning or memory inside Gemma;
- that all mathematical tasks will be covered by prior verified capabilities;
- that the same 100% reduction holds on SAIR's private evaluation set;
- that local finite verification is free;
- that the bank was itself acquired by Gemma in this V2 experiment.

The next stronger experiment should make capability acquisition itself
model-generated, independently verify promotion, restart, and then measure
model-call avoidance on untouched related tasks.
