# Closure-relative capability growth

## Exact finite witness and categorical question

This note states the mathematical object behind the executable reproduction. The Python program is a finite certificate of the statements below; it is not the definition of the phenomenon.

The experiment deliberately separates:

1. **reachability** in a fixed generative regime;
2. **capability identity** modulo transformations already present in the old regime;
3. **developmental change** of the regime itself;
4. the stronger question of whether development changes what the constructor language can *form at all*.

The first three are witnessed here in a bounded setting. The fourth is explicitly **not** established.

---

## 1. Old regime

Let

\[
\Sigma=\{\mathrm{LT},\mathrm{LE},\mathrm{AND},\mathrm{OR},A,B,C,D\},
\qquad X=\Sigma^4.
\]

Let

\[
G=C_4=\langle \rho\mid \rho^4=e\rangle
\]

act on \(X\) by cyclic coordinate permutation.

For \(x\in X\), the old closure is

\[
\operatorname{Cl}_0(x)=G\cdot x.
\]

Every old transformation preserves the token multiset.

### Proposition 1 — exact old-closure obstruction

For

\[
x_1=(\mathrm{LT},A,B,C),\quad
 t_1=(\mathrm{LE},A,B,C)
\]

and

\[
x_2=(A,B,\mathrm{LT},C),\quad
 t_2=(A,B,\mathrm{LE},C),
\]

we have

\[
t_1\notin\operatorname{Cl}_0(x_1),
\qquad
t_2\notin\operatorname{Cl}_0(x_2).
\]

**Proof.** The old action preserves token multiset, while each target replaces one \(\mathrm{LT}\) with \(\mathrm{LE}\). ∎

This is an obstruction theorem in the finite world, not a failure of search.

---

## 2. Constructor language

For coordinate \(i\in\{0,1,2,3\}\) and distinct tokens \(a,b\in\Sigma\), let

\[
r_{i,a\to b}:X\rightharpoonup X
\]

be the partial map replacing \(a\) by \(b\) at coordinate \(i\), defined when that coordinate contains \(a\).

The frozen one-step constructor language contains all such maps.

For a source/target pair \((x,t)\), the external verifier returns

\[
V_{x,t}(r)=1\iff r(x)=t.
\]

For the two source cases above, the unique literal survivors are respectively

\[
r_{0,\mathrm{LT}\to\mathrm{LE}}
\quad\text{and}\quad
r_{2,\mathrm{LT}\to\mathrm{LE}}.
\]

Their literal-program intersection is empty.

---

## 3. Capability identity relative to old symmetry

Literal identity is too fine because the old regime already knows how to transport coordinates.

Let \(G\) act on one-site partial rewrites by conjugation:

\[
g\cdot r = g\,r\,g^{-1}.
\]

Define

\[
r\sim_G r'
\iff
\exists g\in G\; r'=g\,r\,g^{-1}.
\]

A **closure-relative capability class** in this witness is an orbit

\[
[r]_G.
\]

Because coordinate position is transportable by \(G\),

\[
[r_{0,a\to b}]_G=[r_{i,a\to b}]_G
\]

for every coordinate \(i\).

### Proposition 2 — quotient identity

The two source cases determine the same unique class

\[
O_1=[\mathrm{LT}\to\mathrm{LE}]_G.
\]

**Proof.** Their two literal survivors are conjugate under a cyclic coordinate permutation. ∎

An independently implemented constructor grammar checks the same point in a genuinely different syntax: instead of arbitrary-position rewrites, it permits only a rewrite at slot \(0\) conjugated by old cyclic transport,

\[
\rho^{-k};r_{0,a\to b};\rho^k.
\]

Both grammars recover the same unique orbit class \(O_1\) across both source cases.

---

## 4. Held-out transport and ablation

For

\[
h=(A,\mathrm{LT},B,C),
\qquad
h'=(A,\mathrm{LE},B,C),
\]

neither acquisition literal is the required coordinate-1 program, so literal identity does not transfer.

But

\[
r_{1,\mathrm{LT}\to\mathrm{LE}}\in O_1,
\]

so orbit transport succeeds. Removing \(O_1\) removes the capability and restores failure.

The retained object is therefore not the literal source implementation.

---

## 5. Scope is separate from capability

Let the observable context base be

\[
C=\{\mathtt{if},\mathtt{json},\mathtt{loop},\mathtt{return}\}
\]

with frozen scope grammar

\[
\mathcal S=\{\top\}\cup\{[c=c_0]\mid c_0\in C\}.
\]

Positive evidence requires \(O_1\) under `if`; protected evidence forbids it under `json`. The unique minimal surviving predicate is

\[
s_1(c)=[c=\mathtt{if}].
\]

Later counterevidence occurs inside `if`. Under the frozen grammar, no scope remains satisfying all help/harm constraints, so the lifecycle verdict is **REVOKE**.

Thus acquisition of \(O_1\) and validity of its applicability predicate are distinct claims.

---

## 6. Reachability categories

To keep state transitions and operator syntax type-distinct, define a thin transition category from a family of partial state transformations.

### Definition

For a set \(F\) of partial endomaps on \(X\), let \(\mathcal C(F)\) be the preorder-category whose objects are states \(x\in X\), with a unique arrow

\[
x\longrightarrow y
\]

iff some finite composable word in transformations from \(F\) is defined at \(x\) and sends \(x\) to \(y\).

Let

\[
F_0=G
\]

(where elements of \(G\) are viewed as total state transformations), and let

\[
F_1=F_0\cup O_1
\]

where \(O_1\) denotes all transported literal representatives in its orbit. Write

\[
\mathcal C_0=\mathcal C(F_0),
\qquad
\mathcal C_1=\mathcal C(F_1).
\]

This category forgets path multiplicity and retains exactly the reachability relation needed by the finite experiment. A richer theory could preserve proof/program paths instead.

---

## 7. Second generation

Consider

\[
d=(A,\mathrm{LT},B,\mathrm{AND}),
\qquad
d'=(A,\mathrm{LE},B,\mathrm{OR}).
\]

### Proposition 3 — cold one-step obstruction

There is no one-site rewrite \(r\) satisfying

\[
r(d)=d'.
\]

**Proof.** A one-site rewrite changes at most one coordinate, while \(d\) and \(d'\) differ at two. ∎

The executable audit enumerates all 28 one-site candidates available from \(d\) and finds zero verifier survivors.

Now reuse \(O_1\). Its source token occurs uniquely, so the application location is determined from the current state alone; the target is unavailable to the capability application mechanism. This yields

\[
d_1=(A,\mathrm{LE},B,\mathrm{AND}).
\]

From \(d_1\), the same 28-way one-step audit has one surviving orbit class:

\[
O_2=[\mathrm{AND}\to\mathrm{OR}]_G.
\]

The quotient still uses the fixed old symmetry group \(G\); what is relative to generation 1 is the **closure/reachability test**, not a newly asserted equivalence relation.

Let

\[
F_2=F_1\cup O_2,
\qquad
\mathcal C_2=\mathcal C(F_2).
\]

### Theorem 4 — exact generation-2 closure expansion

\[
d\not\longrightarrow d'
\quad\text{in }\mathcal C_1,
\]

while

\[
d\longrightarrow d'
\quad\text{in }\mathcal C_2.
\]

Furthermore the final reachability disappears if either \(O_1\) or \(O_2\) is removed.

**Proof.** Transformations in \(F_1\) can cyclically permute tokens and replace \(\mathrm{LT}\) by \(\mathrm{LE}\), but cannot create an \(\mathrm{OR}\) token from \(\mathrm{AND}\). Hence \(d'\) is unreachable in \(\mathcal C_1\). Adding \(O_2\) supplies the missing second change. Either single ablation leaves one required token change unavailable. ∎

This is the exact sense in which \(O_2\) is closure-expanding **relative to generation 1**.

---

## 8. Search compression

Cold exhaustive reconstruction with two literal rewrites considers

\[
28^2=784
\]

ordered candidate pairs.

After retaining \(O_1\), the complete one-step audit considers 28 candidates:

\[
784/28=28.
\]

The resulting 28× compression is an operational consequence of retained structure, not the definition of capability growth.

---

## 9. The stronger claim is falsified

Two claims must be separated.

### Developmental discoverability

Under the frozen one-new-capability budget,

\[
\operatorname{Survive}_1(d,d')=\varnothing,
\]

but after reusing \(O_1\),

\[
\operatorname{Survive}_1(d_1,d')=\{O_2\}.
\]

This **holds**.

### Raw constructor formability

Let \(M_0\) be the original one-site rewrite meta-language. It already contains terms of the form

\[
r_{i,\mathrm{AND}\to\mathrm{OR}}.
\]

Therefore

\[
O_2\in\operatorname{Form}(M_0)
\]

before \(O_1\) is acquired.

So the stronger claim

\[
O_2\notin\operatorname{Form}(M_0)
\quad\text{but}\quad
O_2\in\operatorname{Form}(M_1)
\]

is **false in this witness**.

That falsification is deliberately part of the result. The toy demonstrates development of verified reachability/admissibility, not growth of raw syntax.

---

## 10. The categorical question

The finite model now exposes two different kinds of arrow without conflating their types.

### State evolution inside a fixed regime

For fixed \(t\), computation is represented by arrows

\[
x\to y
\quad\text{in }\mathcal C_t.
\]

A search or policy selects continuations internal to that regime.

### Development of the regime

The evidence also induces a sequence of different reachability categories

\[
\mathcal C_0,
\mathcal C_1,
\mathcal C_2.
\]

The developmental question concerns whatever higher-level structure should represent transitions such as

\[
\mathcal C_t\rightsquigarrow\mathcal C_{t+1},
\]

including admission, restriction and revocation. The symbol \(\rightsquigarrow\) is intentionally neutral: the experiment does not assume these regime changes are ordinary functors, inclusions, optics, profunctors, 2-cells, or something else.

This is precisely where a categorical formulation becomes substantive rather than decorative.

---

## 11. Capability identity beyond the toy

The finite witness uses a literal group action, so orbit identity is exact:

\[
[r]_G.
\]

A general developmental system will not usually have such a simple symmetry group. The corresponding identity question could require a universal or observational construction: for example an action groupoid, coequalizer, localization, bicategorical quotient, profunctorial equivalence, or another notion entirely.

The experiment leaves that choice open.

Likewise, applicability is indexed by context. That raises a separate question of whether scope is naturally represented by a fibration/indexed category, subobject structure, modality, or some other construction in which counterevidence restricts or destroys the admissible region.

---

## 12. Stronger second-order development

The open target needs constructor regimes \(M_t\) as well as execution regimes \(\mathcal C_t\).

A strict second-order result would require an admitted \(O_1\) that causally changes the constructor regime

\[
M_0\rightsquigarrow M_1
\]

and a later capability \(O_2\) satisfying

\[
O_2\notin\operatorname{Form}(M_0),
\qquad
O_2\in\operatorname{Form}(M_1).
\]

The hard part is to establish this without making it tautological by defining an `O2` constructor that simply takes `O1` as a hard-coded argument.

The real Specimen/Lean lineage is relevant because it already shows one causal constructibility expansion followed by a qualitatively changed residual. The remaining question is whether the next constructor capability can be made genuinely unformable before the first representation change and formable after it.

---

## 13. Questions for the formalism

1. Is the old-symmetry orbit the right prototype of closure-relative capability identity, or is a more semantic universal construction preferable?
2. What categorical object should have continuation regimes \(\mathcal C_t\) as its states while keeping internal arrows \(x\to y\) distinct from developmental transitions between regimes?
3. Is applicability naturally fibred/indexed over context?
4. What is the compositional meaning of revocation?
5. Should “development” form a hierarchy: changed reachability, changed admissibility, changed representation, changed constructor formability?
6. Can categorical RL model the internal agent/environment dynamics while another categorical layer models verified changes of the continuation regime itself?

The executable reproduction fixes a tiny world in which the lower layer is exact and the boundary to the stronger problem is explicit.
