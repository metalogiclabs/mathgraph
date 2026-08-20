# A finite typed witness of continuation-language growth

This note isolates one question from the larger MathGraph / Structured Continuation Calculus programme:

> Can a verified episode change not merely which existing continuation is selected, but which continuation terms are well-formed at all?

The construction below is deliberately finite and elementary. Its purpose is not to claim open-ended invention. Its purpose is to make the distinction mathematically exact.

## 1. The old constructor regime

Let

\[
X=\{0,1\},\qquad A=\{0,1,2\},\qquad \mathbf 2=\{0,1\}.
\]

The old language \(M_0\) has one predicate sort

\[
U := A\to\mathbf 2
\]

with constants \(\bot,\top\), the atom \([a=0]\), and Boolean operations \(\neg,\wedge,\vee\).

When an old term is observed on \(X\times A\), it is interpreted through the projection

\[
\pi:X\times A\to A,\qquad \pi(x,a)=a.
\]

Thus every old denotation factors through \(\pi\):

\[
\llbracket t\rrbracket(x,a)=\widehat t(a).
\]

### Lemma 1 — projection invariant

For every \(t\in\operatorname{Form}(M_0)\),

\[
\pi(x,a)=\pi(x',a')
\Longrightarrow
\llbracket t\rrbracket(x,a)=\llbracket t\rrbracket(x',a').
\]

In particular, no old term can distinguish two states with the same \(a\)-coordinate and different \(x\)-coordinates.

The executable enumerator independently confirms that the old Boolean closure has exactly four unary semantic classes.

## 2. Episode 1: a certified factorization obstruction

Freeze the first target

\[
P_1(x,a) := [x=0]\vee[a=0].
\]

For example,

\[
P_1(0,1)=1,\qquad P_1(1,1)=0,
\]

although

\[
\pi(0,1)=\pi(1,1)=1.
\]

Likewise \((0,2)\) and \((1,2)\) are merged by \(\pi\) but require different outputs.

Therefore \(P_1\) does not factor through the old representation.

The experiment does not infer this from failed search. It records the conflicting pairs explicitly.

### Frozen alternative-extension family

Before admitting a dependency-sensitive representation, the experiment exhausts every possible new unary primitive

\[
q:A\to\mathbf 2.
\]

There are exactly

\[
2^{|A|}=8
\]

such truth tables.

Adding any of them may enrich the unary language, but every resulting term still factors through \(\pi\). Therefore none can represent \(P_1\).

The surviving extension is

\[
O_1:=\operatorname{ExposeDependency}.
\]

It introduces a new sort

\[
D := X\times A\to\mathbf 2,
\]

a primitive \([x=0]:D\), and a lifting operation

\[
\operatorname{lift}:U\to D,
\qquad
\operatorname{lift}(u)(x,a)=u(a),
\]

with the same Boolean connectives on \(D\).

Write

\[
M_1=M_0+O_1.
\]

The first target is now representable, for example by

\[
[x=0]\vee\operatorname{lift}([a=0]).
\]

## 3. Conservativity

The extension does not alter the old unary fragment.

### Proposition 2 — conservative old fragment

For every old \(U\)-term \(t\), its syntax and denotation are unchanged in \(M_1\). Conversely the extension adds no new constructor of sort \(U\).

Hence

\[
\operatorname{Form}_U(M_0)=\operatorname{Form}_U(M_1)
\]

extensionally in this finite model.

The executable check obtains four unary semantic classes on each side and verifies equality of the two sets.

The strict growth occurs in a new sort:

\[
\operatorname{Form}_D(M_0)=\varnothing,
\qquad
\operatorname{Form}_D(M_1)\neq\varnothing.
\]

This is the key distinction from the earlier token-rewrite toy.

## 4. Episode 2: a term that was not well-formed before development

The protected second target is fixed by SHA-256 commitment before episode-1 extension selection. The episode-1 selector never reads it.

After \(O_1\) has been selected, reveal

\[
P_2(x,a):=([x=0]\leftrightarrow[a=0]).
\]

Its committed truth-vector hash is

```text
71ca9703af0fda42b802aa93ef5ff20cc9d02353e1b2d514acae2ec02f2c7278
```

Let the second-generation synthesis operator be the same deterministic size-ordered enumerator in every arm.

### Cold arm

Under \(M_0\), the result sort \(D\) is absent. Therefore

\[
\boxed{P_2\notin\operatorname{Form}_D(M_0)}
\]

for a syntactic reason: there are no \(D\)-typed terms.

There is also a semantic obstruction. Even if one grants **any** additional unary primitive \(q:A\to\mathbf2\), every such expression remains invariant in \(x\), whereas \(P_2\) is not.

Thus every one of the eight possible unary-only sham extensions fails as well.

### Developed arm

Under \(M_1\), the same synthesizer enumerates \(D\)-terms and finds

\[
O_2=
([x=0]\wedge\operatorname{lift}([a=0]))
\vee
\neg([x=0]\vee\operatorname{lift}([a=0])).
\]

This is extensionally \(P_2\).

It is not a primitive constructor supplied by the experiment; it is a composed term discovered by the unchanged enumerator after the new sort and lifting structure exist.

The finite closure contains all 16 Boolean semantic classes over the two effective atoms \([x=0]\) and \([a=0]\).

## 5. Strict developmental formability theorem

Within this frozen constructor calculus:

### Theorem 3

\[
P_2\notin\operatorname{Form}_D(M_0),
\]

but

\[
P_2\in\operatorname{Form}_D(M_1).
\]

Moreover:

1. removing \(O_1\) restores \(\operatorname{Form}_D=\varnothing\);
2. every unary-only sham extension preserves non-formability of \(P_2\);
3. the old \(U\)-fragment is conservative;
4. the identical synthesis procedure returns no term cold and returns \(O_2\) warm.

So the causal change is not merely

\[
\text{same grammar}+\text{better search state}.
\]

It is, inside this finite object language,

\[
\boxed{M_0\hookrightarrow M_1}
\]

with a strictly larger typed space of possible continuation terms.

## 6. What is and is not established

Established exactly in this witness:

- a verifier-visible factorization obstruction in episode 1;
- exhaustion of all unary-only sham extensions;
- acquisition of a dependency-exposing language extension;
- conservativity on the old fragment;
- strict growth of the typed constructor language;
- a protected second-generation term that is unformable before the extension and constructible afterward;
- ancestor ablation restoring non-formability;
- the same second-generation synthesis algorithm in cold and developed arms.

Not established:

- that Python or Lean could not encode \(O_2\) before the experiment;
- that the host programming language grew;
- that an unrestricted agent can invent arbitrary new type formers;
- that \(\operatorname{ExposeDependency}\) is a universally derivable response to arbitrary obstruction;
- that this finite witness by itself establishes the broader natural-system Developmental Intelligence thesis.

The scientific boundary is the frozen **object-level constructor calculus available to the developmental controller**, not the expressive power of the implementation language.

## 7. The mathematical question for regime change

Structured Continuation Calculus already describes lawful continuations relative to a fixed signature. This example asks what structure should model a conservative change of signature itself.

Internally one has ordinary continuations in a regime,

\[
x\longrightarrow y.
\]

Development here changes the language in which such continuations can be formed:

\[
M_0\hookrightarrow M_1.
\]

The natural question is therefore:

> What mathematical structure should represent verified conservative transitions between continuation regimes when the transition changes which typed morphisms/continuations can exist afterward?

The example intentionally does not choose the answer in advance. A category of theories, indexed/fibered structure, double category, equipment, or something simpler should be judged by what additional invariants and compositional laws it explains beyond this finite witness.
