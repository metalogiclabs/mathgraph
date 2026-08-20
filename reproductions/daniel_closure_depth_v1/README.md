# Daniel Reproduction — Closure-Relative Developmental Depth V1

This is the minimal standalone reproduction of one bounded developmental phenomenon from the MathGraph / Triskelion research line.

It is deliberately small enough to inspect line by line. It requires only Python 3.10+: no API keys, model calls, network calls after cloning, hidden datasets, or third-party packages.

## Run

```bash
git clone https://github.com/metalogiclabs/mathgraph.git
cd mathgraph
python reproductions/daniel_closure_depth_v1/reproduce.py
```

A successful run ends with:

```text
=== REPRODUCTION VERIFIED ===
independent oracle: MATCH
14/14 core gates: PASS
O1: [LT -> LE]
cold O2 survivors: 0/28
after O1, O2: [AND -> OR]
O2 outside G1 semantic closure: PASS
both targeted ablations: FAIL as required
presentation invariance: 24/24
search compression: 784 -> 28 (28x)
later counterevidence: REVOKE
core verdict: PASS_DISCOVERABILITY_DEPTH
strict raw constructibility: NOT ESTABLISHED (intended falsification)
```

## The mathematical question

Let `G0` be a frozen generative system. A verified failure may show that a target is outside `Cl(G0)`. After admitting a new closure-relative capability class `O1`, the effective system becomes `G1`.

The experiment asks two different questions:

1. Does retaining `O1` change what later capability can be *verifiedly discovered* under the same bounded search protocol?
2. Does retaining `O1` change what later capability can even be *formed by the raw constructor meta-language*?

The answer here is **yes to (1), no to (2)**. Keeping those claims separate is part of the experiment.

## Verifier / constructor boundary

The constructor can enumerate one-token rewrites. The verifier alone decides whether a candidate exactly reaches the target.

Once a capability class has been admitted, applying it does **not** receive the target. `transport_apply` sees only the retained class and the current state. In the frozen cases the capability source token occurs exactly once, so its application site is determined without target access. If that uniqueness condition fails, transport returns no application.

This is intentional: target knowledge must not leak from the verifier into capability application.

## Generation 1 — capability identity relative to closure

The old language can only cyclically transport token positions. It preserves token multiset exactly.

Two acquisition cases require the same semantic change at different positions:

```text
S1: LT A B C  ->  LE A B C
S2: A B LT C  ->  A B LE C
```

Their literal repairs are different positional programs, so literal identity has empty intersection. Quotienting by transformations already available in `G0` removes position as an identity distinction and yields the same unique class:

```text
O1 = [LT -> LE]_(G0)
```

A third held-out position is solved by transporting the class, while literal-identity reuse fails. Targeted ablation restores failure.

The same class is also recovered under an alternate constructor presentation and under all 24 bijective renamings of the four semantic role tokens, mapped back to the original presentation.

A frozen context grammar independently selects `context == if` as the unique minimal non-global applicability scope.

## Generation 2 — developmental discoverability

The second target has two independent defects:

```text
A LT B AND  ->  A LE B OR
```

With the same one-new-capability budget, cold search tests 28 rewrites and has **0 verifier-surviving candidates**.

Retained `O1` is then applied without target access:

```text
A LT B AND  ->  A LE B AND
```

The same 28-way one-rewrite search now exposes one unique surviving class:

```text
O2 = [AND -> OR]_(G1)
```

The script exhaustively computes the semantic closure of old transport plus `O1` and verifies that the final target is still outside `Cl(G1)`. `O2` is therefore genuinely closure-expanding relative to `G1`, rather than merely a cheaper route already in that closure.

Final success requires both classes: ablate either `O1` or `O2` and the final target fails.

For this finite world, exhaustive cold two-rewrite reconstruction considers 784 literal pairs; after retaining `O1`, the complete one-rewrite audit considers 28 candidates: 28x search compression.

## Lifecycle / revocation

A later counterexample appears inside the learned `if` scope. Under the frozen context-only scope grammar there is then no surviving scope refinement, so the decision is:

```text
REVOKE
```

not “retain the useful capability somehow”.

## Independent reproduction oracle

`EXPECTED.json` is a frozen reproduction oracle separate from the generated experiment output path.

The wrapper checks, in this order:

1. committed `RESULT.json` agrees with `EXPECTED.json` before execution;
2. the experiment regenerates `RESULT.json` from `run.py`;
3. regenerated output agrees with the independently frozen oracle;
4. all 14 headline predicates and the strict-constructibility falsification are rechecked explicitly;
5. the original committed result bytes are restored so a fresh checkout remains clean.

The original capstone result commit is:

```text
df795a6446ec884b40d4760e230d7776a3032e39
```

## Claim boundary

This is an exact **synthetic finite witness**, not the natural-code evidence and not a claim of open-ended self-improvement.

It supports, inside this frozen world:

- exact old-closure obstruction;
- closure-relative rather than literal capability identity;
- held-out positional transport and causal ablation;
- presentation/constructor-description robustness;
- independently scoped applicability and later revocation;
- two-generation verifier-dependent discoverability;
- exact semantic closure obstruction for `O2` relative to `G1`;
- measurable search compression.

It deliberately **does not** claim that `O2` was impossible to spell in the original generic rewrite meta-language. It was already syntactically available. `O1` changes what becomes verifier-surviving under the bounded developmental protocol, not the raw syntax of that meta-language.

The stronger unresolved target is **strict second-generation constructibility** on a real constructor substrate: an acquired capability must causally enable formation/typechecking/generation of a later capability that the previous constructor substrate genuinely could not construct.

That stronger question is why this reproduction should be read together with the real Specimen/Triskelion lineage, not as a replacement for it.
