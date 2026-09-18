# OpenRouter × MathGraph — Sealed Reserve Confirmation V6

## Result

V6 tests whether the exact three-capability bank frozen after V5 still pays on
the final 250 FALSE problems that V5 deliberately left untouched.

No acquisition occurs in V6.

Frozen source:

- V5 source run: `35402563917`
- V5 artifact: `10570398912`
- frozen bank source run SHA: `e0a20cb8a9e40f424229aaff3be7f33afcb13adf`
- V6 qualification run:
  https://github.com/metalogiclabs/mathgraph/actions/runs/35402936630

Before reserve evaluation, every frozen capability was independently rechecked
against the original acquisition task that licensed it.

## Sealed 250-problem reserve

| condition | verified | reuse hits | model calls | tokens | cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| cold | 82/250 | 0 | 250 | 36,221 | $0.00432391 |
| warm | 125/250 | 125 | 125 | 17,997 | $0.00213223 |
| restart | 125/250 | 125 | 125 | 17,997 | $0.00213223 |
| ablation | 82/250 | 0 | 250 | 36,221 | $0.00432391 |

Reserve effect:

- **50.0% fewer model calls**
- **50.31% fewer tokens**
- **50.69% lower OpenRouter cost**
- **52.02% less model latency**
- verified terminal yield: **32.8% → 50.0%**

Restart reproduced warm. Targeted ablation restored cold exactly.

This is important because the three-capability bank was frozen **before** these
250 problems were evaluated.

## Cumulative 500-FALSE normal stream

Combining V5 acquisition, V5 fresh evaluation, and the sealed V6 reserve:

| | cold / no retained reuse | developmental verified reuse |
| --- | ---: | ---: |
| model calls | 531 | 300 |
| tokens | 77,514 | 44,028 |
| OpenRouter cost | $0.00887070 | $0.00494998 |
| model latency | 443.90 s | 239.69 s |

Cumulative reduction:

- **43.50% fewer model calls**
- **43.20% fewer tokens**
- **44.20% lower OpenRouter cost**
- **46.00% less model latency**

Across the 450 post-acquisition FALSE problems, cold produced 148 verified
finite-countermodel results while verified reuse produced 231, with no change
to the exact verification boundary.

## Supported statement

The strongest supported statement from V5–V6 is:

> A small set of model-generated mathematical artifacts, once independently
> verified and frozen, can remain useful across hundreds of later unseen public
> SAIR problems, reducing external model use and increasing the number of
> verifier-backed terminal results. Removing those artifacts restores the cold
> behavior.

The capability is persistent state outside the model. The model does not need
to remember or regenerate the artifact.

## Claim boundary

This remains bounded public-data evidence. It does not establish private SAIR
performance, TRUE-proof generation, universal mathematical coverage, or
weight-level learning inside Gemma.
