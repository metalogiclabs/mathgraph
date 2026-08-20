# Developmental Capability Growth V1

This is a deliberately tiny, exact experiment for a bounded form of the MathGraph developmental claim:

```text
verified closure failure
  -> machine-checkable obstruction
  -> search a frozen refinement family
  -> a new representational distinction removes the obstruction
  -> the target becomes constructible
  -> a same-shape sham does not
  -> removing the distinction restores the failure
  -> the distinction supports a second task
```

The purpose is not to prove that every failure tells us how to invent the right representation. It does not. The purpose is to create a finite world in which every relevant claim can be checked exhaustively, so proposed mathematical formalisms of "development" have a clean object to explain.

## The world

There are exactly eight states:

```text
000 001 010 011 100 101 110 111
```

The initial representation sees only parity:

```text
R0(x) = parity(x)
```

So the eight states collapse to two representation cells: even parity and odd parity.

Any Boolean policy operating only on `R0` must be constant on each cell. Therefore the **complete** policy closure has exactly:

```text
2^2 = 4
```

Boolean functions. This is not a sampling claim; the script enumerates all four.

## Discovery target

The discovery target is:

```text
T1(x) = bit0(x) AND parity(x)
```

This choice is intentional. `T1` is **not itself one of the candidate refinement features**. That avoids the trivial experiment in which the target label is simply handed to the representation.

`T1` is outside the old closure. The obstruction is exact: within at least one parity cell there are states that the old representation treats as identical but for which `T1` requires different outputs. No deterministic function of parity alone can therefore implement `T1`.

The script checks this in two independent ways:

1. **Cell-conflict criterion:** find an `R0` cell containing incompatible required labels.
2. **Literal closure enumeration:** enumerate every Boolean policy on the representation cells and verify that the target truth vector is absent.

The two methods must agree.

## Frozen refinement family

Before evaluating the target, the source code fixes this one-step refinement family:

```text
bit0
bit1
bit2
weight
constant_zero
```

Each candidate is appended as one observable coordinate. The world, target, and evaluation procedure stay fixed.

The result required by the protocol is that exactly one member of this frozen one-feature family makes `T1` representable:

```text
bit0
```

This is a **relative minimality** claim. The baseline uses zero extra features and fails; among the precommitted one-feature candidates, exactly one succeeds. Nothing here claims that `bit0` is the unique possible mathematical extension over all conceivable languages.

The test also verifies that the selected feature's truth vector is not equal to either evaluation target, so the refinement is a distinction used to construct the capability rather than the answer label itself.

## Controls and causal gates

The run passes only if all of these hold:

1. **Old-closure failure:** `T1` is absent from the complete old closure and has a non-empty conflict certificate.
2. **Unique bounded refinement:** exactly one member of the frozen one-feature family succeeds.
3. **Non-tautological refinement:** the selected feature is not itself the discovery or reuse target label.
4. **Capability gain:** after adding `bit0`, `T1` enters the complete refined closure.
5. **Same-shape sham:** adding `bit1` instead does not make `T1` representable.
6. **Real ablation:** remove `bit0` from the repaired representation; its induced partition must become exactly the original parity partition and the obstruction must return.
7. **Source-distinct reuse:** a second target must fail under the old representation, succeed under the repaired representation, and fail under the sham.
8. **Cross-check consistency:** analytic cell reasoning and brute-force closure enumeration must agree, and formula closure sizes must match enumerated closure sizes.

## Reuse target

The second target is:

```text
T2(x) = bit0(x) OR parity(x)
```

`T2` is different from `T1`, but it uses the same newly exposed first-coordinate distinction together with the already-visible parity distinction.

The required pattern is:

```text
R0                 : T2 impossible
R0 + bit0          : T2 possible
R0 + sham(bit1)    : T2 impossible
```

This is deliberately modest evidence of reuse: one discovered distinction participates in more than the task that selected it. It is not a claim of broad transfer or open-ended generalization.

## What exactly changes?

Before refinement, the generator can only implement functions constant on the parity quotient:

```text
G0 = Boolean policies on cells(R0)
```

After refinement:

```text
R1(x) = (parity(x), bit0(x))
G1 = Boolean policies on cells(R1)
```

The induced partition is finer, so the exact generative closure expands. `T1` and `T2` are absent from `G0` and present in `G1`.

That is the bounded phenomenon being tested:

```text
verified representational capability growth
```

The change in possible continuations is a consequence of the representational refinement; the experiment does not assume that "continuation space" is the correct ultimate mathematical formalism.

A useful question for a categorical/proof-theoretic treatment is therefore:

> What compositional object changes when a verified obstruction justifies a refinement of representation and the exact generative closure expands?

## Run

No third-party dependencies are needed.

```bash
python experiments/developmental_capability_growth_v1/run.py
```

The program first prints a short human-readable summary, then a full JSON certificate. It exits with status 1 if any gate fails.

Expected final line in the summary:

```text
VERDICT:            PASS_BOUNDED_DEVELOPMENTAL_EVENT
```

## Claim boundary

This experiment establishes only a bounded finite result:

- eight states;
- exact finite policy closures;
- a fixed finite one-feature refinement family;
- exact obstruction certificates;
- exact sham and ablation tests;
- one source-distinct reuse task.

It does **not** establish:

- a universal method for inventing missing representations;
- that every obstruction admits a consistent extension;
- that the selected refinement is globally unique outside the frozen family;
- autonomous open-ended developmental intelligence;
- that category theory, RL, optics, or any particular formalism is the correct explanation.

Those are research questions. This experiment is the minimal exact object they must explain without overclaiming.
