# Developmental Capability Growth V1

This is a minimal exact experiment for the strongest bounded form of the MathGraph developmental claim:

```text
verified closure failure
  -> obstruction certificate
  -> constrained representation refinement
  -> previously unavailable capability
  -> sham control
  -> ablation
  -> reuse on a source-distinct target
```

The point of this experiment is **not** to show that a missing representation can always be derived from a failure. It cannot. The point is to isolate a finite setting in which the current generative closure is exactly enumerable, the obstruction is machine-checkable, a frozen family of possible representational refinements can be searched without changing the target, and the causal effect of the selected distinction can be tested exactly.

## World

The world is all 3-bit states:

```text
000 001 010 011 100 101 110 111
```

The initial representation deliberately quotients these states by parity only:

```text
R0(x) = parity(x)
```

A deterministic generator/policy that sees only `R0` can therefore express only Boolean functions that are constant on the two parity cells. The complete finite generative closure has size `2^2 = 4`.

The discovery target is:

```text
T(x) = first_bit(x)
```

`T` is not merely missed by a particular search procedure. It is **outside the complete policy closure induced by R0**. A certificate consists of representation cells containing states with incompatible required outputs. For example, states of equal parity can require different values of `first_bit`, so no function of parity alone can implement the target.

## Frozen refinement family

Before evaluation, the test freezes the one-step refinement family:

```text
bit0
bit1
bit2
weight
constant_zero
```

Each candidate is added as one extra observable coordinate to the representation. The target and finite world remain fixed.

The experiment exhaustively asks which one-feature refinements make `T` enter the resulting generative closure. In this world, `bit0` is the unique successful member of the frozen one-feature family.

This is deliberately a **relative minimality claim**: minimal only within the frozen single-feature family. It is not a universal theorem that the obstruction uniquely determines an extension in arbitrary mathematics.

## Causal gates

The run passes only if all gates hold:

1. **Verified old-closure failure.** The discovery target is absent from the exhaustively enumerated old closure, with a non-empty conflict certificate.
2. **Constrained refinement.** Exactly one member of the frozen one-feature family removes the obstruction: `bit0`.
3. **Capability gain.** Under `parity + bit0`, the previously unreachable discovery target enters the exact generative closure.
4. **Sham control.** A same-shape irrelevant distinction (`bit1`) does not rescue the target.
5. **Ablation.** Removing the new distinction restores the original impossibility.
6. **Source-distinct reuse.** A second target, `bit0 == parity`, is outside the old closure, enters the repaired closure, and is not rescued by the sham distinction.

The expected verdict is:

```text
PASS_BOUNDED_DEVELOPMENTAL_EVENT
```

## Why this is the core test

Ordinary learning can update parameters, scores, memories, or a policy over already available actions. This experiment isolates a stronger event:

```text
G0  ->  G1
```

where `G0` and `G1` are different **generative representation systems**. The target is not in the closure of `G0`; a verifier exposes why; the representation is refined; and the closure of `G1` contains capabilities that literally did not exist in the old quotient.

The continuation space changes as a consequence of the representational change, but the scientific object being tested is stronger than continuation reranking: **verified representational capability growth**.

A useful mathematical question is therefore:

> What is the minimal compositional object that changes when a verified obstruction causes a representational refinement that expands generative closure?

In categorical language, one possible future interpretation is that the change is not merely an update to state inside a fixed category of actions, but a change to the structure that determines which continuations/morphisms are representable. This experiment intentionally does not assume that interpretation; it provides a small exact object against which proposed formalisms can be tested.

## Run

No dependencies are required beyond Python 3.10+.

```bash
python experiments/developmental_capability_growth_v1/run.py
```

The program prints the full JSON certificate/report and exits non-zero if any gate fails.

## Claim boundary

This experiment establishes only a bounded finite result:

- the world is exactly eight states;
- the old and refined closures are exactly enumerable;
- refinement search is restricted to a frozen finite one-feature family;
- the test demonstrates causal representational capability expansion, not autonomous open-ended invention;
- it makes no claim that every verified obstruction determines a unique or even consistent extension.

Its purpose is to provide a rigorous minimal testbed for theories of developmental intelligence, verified capability growth, changing generative closure, and changing continuation structure.
