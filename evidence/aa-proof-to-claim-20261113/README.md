# Proof-to-claim receipt: an Aaronson–Ambainis case

**13 November 2026 · Independent statement audit, not a new proof of the conjecture**

Kevin Buzzard's [four-question checklist](https://xenaproject.wordpress.com/2026/11/12/and-the-proof-is-checked-in-lean/) separates the informal statement, the build, the comparator, and independent kernels. This case supplies a machine-checkable *positive witness* for an additional part of the first question:

> Given an AI project's formal theorem `P` and an independently formulated interpretation `H` of the external mathematical claim, can we actually check the entailment `P → H`?

## Pinned sources and claim mapping

| Layer | Concrete object | Evidence and boundary |
| --- | --- | --- |
| Historical question | Aaronson–Ambainis, [arXiv:0911.0996v3](https://arxiv.org/abs/0911.0996v3), Conjecture 6 | Human interpretation of `(ε/d)^{O(1)}` required. |
| AI project's theorem | [`AaronsonAmbainis.aaronson_ambainis : PrintedConjecture`](https://github.com/physical-superintelligence/aaronson-ambainis/blob/2a6ceaef872ae993708950f951989134084b851a/AaronsonAmbainis/Conjecture.lean) | Explicit fixed exponent 7. |
| Independently written formal target | [`IndependentAAAudit.OriginalConjecture6`](https://github.com/metalogiclabs/aaronson-ambainis/blob/85adf55b3e9913ae2a239e3ccc1ca9285867bac2/audit/OriginalConjecture6.lean) | Rebuilds the cube, mean, variance, and influences using Mathlib primitives; chooses a uniform positive natural exponent interpretation. |
| Checked bridge | `printed_implies_original : PrintedConjecture → OriginalConjecture6` | Lean checks the **one-way implication**, choosing `k = 7`; `historical_conjecture` applies the project's theorem. |
| Representation change | `signed_variance_eq` and `signed_influence_eq` in the same file | Lean checks the `{0,1}^n` to `{-1,1}^n` scaling, including the squared half-difference convention. |
| Build and audit | [Exact-head Actions run #43210357666](https://github.com/heathsanchez/test/actions/runs/43210357666) | Pinned Lean 4.33.0 / Mathlib build, 87-file static scan, standard axiom report, original-project `leanchecker` replay. **No claim of a second-kernel replay of this adapter.** |

The adapter is in [public PR #2](https://github.com/physical-superintelligence/aaronson-ambainis/pull/2), which remains separate from the original project's proof. It has not been merged or endorsed as the definitive historical interpretation.

## A tiny independent arithmetic control

For a Boolean-cube polynomial `p`, define `f(s) = 2p((s+1)/2)-1` on signed coordinates. With a squared bit-flip influence for `p` and a squared **half-difference** influence for `f`, the intended invariants are:

```
Var(f) = 4 Var(p)
Inf_signed_i(f) = Inf_boolean_i(p)
```

Two standard-library-only Python programs independently evaluate finite truth tables using exact `Fraction` arithmetic:

```sh
python3 PSI_claim_semantic_probe_2026-11-09.py
python3 AA_signed_cube_probe.py
```

Each enumerates `5^4 = 625` coefficient choices for the two-variable multilinear polynomial `a + bx + cy + dxy` over the grid `{-1/2,-1/4,0,1/4,1/2}`. The first compares tuple and packed-bit cube encodings; the second compares direct Boolean and signed-cube evaluations. Neither finite check requires Lean or third-party Python packages.

The decisive positive control is `p(x,y)=(x+y)/2`:

| Observable | `{0,1}²` | `{-1,1}²` |
| --- | ---: | ---: |
| Variance | `1/8` | `1/2` |
| Each coordinate's normalized influence | `1/4` | `1/4` |
| **Mutant:** omit the signed half-difference | — | **`1`** |

The first script also distinguishes `(∃ i)` from the incorrect stronger `(∀ i)` condition on a selective-coordinate witness, and catches a doubled influence denominator. These are controls against recognizable semantic mutations, **not evidence of an error in the reviewed project's source**.

## Precisely what this warrants

- **WARRANTED, native-checked:** At the pinned PR source, Lean accepts a one-way implication from the repository's `PrintedConjecture` to an *independently stated* `OriginalConjecture6` under an explicit historical interpretation, plus general signed-cube normalization lemmas.
- **WARRANTED, finite:** The two independent Python controls agree on their 625 sampled coefficient tuples and detect the specified mutations. This is not an exhaustive proof for all real polynomials.
- **UNKNOWN, external meaning:** Whether the chosen positive-natural-exponent quantification exactly captures the authors' intended `(ε/d)^{O(1)}` needs a domain expert. The paper's downstream quantum query reduction is separate.
- **UNKNOWN, independent adapter kernel:** The original project's `leanchecker` replay did not separately recheck the added bridge in an independent kernel implementation. A native Lean build is not that test.

The distinction is constructive: a **green proof checker** can be supplemented by a separately formulated **claim** and a *checked arrow between them*. A clean comparator/independent-kernel result by itself cannot certify that humans selected the right external question.

For the full trust-boundary and toy canary experiments, see the separate Proof-to-Claim Receipt v2 package. This public case intentionally keeps only the real theorem, its replayable finite controls, and the unresolved boundaries.
