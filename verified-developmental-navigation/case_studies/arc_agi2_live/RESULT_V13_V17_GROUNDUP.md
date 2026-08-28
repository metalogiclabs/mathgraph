# ARC ground-up developmental MSI — V13 to V17

## Question

Starting below supplied constructor concepts, can verified future collisions force the representational distinctions needed to separate first-stage states by whether a lawful second-stage continuation exists?

Pinned source: `fchollet/ARC-AGI@399030444e0ab0cc8b4e199870fb20b863846f34`.

Protected targets, frozen from the earlier V4 strict depth-2 gains:

- `0c786b71`
- `59341089`
- `833dafe3`
- `be03b35f`

The continuation boundary is fixed throughout: a first-stage state is an intermediate grid produced by one admitted base program; its protected developmental future is whether one further admitted base-program continuation can satisfy the exact verifier. The second-stage search is capped at 25,000 candidates per first-stage state. No reported run truncated.

The protocol is deliberately bottom-up:

1. quotient first-stage states by the currently available observation language;
2. detect a certified collision when observationally identical states have different verified second-step futures;
3. exhaust the full current observation language before adding anything;
4. add only the smallest next observation family licensed by that exhaustion;
5. retain lawful earlier distinctions rather than replacing them.

No family-pair prior, successful constructor identity, object-role label, left/right concept, or task-specific constructor name is supplied to the learner.

---

## V13 — scalar raw relations

Observation vocabulary: sixteen mechanically computed relations between each intermediate demonstration grid and its required output, including dimensions, area, color-set inclusion/equality and parity relations. V13 initially aggregates each relation across demonstrations.

Every protected task contains both future-positive and future-negative first-stage states, so the old empty quotient is definitely too coarse.

Representative certified collisions include:

- `0c786b71`: future-positive `concat:h_rl:flip_h` versus future-negative `identity`;
- `59341089`: same pattern;
- `833dafe3`: same pattern;
- `be03b35f`: future-positive `rot90` versus future-negative `identity`.

No basis of size <=5 from this scalar vocabulary separates future-success classes on any target; no common basis <=6 was found. This was a bounded subset-search negative, not yet a full-vocabulary impossibility result.

---

## V14b — preserve demonstration-indexed scalar patterns

V14 makes the smallest possible refinement to V13: retain the exact same primitive scalar predicates separately for each demonstration instead of collapsing them with `all(...)`.

Before searching subsets, V14b tests the entire demo-indexed vocabulary. On every protected task, the **full vocabulary itself** contains a positive/negative future collision. Therefore no subset of that vocabulary can possibly separate the verified futures.

Decision:

`DEMO_PATTERN_EXHAUSTED_ON_AT_LEAST_ONE_TASK`

In fact the exhaustion occurs on all four protected tasks.

This rules out dimensions, area, color-set relations, parity, and their per-demonstration patterns as a sufficient developmental interface for these targets.

---

## V15 — generated geometric observation contexts

Licensed by V14's full-vocabulary exhaustion, V15 adds no semantic feature labels. It reuses the already-admitted primitive geometric action carrier as observation contexts:

`identity, rot90, rot180, rot270, flip_h, flip_v, transpose, anti_transpose`.

Each context emits only raw equality bits: whether applying the context leaves the intermediate unchanged, or makes it equal the required output.

The entire V15 context vocabulary still has exact positive/negative future collisions on all four tasks.

Representative collisions sharpen to:

- `0c786b71`: future-positive `concat:h_rl:flip_h` vs future-negative `concat:h_lr:flip_h`;
- `59341089`: same;
- `833dafe3`: same;
- `be03b35f`: future-positive `rot90` vs future-negative `identity`.

So primitive symmetry/fixed-point information is still insufficient.

---

## V16 — raw spatial embedding contexts

V16 is licensed by V15's exact exhaustion. For every primitive geometric image of each original demonstration input, it enumerates every raw integer subgrid offset at which that image could occur in the first-stage intermediate, plus small occurrence-count equality bits.

No semantic placement labels such as `left`, `right`, `top`, `bottom`, `concat`, `role`, or `orientation` are supplied.

This is the first positive emergence signal:

- `0c786b71`: a 4-bit embedding basis separates all future-positive from future-negative states;
- `59341089`: a 2-bit basis;
- `833dafe3`: a 4-bit basis.

For `be03b35f`, however, the complete V16 embedding vocabulary still contains an exact collision: future-positive `separator_tile:0` and future-negative `crop_color:2` are embedding-equivalent under V16.

Decision:

`EMBEDDING_LANGUAGE_EXHAUSTED_ON_AT_LEAST_ONE_TASK`.

At this point it would have been incorrect to invent another concept immediately.

---

## Persistence correction

V14-V16 were useful diagnostic replacement-language probes, but replacement is not the developmental law established by MSI: lawful earlier distinctions should persist when a new observation family is added.

The `be03b35f` V16 collision exposed this protocol bug. The V16-only language forgot scalar color/shape distinctions that were already available earlier.

V17 therefore adds **no new concepts at all**. It restores the cumulative developmental language:

`C17 = demo-indexed scalar relations U primitive geometric equality contexts U raw embedding contexts`.

---

## V17b — cumulative developmental interface

The cumulative language is sufficient on **all four protected tasks**. A greedy residual-separation search followed by exhaustive single-feature backward ablation produces a sufficient, inclusion-minimal basis for each task. Global cardinality minimality is not claimed.

Results:

| task | first-stage states | future-positive | cumulative bits | irreducible basis size | basis families |
|---|---:|---:|---:|---:|---|
| `0c786b71` | 35 | 2 | 672 | 5 | embedding + scalar + geometric-context |
| `59341089` | 64 | 1 | 704 | 2 | embedding + scalar |
| `833dafe3` | 75 | 2 | 472 | 5 | embedding + scalar + geometric-context |
| `be03b35f` | 74 | 12 | 480 | 7 | scalar + embedding + geometric-context |

For every task, the basis separating demonstration-future success is exactly the same basis separating held-out future success. No search truncated.

The unresolved positive/negative pair counts fall to zero under the retained bases. For example:

- `59341089`: 63 -> 2 -> 0 using two retained bits;
- `be03b35f`: 744 -> 372 -> 174 -> 75 -> 30 -> 16 -> 4 -> 0 using seven retained bits.

Each reported bit is individually necessary relative to the final reported basis: removing any one restores at least one verified-future collision.

Decision:

`CUMULATIVE_IRREDUCIBLE_BASIS_ALL_TASKS`.

---

## What emerged, and what did not

The experiment does **not** justify installing a hand-named `constructor prior`, `object relation`, `spatial role`, or `concatenation concept` as the developmental representation.

What is justified is narrower and stronger:

1. the old quotient is falsified by verified developmental futures;
2. scalar observations are insufficient even when preserved per demonstration;
3. primitive geometric self/target contexts are insufficient;
4. raw spatial embedding observations add genuinely necessary distinctions on three tasks;
5. retaining earlier lawful scalar/geometric distinctions together with embedding information is sufficient on all four;
6. the final sufficient interfaces are mixed, task-relative, and irreducible under single-feature ablation.

The key forced principle is therefore **cumulative future-relative sufficiency**, not a particular human semantic ontology.

A developmental interface should be represented as a replayable retained basis of verified distinctions with provenance, not as a frozen partition and not as a single monolithic feature family.

Formally, for stage `t`, active retained basis `B_t`, constructor/continuation language `C_t`, verifier `V`, and budget boundary `H`, the central object should be something like

`Pi_t(x) = (c(x))_{c in B_t}`

with a development step licensed only when a certified future collision remains:

`Pi_t(x) = Pi_t(y)` but `exists f in C_{t+1}: V(f(x)) != V(f(y))`.

The next extension is then admitted only after the full current basis language is shown unable to eliminate that collision.

## Runs / artifacts

- V13 run: `33138329994`, artifact `9672897860`.
- V14b run: `33138459975`, artifact `9672949462`.
- V15 run: `33138583595`, artifact `9672996479`.
- V16 run: `33138651816`, artifact `9673023568`.
- V17b run: `33138823299`, artifact `9673089251`.
