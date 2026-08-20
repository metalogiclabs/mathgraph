# Closure-relative capability growth

## An exact finite witness, its categorical reading, and the remaining open claim

This note states the mathematical object behind the executable reproduction in this directory. The Python program is intended as a finite certificate of the statements below; it is not the definition of the phenomenon.

The purpose is to keep three notions separate:

1. **reachability in a currently installed generative system**;
2. **identity of a capability relative to transformations already available in that system**;
3. **development of the generative system itself**.

A fourth, stronger notion — whether one acquired capability makes a later capability *formable* in a constructor language in which it was previously unformable — is tested separately and is **not** established by this finite example.

---

## 1. Finite state space and old generative system

Let

\[
\Sigma = \{\mathrm{LT},\mathrm{LE},\mathrm{AND},\mathrm{OR},A,B,C,D\}
\]

and let

\[
X = \Sigma^4.
\]

Let the cyclic group

\[
G=C_4=\langle \rho\mid \rho^4=e\rangle
\]

act on \(X\) by cyclic permutation of coordinates. The **old generative system** is the action of \(G\) alone.

For \(x\in X\), define its old closure by

\[
\operatorname{Cl}_0(x)=G\cdot x.
\]

Every element of \(G\) preserves the multiset of tokens. Hence the token multiset is an invariant of \(\operatorname{Cl}_0\).

### Proposition 1 — exact old-closure obstruction

For

\[
x_1=(\mathrm{LT},A,B,C),\qquad
 t_1=(\mathrm{LE},A,B,C),
\]

and

\[
x_2=(A,B,\mathrm{LT},C),\qquad
 t_2=(A,B,\mathrm{LE},C),
\]

we have

\[
t_1\notin \operatorname{Cl}_0(x_1),\qquad
 t_2\notin \operatorname{Cl}_0(x_2).
\]

**Proof.** Every state in the old closure has exactly the same token multiset as its source. Each target replaces one occurrence of \(\mathrm{LT}\) by \(\mathrm{LE}\), so its multiset differs. ∎

This is a structural obstruction, not a search timeout.

---

## 2. Construction language and literal repairs

For a position \(i\in\{0,1,2,3\}\) and distinct tokens \(a,b\in\Sigma\), let

\[
r_{i,a\to b}:X\rightharpoonup X
\]

be the partial map that replaces \(a\) by \(b\) at coordinate \(i\), defined only when coordinate \(i\) contains \(a\).

The finite constructor meta-language contains all such one-site rewrites.

A verifier for a source/target pair \((x,t)\) is the Boolean relation

\[
V_{x,t}(r)=1 \iff r(x)=t.
\]

For the two source cases above, the unique literal verifier-surviving repairs are

\[
r_{0,\mathrm{LT}\to\mathrm{LE}}
\]

and

\[
r_{2,\mathrm{LT}\to\mathrm{LE}},
\]

respectively. Their literal intersection is therefore empty.

---

## 3. Closure-relative capability identity

Literal program identity is not the identity of interest because the old system already knows how to transport coordinates.

Define an equivalence relation on one-site rewrites by the old symmetry action:

\[
r\sim_0 r'
\quad\Longleftrightarrow\quad
\exists g\in G\;\;r'=g\,r\,g^{-1}
\]

where equality is equality of partial maps on \(X\).

A **closure-relative capability** is an orbit

\[
[r]_0 = G\cdot r.
\]

Since coordinate transport is exactly the \(G\)-action,

\[
[r_{0,a\to b}]_0=[r_{i,a\to b}]_0
\]

for every coordinate \(i\).

### Proposition 2 — quotient identity across source-distinct cases

Although the two source cases have no common literal repair, their verifier-surviving repairs determine the same unique closure-relative capability

\[
O_1=[\mathrm{LT}\to\mathrm{LE}]_0.
\]

**Proof.** The two literal repairs differ only by conjugation with a cyclic coordinate permutation. ∎

This is the finite analogue of the claim that capability identity should be relative to the transformations already admitted by the current system, rather than to implementation syntax.

---

## 4. Source-distinct transport and ablation

Consider the held-out case

\[
h=(A,\mathrm{LT},B,C),\qquad
h'=(A,\mathrm{LE},B,C).
\]

Neither literal acquisition repair is identical to the required held-out literal repair at coordinate \(1\). Hence literal-identity transfer fails.

But the retained orbit \(O_1\) contains the transported representative

\[
r_{1,\mathrm{LT}\to\mathrm{LE}},
\]

so quotient transport succeeds.

Removing \(O_1\) removes that capability and restores failure.

Thus the retained object is not a memorised source-position implementation.

---

## 5. Scope as a separate object

Let the observable context set be

\[
C=\{\mathtt{if},\mathtt{json},\mathtt{loop},\mathtt{return}\}.
\]

The frozen scope grammar is

\[
\mathcal S=
\{\top\}\cup\{[c=c_0]\mid c_0\in C\}.
\]

Positive evidence requires the capability in context `if`; protected evidence forbids it in context `json`.

Within \(\mathcal S\), the unique minimal admissible scope is

\[
s_1(c)=[c=\mathtt{if}].
\]

This deliberately separates the capability \(O_1\) from its applicability predicate \(s_1\).

Later counterevidence is introduced inside the `if` scope. Under the frozen grammar \(\mathcal S\), no refinement remains that contains all positive cases while excluding all harmful cases. The lifecycle verdict is therefore **revoke**, rather than silently weakening the evidence standard.

---

## 6. Second generation: developmental discoverability

Now consider

\[
d=(A,\mathrm{LT},B,\mathrm{AND})
\]

with target

\[
d'=(A,\mathrm{LE},B,\mathrm{OR}).
\]

The target contains two independent defects relative to \(d\).

### Proposition 3 — no cold one-rewrite solution

There is no one-site rewrite \(r\) in the frozen constructor language such that

\[
r(d)=d'.
\]

**Proof.** A one-site rewrite changes at most one coordinate, while \(d\) and \(d'\) differ at two coordinates. ∎

The executable audit enumerates all 28 one-site candidates available from \(d\) and finds zero verifier survivors.

Apply the already admitted \(O_1\) first. Since its source token occurs uniquely, its application site is determined from the current state alone; the target is not consulted. We obtain

\[
d_1=(A,\mathrm{LE},B,\mathrm{AND}).
\]

Now exactly one one-site capability class survives the verifier:

\[
O_2=[\mathrm{AND}\to\mathrm{OR}]_1.
\]

Here the subscript reminds us that the identity is being considered relative to the currently installed system.

---

## 7. Exact closure expansion at generation 2

Let \(\mathcal C_0\) be the transition category generated by the old cyclic transports, viewed as partial endomorphisms of \(X\).

Let

\[
\mathcal C_1=\langle \mathcal C_0,O_1\rangle
\]

be the subcategory of \(\mathbf{Par}(X)\) generated by the old transports and all transported representatives of \(O_1\).

Then

\[
d'\notin \operatorname{Reach}_{\mathcal C_1}(d).
\]

One simple invariant is that morphisms in \(\mathcal C_1\) can permute coordinates and can replace \(\mathrm{LT}\) by \(\mathrm{LE}\), but cannot replace \(\mathrm{AND}\) by \(\mathrm{OR}\). Thus the required \(\mathrm{OR}\) token cannot be created.

Adjoining \(O_2\) gives

\[
\mathcal C_2=\langle \mathcal C_1,O_2\rangle
\]

and now

\[
d'\in \operatorname{Reach}_{\mathcal C_2}(d).
\]

Targeted ablations establish both dependencies:

\[
d'\notin \operatorname{Reach}_{\langle\mathcal C_0,O_1\rangle}(d)
\]

and

\[
d'\notin \operatorname{Reach}_{\langle\mathcal C_0,O_2\rangle}(d).
\]

So the final capability is causally dependent on both admitted classes.

---

## 8. Search compression is a consequence, not the definition

Cold exhaustive reconstruction with two literal rewrites considers

\[
28\times 28=784
\]

ordered candidate pairs in this finite world.

After retaining \(O_1\), the second-generation audit considers only 28 one-site candidates, giving

\[
\frac{784}{28}=28
\]

fold search compression.

This is useful operationally, but the mathematical claim is the change in the installed generative structure, not the speedup itself.

---

## 9. The stronger claim is falsified here

There are two different notions of “O2 was unavailable before O1”:

### Verifier-relative discoverability

Under the frozen budget of one newly admitted capability,

\[
\operatorname{Survive}_1(d,d')=\varnothing,
\]

whereas after applying \(O_1\),

\[
\operatorname{Survive}_1(d_1,d')=\{O_2\}.
\]

This **does** hold.

### Raw constructor-language formability

However, the constructor meta-language already contains the syntactic primitive

\[
r_{i,\mathrm{AND}\to\mathrm{OR}}
\]

before \(O_1\) is acquired.

Therefore

\[
O_2\in \operatorname{Form}(M_0)
\]

already, where \(M_0\) is the frozen raw constructor meta-language.

Hence the stronger statement

\[
O_2\notin \operatorname{Form}(M_0)
\quad\text{but}\quad
O_2\in \operatorname{Form}(M_1)
\]

is **false in this experiment**.

This is why the executable verdict is deliberately

`PARTIAL_STRICT_CONSTRUCTIBILITY_NOT_ESTABLISHED`.

The distinction is central: the finite witness demonstrates development of **admissible/reachable capability structure**, not growth of raw syntax.

---

## 10. A categorical formulation of the question

The old system supplies two mathematically different levels.

### Internal computation

Inside a fixed regime \(\mathcal C_t\), a computation is a morphism

\[
x\longrightarrow y
\]

or a composable path of such morphisms.

An ordinary policy/search mechanism chooses among such continuations.

### Developmental change

A developmental event changes the regime itself:

\[
\mathcal C_t\longrightarrow \mathcal C_{t+1}.
\]

In the finite witness,

\[
\mathcal C_0
\hookrightarrow
\mathcal C_1=\langle\mathcal C_0,O_1\rangle
\hookrightarrow
\mathcal C_2=\langle\mathcal C_1,O_2\rangle.
\]

So a natural higher-level object would have **regimes/continuation categories as objects** and verified admissions, restrictions or revocations as morphisms between regimes. This is only a proposed reading, not a claimed final formalism.

The point is that

\[
x\to y\text{ in }\mathcal C_t
\]

and

\[
\mathcal C_t\to\mathcal C_{t+1}
\]

should not be conflated: state evolution and change of continuation structure have different mathematical types.

### Capability identity as an orbit / quotient

For the finite group action, literal repairs are identified under conjugation by already admitted symmetries. One may view this through the action groupoid

\[
G\ltimes X
\]

or as an orbit quotient of partial endomorphisms under \(G\).

The experiment uses the simplest exact orbit construction. A more general theory may need a coequalizer, localization, bicategorical quotient, profunctorial semantics, or another notion of observational equivalence. The experiment does not choose among these.

### Scope

Applicability is indexed by observable context. This suggests an indexed/fibred treatment may be more natural than attaching one global Boolean flag to a capability: a capability can be valid over one part of a context base and invalid over another, and counterevidence can shrink that admissible region or force revocation.

Again, this is a mathematical question raised by the experiment, not a theorem of the toy model.

---

## 11. The real stronger target

The finite witness does **not** establish strict second-order constructibility.

The stronger developmental statement would require constructor regimes \(M_t\) as well as execution regimes \(\mathcal C_t\), with a witnessed transition

\[
M_0 \longrightarrow M_1
\]

caused by an admitted capability \(O_1\), and a later capability \(O_2\) such that

\[
O_2\notin\operatorname{Form}(M_0)
\]

but

\[
O_2\in\operatorname{Form}(M_1).
\]

The hard part is to establish this without baking the conclusion into the constructor definition (for example, by simply defining an `O2` constructor that takes `O1` as an argument).

The real Specimen/Lean lineage is relevant because it already contains a one-generation causal constructibility expansion followed by a qualitatively changed residual. The next question is whether that changed residual can induce a second constructor capability whose *formation itself* depends on the first acquired representation.

---

## 12. Questions this leaves open

The experiment is intended to make the following questions precise enough to disagree about:

1. Is the orbit quotient under already admitted symmetries the right finite prototype of **capability identity**, or should identity be defined through a more semantic universal construction?
2. What categorical structure best separates morphisms **inside** a continuation regime from verified morphisms **between** continuation regimes?
3. Should applicability/scope be represented by an indexed category, fibration, subobject structure, modality, or something else?
4. What is the right compositional notion of revocation? Is it deletion of a generator, restriction of a domain, movement to another object in a category of regimes, or a different construction?
5. What should count as genuine second-order development: changed reachability, changed admissibility, changed constructor formability, or some hierarchy of these notions?
6. Can a categorical RL/state framework model the internal dynamics while a higher-level categorical object models changes of the continuation category itself?

The executable reproduction fixes a tiny world in which the first layer can be answered exactly, while deliberately exposing the boundary at which the stronger question begins.
