# A finite typed witness of continuation-language growth

This note isolates one precise question:

> Can a verified episode change not merely which existing continuation is selected, but which object-level continuation terms are well-formed at all?

The construction is deliberately finite. It does **not** claim open-ended ontology invention. It isolates the distinction between state/search change inside a fixed constructor language and a checked extension of that language.

## 1. Old regime and exact formability boundary

Let

\[
X=\{0,1\},\qquad A=\{0,1,2\},\qquad \mathbf 2=\{0,1\}.
\]

The old object language \(M_0\) has one predicate sort

\[
U:=A\to\mathbf2
\]

with \(\bot,\top,[a=0]\) and Boolean operations \(\neg,\wedge,\vee\).

Observed on \(X\times A\), every old term is interpreted through

\[
\pi:X\times A\to A,\qquad \pi(x,a)=a.
\]

Hence every old denotation factors through \(\pi\).

### Lemma 1 — projection invariant

For every old term \(t\),

\[
\pi(x,a)=\pi(x',a')
\Longrightarrow
\llbracket t\rrbracket(x,a)=\llbracket t\rrbracket(x',a').
\]

Thus no \(M_0\)-term can distinguish states with equal \(a\) and different \(x\).

The executable finite closure has exactly four distinct \(U\)-semantics.

Crucially, \(M_0\) contains no sort

\[
D:=X\times A\to\mathbf2.
\]

Therefore

\[
\operatorname{Form}_D(M_0)=\varnothing.
\]

This is a syntactic/type-theoretic statement about the frozen object language, not a bounded-search observation.

## 2. Episode 1 — factorization obstruction

Freeze

\[
P_1(x,a):=[x=0]\vee[a=0].
\]

For example,

\[
P_1(0,1)=1,\qquad P_1(1,1)=0,
\]

although both points have projection \(a=1\). Therefore \(P_1\) does not factor through \(\pi\).

The program records all such conflicting pairs directly.

### Frozen developmental extension family

The developmental meta-language is **not unrestricted**. The experiment supplies a finite family consisting of:

1. every possible additional unary primitive \(q:A\to\mathbf2\); and
2. one dependency-exposing extension schema `ExposeDependency`.

There are exactly \(2^{|A|}=8\) unary truth tables. Every unary-only extension still factors through \(\pi\), so the complete unary-only subfamily is ruled out structurally and exhaustively.

This does **not** mean the obstruction uniquely derives `ExposeDependency` from first principles. `ExposeDependency` is a supplied candidate in the frozen developmental extension family.

The protocol admits that candidate only after the unary-only alternatives are ruled out and the candidate represents \(P_1\).

`ExposeDependency` adds the sort

\[
D:=X\times A\to\mathbf2,
\]

the primitive \([x=0]:D\), lifting

\[
\operatorname{lift}:U\to D,
\qquad
\operatorname{lift}(u)(x,a)=u(a),
\]

and Boolean operations on \(D\).

Write

\[
M_1=M_0+\operatorname{ExposeDependency}.
\]

Then \(P_1\) is representable, for example as

\[
[x=0]\vee\operatorname{lift}([a=0]).
\]

## 3. Conservativity — exact finite meaning

Here **conservative** has a deliberately narrow semantic meaning. We do not claim a general proof-theoretic conservativity theorem.

Let

\[
\operatorname{Sem}_U(M)
\]

denote the set of \(U\)-valued Boolean functions denoted by terms of regime \(M\) on the finite domain \(A\).

### Proposition 2 — old-fragment semantic conservativity

The extension adds no constructor returning sort \(U\), and the old constructors retain their denotations. Hence

\[
\operatorname{Sem}_U(M_0)=\operatorname{Sem}_U(M_1).
\]

The executable closure independently obtains four semantic classes on both sides and checks equality of the sets.

At the same time,

\[
\operatorname{Form}_D(M_0)=\varnothing,
\qquad
\operatorname{Form}_D(M_1)\neq\varnothing.
\]

Thus the old semantic fragment is preserved while the typed object language strictly grows.

## 4. Episode 2 — protected against online target leakage

The second target is represented by a fixed truth vector whose SHA-256 commitment is declared in the program before episode-1 extension selection. The function `select_episode1_extension()` does not reference the second target.

This establishes **online target blindness of the episode-1 selector**. It does not establish independent authorship: the experimenter designed the finite witness, the extension family, and the two episodes.

After episode 1, reveal

\[
P_2(x,a):=([x=0]\leftrightarrow[a=0]).
\]

with committed truth-vector hash

```text
71ca9703af0fda42b802aa93ef5ff20cc9d02353e1b2d514acae2ec02f2c7278
```

The same deterministic size-ordered second-generation synthesizer is used in every arm.

### Cold arm

Since sort \(D\) is absent,

\[
\boxed{P_2\notin\operatorname{Form}_D(M_0)}.
\]

No amount of search over well-formed \(M_0\)-terms changes this statement.

Moreover, granting any one of the eight possible unary primitives still cannot represent \(P_2\), because every unary-only expression remains invariant in \(x\).

### Developed arm

Under \(M_1\), the unchanged synthesizer finds the composed term

\[
O_2=
([x=0]\wedge\operatorname{lift}([a=0]))
\vee
\neg([x=0]\vee\operatorname{lift}([a=0])).
\]

It is extensionally equal to \(P_2\). It is not supplied as a primitive constructor.

The finite \(D\)-closure contains all 16 Boolean semantic classes over the effective atoms \([x=0]\) and \([a=0]\).

## 5. Strict typed regime-growth theorem

### Theorem 3

Within this frozen finite object-level calculus and supplied developmental extension family,

\[
P_2\notin\operatorname{Form}_D(M_0),
\qquad
P_2\in\operatorname{Form}_D(M_1).
\]

Furthermore:

1. removing `ExposeDependency` restores \(\operatorname{Form}_D=\varnothing\);
2. every unary-only sham extension preserves non-formability of \(P_2\);
3. \(\operatorname{Sem}_U(M_0)=\operatorname{Sem}_U(M_1)\);
4. the identical second-generation synthesizer returns no term cold and returns \(O_2\) warm.

Thus this witness is not explained as

\[
\text{same object grammar}+\text{better search state}.
\]

Inside the stated scientific boundary, the transition is

\[
\boxed{M_0\hookrightarrow M_1}
\]

with preservation of the old semantic fragment and strict enlargement of the typed space of formable continuation terms.

## 6. Exact claim boundary

### Established in this finite witness

- an explicit factorization obstruction in episode 1;
- structural and exhaustive rejection of the complete unary-only extension subfamily;
- admission of a supplied dependency-exposing extension schema;
- preservation of the old \(U\)-semantic fragment;
- strict addition of a previously absent result sort;
- online target blindness of episode-1 extension selection;
- a second composed term that is ill-typed/unformable before the extension and constructible afterward;
- ancestor ablation restoring non-formability;
- identical second-generation synthesis code in cold and developed arms.

### Not established

- that Python or Lean lacked the ability to encode either regime;
- host-language growth;
- autonomous invention of `ExposeDependency`;
- unrestricted invention of new type formers;
- unique derivability or minimality of `ExposeDependency` among every conceivable representation change;
- independent authorship of episode 2;
- general proof-theoretic conservativity;
- the broader natural-system Developmental Intelligence thesis.

The scientific boundary is the frozen **object-level constructor calculus available to the developmental controller**. The developmental meta-language remains richer and already contains `ExposeDependency` as an admissible extension schema.

The next stronger experiment should move this boundary downward: remove `ExposeDependency` as a named candidate and test whether an obstruction-defined structural requirement can cause synthesis of a dependency-sensitive extension class from a weaker generic meta-language.

## 7. Mathematical question

Structured Continuation Calculus studies lawful continuations relative to a fixed signature. This witness isolates a transition between two typed continuation regimes:

\[
M_0\hookrightarrow M_1.
\]

The question is not which categorical formalism sounds most sophisticated, but which one captures additional invariants and compositional laws of such checked regime extensions.

> What is the natural mathematical object for a verified transition between continuation regimes that preserves the old semantic fragment while changing which typed continuations can be formed afterward?

Possible answers might involve categories of theories/signatures, indexed or fibered categories, double categories, equipments, or something simpler. The witness deliberately does not choose among them in advance.
