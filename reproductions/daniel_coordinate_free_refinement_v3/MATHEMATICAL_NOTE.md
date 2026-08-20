# Coordinate-free obstruction-driven regime synthesis

This finite note moves one level below the earlier `Expose(S)` witness.

The aim is narrow:

> can a verified obstruction synthesize the **extension instance itself** when the developmental constructor is not given named coordinate-extension candidates?

The answer is yes in this finite quotient-refinement model. The generic act of partition refinement is still supplied, so this is **not** autonomous invention of the refinement schema.

## 1. Base regime

Let `W` be an 8-element set. For readability the executable file enumerates it as `{0,1}^3`, but the developmental constructor receives only opaque state indices.

The base observation regime is a partition

\[
P_0=B_0\mid B_1,
\qquad |B_0|=|B_1|=4.
\]

A Boolean target

\[
f:W\to 2
\]

is formable in a regime `P` exactly when it factors through the quotient map

\[
q_P:W\to W/P,
\]

i.e. when `f` is constant on every block of `P`.

Thus the object language associated to `P` is extensionally the Boolean algebra

\[
2^{W/P}.
\]

## 2. Verifier obstruction

For a current regime `P`, define the conflict relation

\[
\Omega_P(f)
=
\{\{u,v\}:u\sim_P v,\; f(u)\neq f(v)\}.
\]

Every edge is a certificate that the current quotient identifies two states that the verified target requires to differ.

No coordinate name occurs in this object.

## 3. Generic developmental constructor

The developmental meta-language is supplied one generic operation:

\[
\operatorname{Refine}(P,\Omega).
\]

In V3 this operation is deliberately finite and exhaustive. It enumerates **every partition refining `P0`** and returns the unique coarsest refinement that separates every edge of `Omega`.

Because each 4-element base block has Bell number

\[
B_4=15,
\]

there are exactly

\[
15^2=225
\]

candidate refinements of `P0`.

### Proposition 1 — unique coarsest obstruction repair

For every one of the 256 Boolean targets `f:W->2`, `Refine(P0, Omega_P0(f))` exists and is unique.

It is precisely the partition obtained by splitting each base block into the nonempty `f=0` and `f=1` fibers inside that block.

The executable result does **not** assume this description. It searches all 225 candidate partitions from the conflict relation alone, then checks uniqueness and formability.

## 4. Exact regime counts

A base block remains unsplit when `f` is constant on it: 2 possible labelings.

A base block splits into two target fibers when `f` is nonconstant on it: `2^4-2=14` possible labelings.

Hence the 256 targets divide by synthesized quotient size as

\[
\begin{array}{c|c}
|W/P_1| & \#f\\
\hline
2 & 2\cdot2=4\\
3 & 2(14\cdot2)=56\\
4 & 14\cdot14=196.
\end{array}
\]

There are 64 distinct synthesized partitions; each is induced by exactly 4 targets. The four targets differ only by independently complementing labels on the two original base blocks, which leaves the conflict relation unchanged.

## 5. Coordinate-free equivariance

The automorphism group of the base partition has

\[
2(4!)^2=1152
\]

elements: arbitrary permutations inside each four-state block, together with optional exchange of the two blocks.

For every target `f` and every such automorphism `g`, V3 checks

\[
\operatorname{Refine}(P_0,\Omega(g\cdot f))
=
g\cdot \operatorname{Refine}(P_0,\Omega(f)).
\]

That is

\[
256\times1152=294{,}912
\]

exact equivariance checks.

This matters because the developmental constructor has no privileged `x` or `y` coordinate vocabulary left. Its output depends only on the obstruction relation relative to the parent quotient.

## 6. Two-episode developmental effect

Let episode 1 synthesize

\[
P_1=\operatorname{Refine}(P_0,\Omega(f_1)).
\]

For every distinct ordered pair `(f1,f2)`, compare formability of `f2` in `P0` and `P1`.

A strict downstream growth pair satisfies

\[
f_2\notin 2^{W/P_0},
\qquad
f_2\in 2^{W/P_1}.
\]

All

\[
256\cdot255=65{,}280
\]

distinct ordered pairs are checked.

If `P1` has 3 quotient blocks, exactly

\[
2^3-4-1=3
\]

distinct non-base episode-2 targets are newly formable, giving

\[
56\cdot3=168.
\]

If `P1` has 4 quotient blocks, exactly

\[
2^4-4-1=11
\]

are newly formable, giving

\[
196\cdot11=2156.
\]

Therefore

\[
\boxed{168+2156=2324}
\]

strict downstream formability-growth pairs exist. The exhaustive execution independently obtains the same count.

For every such pair, reconstructing the parent regime `P0` and rerunning the same quotient-table constructor restores non-formability.

## 7. What V3 has fixed

V1 supplied a named `ExposeDependency` candidate and used hand-authored targets.

V2 exhausted all targets but still supplied a named coordinate schema

\[
\operatorname{Expose}(S),\quad S\subseteq\{x,y\}.
\]

V3 supplies no such coordinate vocabulary. The extension **instance** is a synthesized quotient partition selected from all 225 parent refinements using only verifier conflict edges.

So the remaining boundary has moved downward:

\[
\boxed{
\text{verified obstruction}
\longmapsto
\text{synthesized quotient extension}
}
\]

rather than

\[
\text{verified obstruction}
\longmapsto
\text{selection among named coordinate extensions}.
\]

## 8. What V3 does not establish

The generic operation `RefinePartition(parent, conflicts)` is still supplied by the developmental meta-language.

Therefore V3 does **not** establish:

- invention of partition refinement itself;
- invention of arbitrary new type formers;
- open-ended ontology invention;
- novelty of the underlying mathematics;
- a category-theoretically new object.

Mathematically this is standard finite quotient/partition refinement.

The experimental value is to isolate a lower impossibility boundary: the extension instance is no longer named in advance and is recovered equivariantly from obstruction structure.

## 9. Question for Daniel

Structured Continuation Calculus treats continuations relative to a fixed signature. Here a verifier obstruction induces a conservative quotient refinement

\[
P_0\rightsquigarrow P_1
\]

that strictly enlarges the extensional object language from

\[
2^{W/P_0}
\]

to

\[
2^{W/P_1}.
\]

The finite mathematics is ordinary partition refinement. The question is what structure is useful when such verified refinements themselves become composable developmental transitions between continuation regimes, especially when later constructor languages are indexed by the resulting quotient.
