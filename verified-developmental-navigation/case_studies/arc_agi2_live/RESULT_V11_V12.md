# ARC natural Pi -> K causal test — V11 / V12

## Question

Can retained developmental state causally move a source-distinct depth-2 constructor inside a fixed verifier budget on real ARC data?

Pinned source: `fchollet/ARC-AGI@399030444e0ab0cc8b4e199870fb20b863846f34`.

Protected targets were frozen from the earlier V4 strict depth-2 held-out gains:

- `0c786b71`
- `59341089`
- `833dafe3`
- `be03b35f`

Primary later-constructor budget: **1,000 candidate verifications**.

---

## V11 — old task-signature interface

The retained V3-style interface ranked single-step families using the task signature `(dimension relation, color relation, demonstration count)`. The same retained ordering was then used to navigate depth-2 constructor search.

Result:

| arm | successes <=1000 | ranks on four protected targets | mean rank |
|---|---:|---|---:|
| WARM_RETAINED_PI | 0/4 | 1131, 1239, 2444, 1622 | 1609.0 |
| RAW_HISTORY_RECONSTRUCT | 0/4 | 1131, 1239, 2444, 1622 | 1609.0 |
| COLD_GLOBAL | 1/4 | 2123, 1831, 2352, 142 | 1612.0 |
| SHAM_REVERSED_PI | 1/4 | 3566, 3449, 3925, 255 | 2798.75 |

Decision:

`STRICT_PI_TO_K_GATE = false`

`RAW_HISTORY_RECONSTRUCTS_WARM_RANKS = true`

The current task-level MSI is therefore a valid compression of prior routing evidence, but it is **not constructor-relative enough to causally move the depth-2 constructor frontier** under the frozen 1,000-check boundary.

---

## Residual from V11

The interface was learned for the wrong future.

It predicts which **single-step family** is useful. The protected target is a **two-step constructor**. A sufficient interface for one continuation language need not remain sufficient when the continuation language changes.

This is the natural analogue of the arithmetic developmental-MSI result: enlarging the future language exposes a distinction the old interface did not preserve.

---

## V12 — constructor-relative interface

V12 changed only what prior experience was compressed around.

Training protocol:

- 400 ARC-AGI-1 training tasks.
- Exclude tasks already reachable by the frozen depth-1 language.
- 378 base-failed tasks remain eligible.
- For each eligible task, permit one bounded depth-2 developmental episode with a 5,000-candidate ceiling.
- 8/378 episodes discover a held-out-valid depth-2 constructor.
- Retain a family-pair prior over those verified constructor futures.
- No protected evaluation task is used to learn this prior.

Result:

| arm | successes <=1000 | ranks on four protected targets | mean rank |
|---|---:|---|---:|
| WARM_CONSTRUCTOR_PI | **3/4** | 300, 545, 556, 1429 | **707.5** |
| GLOBAL_CONSTRUCTOR_PRIOR | **3/4** | 300, 545, 556, 1429 | **707.5** |
| COLD_SINGLESTEP_PRIOR | 1/4 | 1412, 1385, 1556, 541 | 1223.5 |
| SHAM_REVERSED_CONSTRUCTOR_PI | 2/4 | 4118, 834, 5629, 31 | 2653.0 |

Decision produced by the frozen V12 script:

`STRICT_CONSTRUCTOR_RELATIVE_PI_GATE = true`

The retained constructor-relative law raises bounded success from **1/4 to 3/4** against the old single-step prior, while a matched reversed law reaches only **2/4**.

However, the task-signature-conditioned WARM arm is exactly equal to the GLOBAL_CONSTRUCTOR_PRIOR arm on all four protected targets. Therefore the strongest warranted interpretation is:

> **Verified constructor experience can be compressed into a retained constructor-relative law that causally moves later constructor discovery under a fixed verifier budget. The present task-signature quotient adds no demonstrated value beyond that global constructor law.**

This is stronger than V11, but it is not yet evidence that the current ARC task signature is the minimal sufficient developmental interface.

---

## Repo consequence

The next MSI object should be future-relative not only to ordinary task outcomes, but to **developmental futures**.

For developmental state `s`, constructor language `K`, verifier `V`, and budget `B`, define a bounded developmental future signature such as

`DevFuture_B(s) = { k in K_B | V(k(s)) = success }`.

Then quotient developmental states by equality of their protected constructor futures:

`s ~^dev_B t  iff  DevFuture_B(s) = DevFuture_B(t)`.

This directly encodes the V11 falsification: two task states may be equivalent for single-step routing while being inequivalent for depth-2 constructor discovery.

The software API should therefore separate:

1. ordinary behavioural continuations;
2. developmental/constructor continuations;
3. retained compiled interfaces/laws;
4. reconstruction cost from raw history;
5. causal ablation under a frozen budget.

A future natural gate should test a learned **conditional developmental quotient** whose classes predict constructor futures better than the global constructor prior, with WARM / GLOBAL-LAW / RAW-HISTORY / COLD / SHAM arms.

## Runs

- V11: `33137738891`, artifact `9672678978`.
- V12: `33137865021`, artifact `9672754330`.
