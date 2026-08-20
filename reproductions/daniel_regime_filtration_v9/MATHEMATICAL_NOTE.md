# Candidate mathematics of verified developmental regimes

This note is a synthesis of the finite evidence, not a claim of new category theory.

The empirical motivation is deliberately narrow:

- V6: installing a verified reusable law changed which later laws were constructible under a fixed AST budget, while macro expansion proved the unbounded semantic closure was unchanged;
- V7: on a frozen finite suite, the installed law changed the set of semantic behaviors reachable by size `H=5` from 23 to 26, while both regimes saturated to the same 32 unbounded behaviors;
- V8: with sparse obstruction evidence, the next minimum-complexity regime is generally not unique: the obstruction determines a version space of admissible successors.

These observations suggest that a developmental state should retain both **resource-indexed future structure** and **admissible successor structure**.

## 1. Verified regime

For present purposes write a regime as

\[
R=(\Sigma,\mathcal P,V,K,\kappa),
\]

where:

- `Sigma` is the current typed/object signature;
- `P` is the current constructor/program language;
- `V` is an external verifier semantics;
- `K` is the installed set of retained verified capabilities;
- `kappa` is the frozen resource/cost measure on constructor terms.

Nothing here says that all real systems decompose uniquely this way. The tuple only makes the experimental boundary explicit.

Let `Beh(R)` denote verifier-equivalence classes of semantic behaviors produced by well-formed programs in `R`.

## 2. Future filtration

For a resource bound `H`, define

\[
F_H(R)
=\{[\llbracket p\rrbracket]_V : p\in\mathcal P_R,\;\kappa_R(p)\le H\}.
\]

Then

\[
F_0(R)\subseteq F_1(R)\subseteq F_2(R)\subseteq\cdots
\]

is the **verified future filtration** of the regime.

The unbounded extensional behavior space is

\[
F_\infty(R)=\bigcup_H F_H(R).
\]

### Resource-indexed future equivalence

Define

\[
R\sim_H R' \iff F_H(R)=F_H(R').
\]

and, more strongly,

\[
R\sim_{\mathrm{fil}}R'
\iff
F_H(R)=F_H(R')\quad\text{for every }H.
\]

Two regimes may therefore have equal unbounded semantics but distinct developmental filtrations:

\[
F_\infty(R)=F_\infty(R')
\quad\text{while}\quad
F_H(R)\subsetneq F_H(R')
\]

for some finite `H`.

This is exactly the distinction isolated by V6/V7. It is intentionally weaker than claiming new absolute semantic expressivity.

## 3. Regime extension

A verified regime extension

\[
f:R\longrightarrow R'
\]

should minimally include a semantics-preserving translation of old programs into the new regime.

If the old program language is literally a sublanguage of the new one and the cost of old programs is unchanged, then

\[
F_H(R)\subseteq F_H(R')
\]

for every `H`.

More generally, if translation can distort cost, attach a monotone resource map

\[
\phi_f:\mathbb N\to\mathbb N
\]

such that

\[
F_H(R)\longrightarrow F_{\phi_f(H)}(R').
\]

This makes explicit a point hidden by ordinary semantic equivalence: a retained abstraction can preserve unbounded semantics while changing the resource geometry of future construction.

## 4. Obstruction does not generally determine one successor

Let `omega` be verifier-certified negative information relative to `R`.

Define the admissible successor version space

\[
\mathcal V(R,\omega)
=
\{R' : R'\text{ extends }R\text{ and satisfies the frozen verifier obligations induced by }\omega\}.
\]

A deterministic developmental rule would select one element of this set.

V8 is evidence that uniqueness cannot be assumed even in tiny finite worlds. Sparse incompatibility evidence can admit many equally coarse successor quotients. Thus the mathematically grounded consequence of obstruction is generally

\[
\omega\quad\leadsto\quad\mathcal V(R,\omega),
\]

not

\[
\omega\quad\leadsto\quad R'\text{ uniquely}.
\]

The creative/heuristic policy may remain responsible for choosing among the surviving extensions. Verification constrains the choice and later evidence may revoke it.

This matches the distinction that motivated the programme: the next proposal need not be mathematically derivable for the obstruction itself to impose mathematically exact restrictions on what a successful proposal may be.

## 5. Minimal categorical structure forced so far

The current finite evidence does **not** require higher category theory.

At minimum one can form a category (often just a preorder in the finite examples) `Reg` whose:

- objects are verified regimes;
- arrows are verified semantics-preserving regime extensions/compilations;
- composition is composition of the corresponding translations/evidence-preserving updates.

For every resource bound `H`, the future assignment behaves like a monotone observable

\[
F_H:\mathrm{Reg}\to\mathbf{Poset}
\]

in cases where regime extension preserves old programs and their cost.

The entire family

\[
R\mapsto (F_H(R))_{H\in\mathbb N}
\]

is a filtered invariant of the regime.

V5 motivates quotienting literal implementations when two syntactically different programs have the same verified behavior. V7 motivates retaining the whole resource filtration rather than only the colimit `F_infinity`.

## 6. Relation to Structured Continuation Calculus

StrCC already provides a calculus of continuations relative to a fixed knowledge-system signature. Denote the internal continuation category associated with regime `R` by

\[
\mathcal C_R.
\]

The new question is not how to construct ordinary arrows inside one `C_R`, but how verified regime extensions transport internal continuation structure:

\[
R\to R'
\qquad\text{and potentially}\qquad
\mathcal C_R\to\mathcal C_{R'}.
\]

If future work shows that every regime morphism induces a functor between the corresponding continuation categories, then `R -> C_R` becomes an indexed/categorical assignment. If this assignment is pseudofunctorial, its Grothendieck construction would package regime state and internal continuation in one ordinary category.

If internal continuations and developmental transitions must remain genuinely different arrow types, a double-category formulation may eventually be more natural. Nothing in V1–V8 yet forces that additional structure.

## 7. Relation to ETP future quotients

ETP identifies objects extensionally when they have the same verified future behavior. The present finite analogue is only a candidate:

\[
R\sim_H R'\iff F_H(R)=F_H(R').
\]

V7 tests this bounded definition in one finite DSL family. It does **not** transfer the ETP theorem to developmental systems or establish that `F_H` is the uniquely correct notion of intelligent state.

The stronger candidate invariant is the whole filtration

\[
(F_H(R))_H,
\]

possibly enriched by the admissible-successor assignment

\[
\omega\mapsto\mathcal V(R,\omega).
\]

## 8. Developmental event

The strongest bounded notion currently supported is therefore not “the system learned something.”

A verified developmental event is a regime transition

\[
R\to R'
\]

such that:

1. old verified behavior is preserved under the frozen trust boundary;
2. for at least one finite resource bound `H`,
   \[
   F_H(R)\subsetneq F_H(R');
   \]
3. the difference is causally attributable to the retained verified capability under the frozen protocol;
4. its applicability conditions remain separately falsifiable and revocable.

Absolute semantic growth would additionally require

\[
F_\infty(R)\subsetneq F_\infty(R'),
\]

which V6/V7 explicitly do not establish.

## 9. The next mathematical/experimental boundary

The remaining question is recursive.

Can a transition

\[
R_0\to R_1
\]

change not merely `F_H(R)` for object-level laws, but the future version spaces of **later regime transformations themselves**?

In other words, for an appropriate bounded developmental future operator `DF_H`, can we establish

\[
DF_H(R_0)\subsetneq DF_H(R_1)
\]

with prospective ancestor ablation and a natural typed substrate?

That is the point at which the phrase “development changes what can develop next” becomes mathematically distinct from ordinary cached abstraction or first-order partition refinement.

## 10. Question for Daniel

The finite experiments suggest three objects rather than one:

1. an internal continuation category `C_R` for each fixed regime;
2. a filtered future invariant `(F_H(R))_H` measuring what is constructible at each resource scale;
3. for each verified obstruction `omega`, a version space `V(R,omega)` of admissible successor regimes.

What is the least categorical structure that makes these three pieces compositional without assuming that an obstruction uniquely determines its successor?

A category/preorder of regimes plus an indexed family may already suffice. A fibration, Grothendieck construction, or double category should only be introduced if additional transport/coherence laws force it.
