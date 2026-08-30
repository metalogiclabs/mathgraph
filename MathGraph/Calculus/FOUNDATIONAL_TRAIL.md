# MathGraph Calculus — Foundational Descent / Reconstruction Trail

Status: active verified reconstruction record

This file records the destructive descent used to identify a minimal operational substrate for the current MathGraph calculus and the constructive ascent from that substrate. Necessity statements are relative to the formal behavior being reconstructed; this is not a metaphysical claim.

## Method

For each descent layer: remove a candidate primitive, preserve the strongest remaining representation, construct the smallest deciding theorem/countermodel, let Lean decide, and record the residual. For each ascent layer: derive the next interface using only already reconstructed lower structure; do not silently reintroduce removed primitives.

A green outer workflow is not itself scientific evidence. The deciding evidence is the Lean invocation and emitted gate in the job log.

## Descent

| Layer | Removed / tested | Deciding result | Classification | Evidence |
|---|---|---|---|---|
| Type-valued identity | Prop-valued identity as primitive | identity data lives below `Prop`; composition/refinement remain constructive | `LEAN_VERIFIED_TYPE_VALUED_IDENTITY_COMPOSITION_AND_REFINEMENT_BELOW_PROP` | commit `fec2001cfc8d8f77931d42fd743fd0c12f58985f`; run `33285422787`; job `99187676912` |
| Directed transport | bidirectionality / symmetry as primitive | one-way transport is reflexive/transitive; typed identity is mutual reachability; reverse direction is not derivable | `LEAN_VERIFIED_DIRECTED_TRANSPORT_PREORDER_WITH_MUTUAL_REACHABILITY_DERIVING_TYPED_IDENTITY` | run `33285738790`; job `99188521990` |
| State equality | equality as consequence of mutual transport | finite Bool countermodel has mutual transport while `false = true -> Empty` | `LEAN_VERIFIED_MUTUAL_TRANSPORT_DOES_NOT_FORCE_STATE_EQUALITY` | commit `035610ad0a015af916c7349c8d47acd537c04b5c`; run `33286434030`; job `99190308736` |
| Coordinate erasure | distinction labels inside witness representation | anonymous pooling creates spurious mutual transport; indexed transport rejects it | `LEAN_VERIFIED_ERASING_DISTINCTION_COORDINATES_CREATES_SPURIOUS_MUTUAL_TRANSPORT` | workflow commit `e64be3cd7dbcffc4c94243aa48c44e4c9af87ca8`; run `33286644577`; job `99190862984` |
| State carrier | explicit `α` labels | states reduce to witness profiles for the transport core; duplicate carrier labels are invisible | `LEAN_VERIFIED_STATE_CARRIER_ELIMINABLE_FROM_TRANSPORT_CORE` | workflow commit `f04a8601f7239f6cbaa65e2626914151f7518b89`; run `33286689100`; job `99190982358` |
| Bare transport algebra | exposed coordinate/profile representation | abstract type-valued `Hom` preserves the core; removing identity loses reflexivity and removing composition loses transitivity | `LEAN_VERIFIED_COORDINATE_FREE_TRANSPORT_ALGEBRA_WITH_IDENTITY_AND_COMPOSITION_NECESSITY` | run `33286953339`; job `99191688130` |
| Raw transport genesis | identity and composition as primitives | free finite paths over raw directed generators generate zero-length identity and composition; closure does not invent reverse edges | `LEAN_VERIFIED_IDENTITY_AND_COMPOSITION_GENERATED_BY_FREE_FINITE_CONTINUATION_FROM_RAW_DIRECTED_POSSIBILITY` | run `33287052469`; job `99191954630` |
| Preliminary rock-bottom test | endpoints and generators | no endpoint carrier gives no packaged continuation; no generators give no cross-endpoint change | `LEAN_VERIFIED_ENDPOINTS_REQUIRED_FOR_ANY_CONTINUATION_AND_RAW_GENERATORS_REQUIRED_FOR_CROSS_ENDPOINT_CHANGE` | run `33287163606`; job `99192245106` |
| **Boundary-typing ablation** | composability/source-target typing while retaining primitive event names | untyped sequencing admits `ab ; cd` although typed paths reject the composite because `b ≠ c`; boundary compatibility carries necessary information | `LEAN_VERIFIED_ERASING_COMPOSABILITY_BOUNDARIES_CREATES_SPURIOUS_CONTINUATION` | run `33287234765`; job `99192438352` |

## Important distinction exposed by the descent

Coordinate erasure and coordinate-free abstraction are compatible:

- **Pooling** coordinate-indexed witnesses forgets relational information and creates false identities.
- **Abstracting** the entire transport relation into a type-valued `Hom` can hide coordinates while preserving the information they carried.

Likewise, explicit endpoint *names* need not be treated as fundamental, but **composability boundary information cannot simply be erased** without admitting spurious continuation.

## Current bedrock candidate

For the present reconstruction target the surviving substrate is represented by a raw typed directed multigraph:

```lean
Ω : Type
G : Ω → Ω → Type
```

`G x y` is raw directed primitive evidence whose indices carry the boundary/composability information. At this floor there is no assumed identity arrow, composition operator, symmetry, state equality, consequence language, separation relation, or algebraic law.

From `G`, `FreePath G` generates finite continuation. Zero steps generate self-continuation; concatenation generates composition; suitable primitive edges generate cross-boundary change; reverse paths are not manufactured without reverse-directed evidence.

This is verified bedrock **relative to the current reconstruction target**, not a claim of unique or metaphysical fundamentality.

## Ascent

### Stage 1 — free continuation → identity, composition laws, refinement

`FreePath` reconstructs identity and composition. Left unit, right unit, and associativity are proved by path recursion rather than assumed. `GeneratedIdentity` is mutual finite continuation. Pointwise primitive generator refinement lifts canonically through paths and preserves generated identity.

Gate: `LEAN_VERIFIED_IDENTITY_AND_REFINEMENT_RECONSTRUCTED_FROM_RAW_DIRECTED_BEDROCK`

Authoritative crossing run: run `33287338158`, job `99192711554` (also reverified subsequently).

### Stage 2 — paths → witness profiles / transport

For endpoint `x`, define the incoming path profile `k ↦ FreePath G k x`. Any path `x → y` transports incoming paths by postcomposition. Conversely, profile transport applied at source `x` to the zero-length path recovers an `x → y` path. Mutual generated identity and mutual incoming-profile transport therefore imply one another constructively.

Gate: `LEAN_VERIFIED_WITNESS_PROFILE_TRANSPORT_RECONSTRUCTED_FROM_BEDROCK_PATHS`

Authoritative run: `33287338158`; job `99192711554`.

### Stage 3 — witness paths → Prop-valued consequence reflection

Reflect each incoming path type to `Nonempty (FreePath G k x)`, producing the original `Language Ω Ω Prop` interface.

- generated identity implies `ConsequentialEq` of the reflected reachability language;
- consequential equality recovers `Nonempty (GeneratedIdentity G x y)` while remaining inside `Prop`;
- extraction of concrete Type-valued generated identity is explicitly isolated behind `Classical.choice`.

Thus the ascent reproduces the logical-reflection boundary exposed on descent instead of hiding witness erasure.

Gate: `LEAN_VERIFIED_PROP_CONSEQUENCE_REFLECTION_FROM_BEDROCK_WITH_EXPLICIT_CHOICE_BOUNDARY`

Authoritative run: `33287408780`; job `99192899839`; workflow commit `7937d68392b869fcae8fed5fa467dea745d404cb`.

## Current dependency trail

```text
raw typed directed evidence / composability boundaries
  -> FreePath finite continuation
  -> generated identity + generated lawful composition
  -> generator refinement lifted to paths
  -> incoming witness profiles
  -> profile transport / mutual typed identity
  -> Nonempty logical reflection
  -> ConsequentialEq
  -> [next] separation / apartness / higher refinement
```

Every further ascent stage must receive its own Lean gate or a finite obstruction explaining why the bridge fails.
