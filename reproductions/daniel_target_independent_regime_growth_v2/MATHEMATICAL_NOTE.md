# Exhaustive finite regime selection by future formability

## 1. Fixed world and regimes

Let

\[
W=X\times Y\times A,
\qquad X=Y=A=\{0,1\}.
\]

The base observation map is

\[
\pi_\varnothing:W\to A,
\qquad \pi_\varnothing(x,y,a)=a.
\]

For each hidden-coordinate mask

\[
S\subseteq\{x,y\},
\]

let

\[
\pi_S:W\to \Big(\prod_{c\in S} c\Big)\times A
\]

be the projection exposing exactly the coordinates in \(S\) together with \(A\).

The developmental meta-language contains one generic schema

\[
\operatorname{Expose}(S),\qquad S\subseteq\{x,y\}.
\]

No particular target is built into this schema.

For a Boolean target

\[
f:W\to\mathbf2,
\]

define formability in regime \(S\) extensionally by

\[
f\in\operatorname{Form}(S)
\iff
\exists \widehat f\; f=\widehat f\circ\pi_S.
\]

Equivalently, \(f\) is constant on every fiber of \(\pi_S\).

## 2. Certified obstruction

If there exist \(p,q\in W\) such that

\[
\pi_S(p)=\pi_S(q)
\qquad\text{but}\qquad
f(p)\neq f(q),
\]

then \(f\notin\operatorname{Form}(S)\).

Such a pair is an exact finite obstruction certificate.

## 3. Essential-coordinate selector

A hidden coordinate \(c\in\{x,y\}\) is essential for \(f\) when there are two states differing only in \(c\) on which \(f\) has different values.

Write

\[
E(f)\subseteq\{x,y\}
\]

for the set of essential hidden coordinates.

### Proposition 1

For every Boolean target \(f:W\to\mathbf2\),

\[
f\in\operatorname{Form}(E(f)).
\]

Moreover, for every proper subset \(T\subsetneq E(f)\),

\[
f\notin\operatorname{Form}(T).
\]

Hence \(E(f)\) is the unique minimal coordinate-exposure mask for \(f\).

### Proof

If two states agree on \(A\) and every coordinate in \(E(f)\), then any remaining hidden coordinate is nonessential and may be flipped without changing \(f\). Therefore the states have equal target value, so \(f\) factors through \(\pi_{E(f)}\).

If an essential coordinate \(c\) is removed, its witnessing pair becomes merged by the smaller projection while retaining unequal target outputs, giving an obstruction certificate. \(\square\)

## 4. Complete finite classification

There are

\[
2^{|W|}=2^8=256
\]

Boolean targets.

The executable audit checks every one and obtains:

\[
\begin{array}{c|r}
E(f)&\#f\\\hline
\varnothing&4\\
\{x\}&12\\
\{y\}&12\\
\{x,y\}&228
\end{array}
\]

Thus different targets induce different minimal regime extensions under one fixed symmetric schema.

This removes the hand-picked-target issue of the earlier constructed witness.

## 5. Two-episode developmental relation

For two distinct targets \(f,g\), let episode 1 install

\[
S_1=E(f).
\]

Call the ordered pair \((f,g)\) a **strict downstream formability-growth pair** when

\[
g\notin\operatorname{Form}(\varnothing)
\]

but

\[
g\in\operatorname{Form}(S_1).
\]

Ancestor ablation returns from \(S_1\) to \(\varnothing\), so the first condition immediately restores non-formability.

The experiment checks all

\[
256\cdot255=65{,}280
\]

distinct ordered pairs.

### Theorem 2 — exhaustive pair result

Exactly

\[
57{,}492
\]

ordered pairs exhibit strict downstream formability growth.

They decompose by episode-1 extension as

\[
132\text{ through }\{x\},
\qquad
132\text{ through }\{y\},
\qquad
57{,}228\text{ through }\{x,y\}.
\]

The executable checker evaluates every pair rather than selecting favorable transfer cases.

## 6. Sham family

Every predicate

\[
q:A\to\mathbf2
\]

is already a function only of the base coordinate \(A\). There are exactly four such truth tables.

Adding any number of these predicates leaves the fibers of \(\pi_\varnothing\) unchanged with respect to hidden-coordinate separation. Therefore no A-only sham can make an \(x\)- or \(y\)-dependent target formable.

The executable audit checks all four predicates directly.

## 7. What is mathematically established

The finite result establishes exactly:

1. obstruction by fiber conflict;
2. a target-independent map
   \[
   f\mapsto E(f)
   \]
   to the unique minimal coordinate-exposure extension;
3. complete discrimination among BASE, \(x\), \(y\), and \(x,y\) regimes across all 256 targets;
4. strict downstream object-language formability growth across all 65,280 distinct ordered episode pairs;
5. ancestor-ablation restoration of non-formability;
6. failure of the complete A-only sham family.

## 8. What is not established

The generic schema

\[
\operatorname{Expose}(S)
\]

is supplied by the developmental meta-language. It is not invented by the experiment.

The mathematics above is a finite instance of standard dependency/factorization/partition-refinement structure. We do not claim Proposition 1 or Theorem 2's underlying structural idea as new mathematics.

The significance for the broader programme is narrower: the prior same-author/hand-picked-target confound is removed, so the experiment now cleanly separates two questions:

\[
\text{Which supplied regime extension is required?}
\]

from the stronger open question

\[
\text{Can the extension schema itself be synthesized from weaker generic means?}
\]

That second question remains the actual representation-invention frontier.
