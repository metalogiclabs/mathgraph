# MathGraph Calculus — Foundational Descent Trail

Status: active verified reconstruction record

This file records the destructive descent used to identify a minimal operational substrate for the current MathGraph calculus, and the evidence that decided each step. It is deliberately narrower than a metaphysical claim: every necessity statement is relative to the formal behavior being reconstructed.

## Method

For each layer:

1. remove a candidate primitive;
2. preserve the strongest remaining representation;
3. construct the smallest deciding theorem or finite countermodel;
4. let Lean decide;
5. record the exact residual and only then descend again.

A green outer workflow is not itself scientific evidence. The deciding evidence is the Lean invocation and emitted gate in the job log.

## Descent

| Layer | Removed / tested | Deciding result | Classification | Evidence |
|---|---|---|---|---|
| Type-valued identity | Prop-valued identity as primitive | identity data can live below `Prop`; reflexivity, symmetry and transitivity are constructive data | `LEAN_VERIFIED_TYPE_VALUED_IDENTITY_COMPOSITION_AND_REFINEMENT_BELOW_PROP` | commit `fec2001cfc8d8f77931d42fd743fd0c12f58985f`; run `33285422787`; job `99187676912` |
| Directed transport | bidirectionality / symmetry as primitive | one-way transport has reflexivity and transitivity; typed identity is mutual directed reachability; reverse direction is not derivable from one-way transport | `LEAN_VERIFIED_DIRECTED_TRANSPORT_PREORDER_WITH_MUTUAL_REACHABILITY_DERIVING_TYPED_IDENTITY` | run `33285738790`; job `99188521990` |
| State equality | underlying equality as consequence of mutual transport | finite Bool countermodel has mutual transport / typed identity while `false = true -> Empty` | `LEAN_VERIFIED_MUTUAL_TRANSPORT_DOES_NOT_FORCE_STATE_EQUALITY` | commit `035610ad0a015af916c7349c8d47acd537c04b5c`; run `33286434030`; job `99190308736` |
| Coordinate erasure | distinction labels inside witness representation | pooling witnesses into one anonymous Sigma type creates spurious mutual transport; indexed transport rejects it | `LEAN_VERIFIED_ERASING_DISTINCTION_COORDINATES_CREATES_SPURIOUS_MUTUAL_TRANSPORT` | workflow commit `e64be3cd7dbcffc4c94243aa48c44e4c9af87ca8`; run `33286644577`; job `99190862984` |
| State carrier | explicit `α` labels | a state can be replaced by its witness profile; directed transport is definitionally pointwise profile transport; duplicate carrier labels are invisible to the core | `LEAN_VERIFIED_STATE_CARRIER_ELIMINABLE_FROM_TRANSPORT_CORE` | workflow commit `f04a8601f7239f6cbaa65e2626914151f7518b89`; run `33286689100`; job `99190982358` |
| Bare transport algebra | exposed coordinate/profile representation | abstract `Hom : Obj -> Obj -> Type` preserves the core without exposing coordinates. Removing identity witnesses loses reflexivity; removing composition loses transitivity | `LEAN_VERIFIED_COORDINATE_FREE_TRANSPORT_ALGEBRA_WITH_IDENTITY_AND_COMPOSITION_NECESSITY` | patch commit `096c1a598fcfad80a975ed2af7d3bdaeb9e26e98`; run `33286953339`; job `99191688130` |
| Raw transport genesis | identity and composition as primitives | free finite paths over raw directed generators generate zero-length identity and concatenative composition; closure does not invent reverse edges | `LEAN_VERIFIED_IDENTITY_AND_COMPOSITION_GENERATED_BY_FREE_FINITE_CONTINUATION_FROM_RAW_DIRECTED_POSSIBILITY` | patch commit `daedc83b251e07dd38f81bfcc15e8749dfd63e35`; run `33287052469`; job `99191954630` |
| Rock bottom ablation | endpoints and raw generators | empty endpoint carrier admits no continuation witness; one endpoint admits zero-length continuation; raw generators are required for cross-endpoint change; one directed generator suffices and does not add symmetry | `LEAN_VERIFIED_ENDPOINTS_REQUIRED_FOR_ANY_CONTINUATION_AND_RAW_GENERATORS_REQUIRED_FOR_CROSS_ENDPOINT_CHANGE` | workflow commit `f0b47127c2ac35b8b55fb4207b3c8fc57d187f00`; run `33287163606`; job `99192245106` |

## Important distinction exposed by the descent

The coordinate-erasure result and the bare-transport result are compatible, not contradictory.

- **Pooling** coordinate-indexed witnesses forgets relational information and creates false identities.
- **Abstracting** the whole pointwise transport relation into a type-valued `Hom` hides the coordinates while preserving the information they carried.

Therefore explicit coordinates are representation-level structure, while directed typed reachability is the lower invariant retained by that representation.

## Current verified floor

The deepest verified input for this reconstruction is a raw typed directed multigraph:

```lean
Ω : Type
G : Ω → Ω → Type
```

`G x y` is raw directed generator data. It has no assumed identity, composition, symmetry, equality, coordinate system, separation relation, or algebraic laws.

From it, `FreePath G` generates finite continuation:

- zero steps generate self-continuation;
- one primitive generator generates a one-step continuation;
- concatenation generates composition;
- no reverse path is manufactured without suitable directed generators.

The rock-bottom claim is operational and relative to the target calculus. It does **not** claim that `Ω` and `G` are metaphysically fundamental or uniquely minimal in every formalism.

## Upward reconstruction rule

The ascent starts from only `Ω` and `G`. A higher concept may enter the reconstruction only when a Lean theorem derives it or when an additional assumption is explicitly named and independently ablated.

Planned dependency direction:

```text
raw endpoints + raw directed generators
  -> free finite continuation
  -> generated identity + composition
  -> mutual reachability / typed identity
  -> generator refinement and lifted path refinement
  -> obstruction / separation when representable
  -> higher consequence and information algebra
```

Every ascent stage receives its own CI gate.
