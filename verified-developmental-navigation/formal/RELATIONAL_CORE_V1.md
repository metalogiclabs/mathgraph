# Relational Core V1 — first-principles claim audit

This document deliberately starts below quotient, factorization, policy, utility, or ontology language.

## 0. Primitive data

Let:

- `X` be a set of situations.
- `C` be a set of available continuations/interventions/probes.
- `O` be a set of verifier-visible outcomes.
- `V ⊆ X × C × O` be the verified continuation relation.
- `K ⊆ O` be the protected outcome set, or more generally let `Π` be any protected predicate/property on verifier-visible outcomes.

For a fixed situation `x` and continuation `c`, define its protected consequence profile

`P(x,c) := { o ∈ O | V(x,c,o) and Π(o) }`.

For a family `B ⊆ C`, define protected observational equivalence

`x ≡_B y  :⇔  ∀ c∈B, P(x,c)=P(y,c)`.

No quotient is assumed. No policy is assumed. No total factor map is assumed.

## 1. Immediate theorems

### T1 — Reflexivity
`x ≡_B x`.

### T2 — Symmetry
`x ≡_B y ⇒ y ≡_B x`.

### T3 — Transitivity
`x ≡_B y ∧ y ≡_B z ⇒ x ≡_B z`.

Hence `≡_B` is an equivalence relation whenever it is defined by equality of protected continuation profiles.

### T4 — Evidence monotonicity
If `B ⊆ B'`, then

`x ≡_{B'} y ⇒ x ≡_B y`.

So adding protected continuations can only preserve or refine this equivalence; it cannot create new identifications.

### T5 — Order-independence
For any `B1,B2 ⊆ C`,

`≡_{B1∪B2} = ≡_{B2∪B1}`.

More generally accumulation is associative and idempotent because it is conjunction/intersection over continuation tests.

### T6 — Separator witness
If `x ≢_B y`, then there exists `c∈B` with `P(x,c) ≠ P(y,c)`.

This is merely unpacking the negation of the universal definition in finite/classically decidable settings; constructively it should be stated with a witnessed separation premise rather than inferred from negation alone.

### T7 — Sufficient basis
A subset `B* ⊆ C` is sufficient for a target protected equivalence `E*` iff

`x E* y  ⇔  ∀ c∈B*, P(x,c)=P(y,c)`.

Any two sufficient bases induce the same extensional interface `E*` even if their syntactic members differ.

## 2. What is *not* yet a theorem from these primitives

The following do **not** follow without extra assumptions:

1. That `P(x,c)` must be binary.
2. That one unique smallest continuation basis exists.
3. That a unique maximally compressed interface exists for arbitrary set-valued action compatibility.
4. That capability expansion always refines the interface.
5. That a counterexample licenses an arbitrary separator.
6. That the full continuation family `C` is necessary for convergence.
7. That a low-information representation is computationally cheapest.
8. That the protected relation is fixed over time.

Each of these requires either an extra condition or a counterexample boundary.

## 3. Minimal falsifiers

### F1 — Full-future equality is stronger than decision sufficiency
Find `x,y` with different continuation profiles but the same protected decision requirement. This falsifies the claim that all future differences must be retained.

### F2 — Non-unique maximal compression under existential compatibility
Use acceptable-action sets

- `A(x1)={a}`
- `A(x2)={b}`
- `A(x3)={a,b}`

Then `{x1,x3}|{x2}` and `{x1}|{x2,x3}` are incomparable maximally compressed viable interfaces.

### F3 — Capability expansion need not refine decision equivalence
Add an action that becomes jointly optimal across states previously requiring different actions.

### F4 — Unsound separator overfits
Construct `x,y` with identical protected continuation semantics but an auxiliary predicate `q` with `q(x)≠q(y)`. Adding `q` preserves training distinctions but introduces an unnecessary split.

## 4. The strongest currently justified sentence

> A representation may identify two situations only when every protected continuation test retained by the system treats them equivalently.

For the full protected family `C`, the induced relation is

`x ≡_C y ⇔ ∀ c∈C, P(x,c)=P(y,c)`.

A distinction is forced exactly when some protected continuation supplies a separator.

## 5. Developmental update

At time `t`, let `B_t ⊆ C_t` be the accumulated protected continuation basis.

The induced interface is `E_t := ≡_{B_t}`.

A verified new continuation `c` changes the interface only where it separates a previously equivalent pair:

`x E_t y` and `P(x,c)≠P(y,c)`.

Then

`E_{t+1} := E_t ∩ ker(P_c)`

where `ker(P_c)` denotes equality of the protected profile under continuation `c`.

This is the exact merge/split law in the extensional relational case: evidence accumulates by intersection of indistinguishability relations.

## 6. Convergence notion

For a fixed target protected relation `E*`, a developmental trajectory converges extensionally when there exists `T` such that for all `t≥T`, `E_t=E*`.

Different continuation orders and different sufficient bases may converge to the same `E*`.

A minimal basis is inclusion-minimal among `B` with `≡_B = E*`.

A minimum basis is minimum-cardinality (or minimum-cost under an explicit cost function) among such `B`.

These are distinct notions.

## 7. Candidate mathematical structures that should be derived, not imposed

From the above primitives we may later derive, when assumptions warrant:

- equivalence relations and quotient sets,
- partition lattices / refinement orders,
- closure operators on evidence families,
- separating families / bases,
- factorization through quotient maps,
- bisimulation-like equivalence for dynamic continuation semantics,
- Galois connections between evidence families and induced distinctions.

None is primitive in V1.

## 8. Audit rule

Every future prose claim must be tagged as one of:

- THEOREM from the relational core,
- THEOREM with explicit additional assumptions,
- FINITE EXHAUSTIVE RESULT,
- EMPIRICAL RESULT,
- CONJECTURE,
- FALSIFIED.

The story is downstream of this ledger, never upstream.
