# Developmental Capability Growth V1

This is a deliberately tiny, exact experiment for a bounded form of the MathGraph developmental claim:

```text
verified closure failure
  -> machine-checkable obstruction
  -> search a protocol-fixed refinement family
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

This choice is intentional. `T1` is **not itself one of the named candidate refinement features**. That avoids the trivial experiment in which the target label is simply handed to the representation.

`T1` is outside the old closure. The obstruction is exact: inside the odd-parity cell, states that `R0` treats as identical require different outputs. No deterministic function of parity alone can therefore implement `T1`.

The script checks this in two independent ways:

1. **Cell-conflict criterion:** find an `R0` cell containing incompatible required labels.
2. **Literal closure enumeration:** enumerate every Boolean policy on the representation cells and verify that the target truth vector is absent.

The two methods must agree.

## Named refinement family

The executable protocol fixes this one-step named refinement family:

```text
bit0
bit1
bit2
weight
constant_zero
```

Each candidate is appended as one observable coordinate. The world, target, and evaluation procedure stay fixed during a run.

Exactly one member of this named family makes `T1` representable:

```text
bit0
```

This is only a **family-relative** statement. It is not a claim that `bit0` is the unique extension over all possible languages.

The test also verifies that the selected feature's truth vector is not equal to either evaluation target, so the refinement is a distinction used to construct the capability rather than the answer label itself.

## Global audit: all 256 Boolean one-bit refinements

To remove the main possible objection to the small named family, the companion audit:

```bash
python experiments/developmental_capability_growth_v1/audit_all_boolean_refinements.py
```

enumerates **every Boolean one-bit feature on the eight-state world**:

```text
2^8 = 256 possible feature truth vectors
```

The exact result is:

```text
256 tested
 32 repair T1
224 fail
  8 distinct successful induced partition classes
```

Among the 32 successful features, 4 induce a 3-cell refinement and 28 induce a 4-cell refinement.

Most importantly, the audit proves a complete necessary-and-sufficient criterion in this finite setting:

> A Boolean one-bit refinement makes `T1` representable **if and only if** it separates every pair of states that the old representation identifies but the obstruction certificate says require different target labels.

So the obstruction does **not** magically determine one literal feature. It determines a **class of admissible refinements** exactly. That is closer to the real research claim: verified failure can constrain what a successful representational extension must distinguish.

This also makes explicit why the experiment should not be sold as a universal invention theorem. Multiple syntactically different features can induce equivalent or adequate refinements.

## Controls and causal gates

The main run passes only if all of these hold:

1. **Old-closure failure:** `T1` is absent from the complete old closure and has a non-empty conflict certificate.
2. **Unique named-family repair:** exactly one member of the protocol-fixed named family succeeds.
3. **Non-tautological refinement:** the selected feature is not itself the discovery or reuse target label.
4. **Capability gain:** after adding `bit0`, `T1` enters the complete refined closure.
5. **Same-shape sham:** adding `bit1` instead does not make `T1` representable.
6. **Real ablation:** remove `bit0` from the repaired representation; its induced partition must become exactly the original parity partition and the obstruction must return.
7. **Source-distinct reuse:** a second target must fail under the old representation, succeed under the repaired representation, and fail under the sham.
8. **Cross-check consistency:** analytic cell reasoning and brute-force closure enumeration must agree, and formula closure sizes must match enumerated closure sizes.

The global audit additionally requires:

1. all 256 Boolean one-bit features are enumerated;
2. analytic and literal closure tests agree on all 256;
3. successful refinement is exactly equivalent to separating every certified conflict;
4. the success class is non-empty but does not include all refinements.

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

> What compositional object changes when a verified obstruction constrains the admissible refinement class and a chosen refinement expands exact generative closure?

## Run

No third-party dependencies are needed.

Main causal witness:

```bash
python experiments/developmental_capability_growth_v1/run.py
```

Global refinement-class audit:

```bash
python experiments/developmental_capability_growth_v1/audit_all_boolean_refinements.py
```

Both programs print a short human-readable summary followed by a full JSON certificate and exit non-zero on failure.

Expected verdicts:

```text
PASS_BOUNDED_DEVELOPMENTAL_EVENT
PASS_GLOBAL_REFINEMENT_CLASS_AUDIT
```

## Claim boundary

This experiment establishes only a bounded finite result:

- eight states;
- exact finite policy closures;
- a fixed finite named refinement family for the causal witness;
- exhaustive coverage of all 256 Boolean one-bit refinements in the global audit;
- exact obstruction certificates;
- exact sham and ablation tests;
- one source-distinct reuse task.

It does **not** establish:

- a universal method for inventing missing representations;
- that every obstruction admits a consistent extension;
- that any literal refinement feature is globally unique;
- autonomous open-ended developmental intelligence;
- that category theory, RL, optics, or any particular formalism is the correct explanation.

The protocol was constructed as a minimal exact witness; it is not presented as a historically pre-registered prospective experiment. Its value is that the mathematical claims are exhaustively checkable and the overclaim boundaries are explicit.
