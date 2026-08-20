# From Structured Continuation Calculus to verified regime change

## Status of this note

This note is a **proposed mathematical interface**, not an established theorem of Structured Continuation Calculus.

Its purpose is to isolate the layer that the existing mechanized StrCC development does not yet formalize: verified change of the continuation / constructor regime itself.

The distinction is important:

- existing StrCC gives mathematics **inside a fixed `KnowledgeSystemSignature`**;
- the experiments increasingly manipulate the effective regime from which later continuations are generated;
- the open problem is to identify the correct mathematical object and notion of morphism for that second level.

Nothing below should be read as claiming in advance that the right answer is a category, fibration, double category, optic, profunctor, or categorical RL construction.

---

## 1. The fixed-regime object already present in StrCC

StrCC is parameterized by a `KnowledgeSystemSignature`

\[
S=(\mathrm{Obj},\mathrm{Gen},\mathrm{src},\mathrm{tgt},\mathrm{Reason},
\mathrm{decision},\mathrm{Obs},\mathrm{observe},\mathrm{Claim},
\mathrm{Evidence},\mathrm{Memory}).
\]

For a fixed `S`, permitted primitive generators produce selected paths by identity and typed composition. Later modules construct free categories, presentations and quotients, semantic descent, dependent evidence transport, interaction/coherence, trace normalization, external adequacy, and replay.

Thus one can schematically write

\[
x \xrightarrow{p} y
\]

for lawful continuation **inside** a fixed regime.

This is not the layer currently missing.

---

## 2. What the experiments change

The experimental controller retains or revokes objects such as:

- an executable representation rule;
- a constructor transformation;
- a scope/applicability condition;
- an obstruction certificate;
- a verified capability;
- a routing / promotion law.

After admission, later search is not conducted with exactly the same effective resources as before.

We therefore provisionally distinguish an effective regime from the bare host programming language.

### Definition 2.1 — Effective verified continuation regime (candidate)

A regime is provisionally a tuple

\[
\mathcal R=(S,K,P,V,L),
\]

where:

- `S` is a StrCC-style knowledge-system signature;
- `K` is the currently installed set of executable capability / constructor resources;
- `P` is the frozen admissible proposal-and-composition protocol;
- `V` is the external verifier contract and its information boundary;
- `L` is persistent verified state: admitted laws, scopes, obstructions, provenance and revocations.

The host language in which `K` happens to be implemented is deliberately **not** identified with the effective constructor regime.

This is necessary because Python or Lean metaprogramming may be able to spell an arbitrary patch manually even when that patch is not reachable under the frozen developmental protocol.

---

## 3. Verified future behavior

The ETP future-set work supplies a useful but simpler prototype.

For a preorder object `A`, its future is

\[
F(A)=\{B:A\Rightarrow B\},
\]

and two syntactically different equations are extensionally identified when they have the same future set.

For developmental regimes we need a richer future object because future events can themselves change the regime.

### Definition 3.1 — Bounded developmental future (candidate)

Fix a frozen experimental horizon / resource bound `H`. Define

\[
\Phi_H(\mathcal R)
\]

to be the verifier-certified developmental futures reachable from `R` under the same proposal protocol and verifier boundary within `H`.

An element of `Phi_H(R)` should record more than a solved task. At minimum it may include certified transitions to new regimes:

\[
\mathcal R \rightsquigarrow \mathcal R'.
\]

### Definition 3.2 — Future equivalence (candidate)

\[
\mathcal R \sim_H \mathcal R'
\quad\Longleftrightarrow\quad
\Phi_H(\mathcal R)=\Phi_H(\mathcal R').
\]

This is intentionally only a candidate analogue of the ETP future quotient.

A major open question is what information must be retained in `Phi` for this equivalence to be compositional and representation-independent.

---

## 4. A developmental transition is stronger than an internal continuation

Inside one fixed regime we have ordinary continuation:

\[
x\to y.
\]

The experimental phenomenon asks for a second kind of arrow:

\[
\mathcal R_t \rightsquigarrow \mathcal R_{t+1}.
\]

A verified capability admission should not be called a developmental transition merely because code changed.

### Definition 4.1 — Causal admission witness (candidate)

A transition

\[
\mathcal R \xRightarrow{\Delta} \mathcal R'
\]

has a bounded causal witness when a precommitted experiment establishes, relative to a declared target family and verifier boundary:

1. **baseline obstruction** — the relevant behavior is unavailable under `R`;
2. **intervention** — `Delta` is the only intended regime change;
3. **verified gain** — the behavior is available under `R'`;
4. **protected behavior** — declared protected tests remain valid;
5. **ablation** — removing `Delta` while retaining the rest of the regime restores the relevant failure;
6. **provenance** — task, protocol, intervention and verifier information boundary were frozen before the deciding run.

Transfer, compression and source-distinct held-out success strengthen this witness but do not replace the causal gates.

This is the experimental pattern established for K5 and, separately, for K7S.

---

## 5. Successive admissions are not yet developmental depth

The current public Specimen history contains successive admitted capabilities:

\[
K5 \quad\leadsto\quad K6 \quad\leadsto\quad K7S
\]

in chronological regime state.

That alone does **not** prove

\[
K5 \Rightarrow K6 \Rightarrow K7S
\]

as causal developmental dependence.

In fact the repository contains an important negative control: V159 prospectively attempted to show that admitted K6 moved a later natural reachability frontier, but the chosen target already passed under K2+K5. The result was `NULL_V159_NO_REACHABILITY_MOVEMENT`.

So chronology must not be confused with dependency.

---

## 6. The strong second-order test

The strongest useful next statement is not that the host language could not literally spell a later patch.

It is that the later capability class was unavailable under the **same frozen effective developmental protocol** before the earlier admission, and became available after it.

### Definition 6.1 — Bounded capability-reachability set (candidate)

Let

\[
\mathrm{CapReach}_H(\mathcal R)
\]

be the set of capability classes that can be proposed, externally verified, pass the frozen promotion gates, and enter the retained regime within bound `H`.

### Definition 6.2 — Strict developmental depth (candidate)

A pair of admitted transitions

\[
\mathcal R_0 \xRightarrow{\Delta_1} \mathcal R_1
\xRightarrow{\Delta_2} \mathcal R_2
\]

has strict bounded developmental depth when the same precommitted meta-protocol establishes

\[
[\Delta_2]\notin \mathrm{CapReach}_H(\mathcal R_0)
\]

but

\[
[\Delta_2]\in \mathrm{CapReach}_H(\mathcal R_1),
\]

and ablating `Delta_1` restores the absence of `Delta_2` from the reachable promoted capability set.

This is stronger than:

- `Delta_2` being useful after `Delta_1`;
- a later residual merely appearing chronologically;
- reduced search cost;
- raw source-code formability;
- retrospective human ability to write both patches.

The public evidence does **not yet establish this predicate**.

---

## 7. Why the quotient question matters

A capability should not automatically be identified with one literal implementation.

Let `~_R` be an equivalence relation generated by transformations already lawfully available in regime `R`, together with whatever verified behavioral equivalence is justified by the domain.

Then the developmental object may be a class

\[
[\Delta]_{\mathcal R}
\]

rather than literal source text.

The finite reproduction gives only a trivial group-orbit prototype of this idea. The natural-code quotient experiments are the relevant empirical motivation.

The real mathematical question is whether there is a regime-relative equivalence with sufficient invariance that transfer, ablation and future behavior factor through the quotient.

---

## 8. Scope and revocation belong in the object

The experiments show that capability and applicability are distinct claims.

A retained capability should therefore not be represented solely by an operation `Delta`. A more faithful object is something like

\[
C=(\Delta,\sigma,E^+,E^-,\pi),
\]

where:

- `Delta` is the executable capability;
- `sigma` is its current verified applicability scope;
- `E+` is supporting evidence;
- `E-` is counterevidence;
- `pi` is provenance / verifier-boundary information.

Counterevidence may narrow `sigma` or revoke the capability entirely.

This suggests that any category of regimes must accommodate not only extension but also lawful withdrawal.

---

## 9. Relationship to StrCC

The proposed extension can be stated compactly.

Existing StrCC studies, relative to a fixed signature:

\[
\mathrm{Continuation}(S).
\]

The developmental problem asks for mathematics of something closer to

\[
\mathrm{Regime}(S,K,P,V,L)
\]

and verified transformations

\[
\mathcal R \rightsquigarrow \mathcal R'.
\]

Possible categorical homes include:

- a category whose objects are lawful regimes and arrows are certified regime transformations;
- an indexed or fibered construction separating internal continuation from regime index;
- a double-category / equipment-style separation between internal computations and regime-changing transformations;
- a 2-categorical theory of presentations and semantics;
- or a simpler order-enriched structure if future inclusion is the only invariant that survives experiment.

At present these are **questions, not conclusions**.

The desired formalism should earn its complexity by predicting an experiment or making an invariant visible that simpler state-update language does not.

---

## 10. The question for Daniel

The concrete mathematical question is:

> Starting from StrCC's already-mechanized calculus of lawful continuation relative to a fixed `KnowledgeSystemSignature`, what is the minimal mathematical structure needed to treat verified capability admission/revocation as transformations between continuation regimes themselves? Can such regimes be quotiented extensionally by verified developmental futures, and what conditions make those transformations compositional?

The concrete experimental question is:

> What is the cleanest finite or Lean-realizable model in which an admitted transition `R0 -> R1` can be proved causally necessary for a later capability class to enter `CapReach_H(R1)`, while that class is not in `CapReach_H(R0)` under the same frozen meta-protocol?

A formalism that predicts the right discriminator for that experiment would be substantially more valuable than a categorical redescription of the already-passing toy.

---

## 11. Evidence-status table

| Claim | Current status |
|---|---|
| StrCC continuation mathematics inside a fixed signature | mechanized existing work |
| ETP future-set quotient for a finite implication preorder | exact existing result; underlying preorder theorem standard |
| V54 two-generation bounded discoverability | supported in frozen synthetic/operator experiment |
| K5 causal constructibility expansion | supported in real Specimen Lean substrate |
| K6 scoped capability admission | supported by V158 |
| K6 causally moves the precommitted V159 later frontier | **false / null** |
| upstream issue #9 supplies a clean K6 natural frontier | **rejected by V164B prerequisite failure** |
| K7S bounded natural constructor-development transition | supported by V169B + prior A/B/C causality |
| K6 is causally necessary for K7S acquisition | **not established** |
| strict second-generation `CapReach` expansion | **open** |
| category / fibration / double category of regimes | **open mathematical question** |
