# OpenRouter × MathGraph — Disjoint Public SAIR Replication V5

## Result

V5 prospectively replicated the model-acquired verified-reuse result on a
different public SAIR development stream.

Source:

- repository: `SAIRcompetition/equational-theories-lean-stage2`
- pinned commit: `817a4653bf762584931d49c6714c9fcfab7df66a`
- target set: public `normal.jsonl`
- every exact `(eq1_id, eq2_id)` pair in `sample_200` excluded first
- model: `google/gemma-4-31b-it`
- route: OpenRouter → DeepInfra
- run: https://github.com/metalogiclabs/mathgraph/actions/runs/35402563917

After exclusion, the public normal stream contained 500 FALSE and 500 TRUE
problems. The FALSE stream was frozen as:

- first 50: acquisition;
- next 200: fresh evaluation;
- final 250: sealed reserve, untouched in V5.

## Acquisition

Gemma generated countermodel proposals with at most two attempts per acquisition
task. MathGraph independently verified every proposal.

- acquisition tasks: **50**
- verified acquisition tasks: **20**
- distinct promoted tables after deduplication: **3**
- acquisition model calls: **81**
- acquisition tokens: **12,516**
- acquisition cost: **$0.00129103**

The three promoted tables were frozen after this run for the later V6 reserve
confirmation.

## Fresh 200-problem replication

| condition | verified | reuse hits | model calls | tokens | cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| cold | 66/200 | 0 | 200 | 28,777 | $0.00325576 |
| warm | 106/200 | 106 | 94 | 13,515 | $0.00152672 |
| restart | 106/200 | 106 | 94 | 13,515 | $0.00152672 |
| ablation | 66/200 | 0 | 200 | 28,777 | $0.00325576 |

Fresh-set effect:

- **53.0% fewer model calls**
- **53.04% fewer tokens**
- **53.11% lower OpenRouter cost**
- **50.85% less model latency**
- verified terminal yield: **33.0% → 53.0%**

Targeted ablation restored the cold system exactly.

## Acquisition + fresh economics

Including acquisition:

- model calls: **281 → 175** (**37.72% reduction**)
- tokens: **41,293 → 26,031** (**36.96% reduction**)
- cost: **$0.00454679 → $0.00281775** (**38.03% reduction**)
- model latency: **177.0 s → 111.6 s** (**36.94% reduction**)

## Reserve boundary

The final 250 FALSE normal problems were not sent to the model during
acquisition and were not evaluated by the V5 controller. Their IDs were frozen
in the V5 report before V6 was run.

This left an explicit sealed holdout for persistence testing.

## Claim boundary

This is public-development-data evidence, not private SAIR evaluation. It uses
only size-2/3 finite countermodel artifacts and says nothing about TRUE-proof
generation or weight-level model learning.
