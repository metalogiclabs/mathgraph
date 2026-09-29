# Crystal Automatic Lean Bridge Discovery V1

Status: WARRANTED / REUSABLE on the declared three-corpus boundary.

## Objective

Turn the manual cross-corpus reuse demonstration into an executable loop:

```text
exact source pins
→ conservative declaration digest
→ alias normalization
→ cross-corpus semantic-head overlap
→ verified-library implication edges
→ candidate selection
→ Lean qualification
→ bounded reusable capability
```

Discovery is not authority. It may propose false positives. The only promoted
route is one that survives an independent Lean build/direct check.

## Current three-corpus boundary

The experiment reads exact immutable files from:

- Anthropic's Fermat's Last Theorem corpus;
- Isomorphic AI's Fermat corpus;
- Imperial College London's FLT project;
- one pinned Mathlib file used as the bridge library.

The source manifest records repository, commit, path and Git blob SHA. Any pin
change revokes the current discovery evidence.

## Discovery rules

V1 intentionally uses a tiny transparent rule set.

1. Parse theorem/lemma/def/abbrev/structure surfaces.
2. Learn transparent aliases from source, e.g. `Fermat.HoldsAt` to
   `FermatLastTheoremFor`.
3. Find semantic heads shared across independent corpora.
4. Learn one-way consequence edges from verified-library structure extension,
   e.g. `IsRegular extends IsWeaklyRegular`.
5. Propose producer-to-consumer routes only. Do not promote them.

This is not claimed to be a complete Lean elaborator or universal semantic
canonicalizer.

## Qualification

The first selected nontrivial route is:

```text
Anthropic:
  IsLocalRing.isRegular_of_systemOfParameters
        ↓
Mathlib:
  IsRegular extends IsWeaklyRegular
        ↓
Imperial consumer surface:
  Sequence.IsWeaklyRegular
```

Qualification replays the already source-pinned Anthropic theorem slice and
checks the consequence transport in Lean. The source proof is imported, not
reformalized.

## Epistemic disposition

A green workflow warrants only:

- the exact source pins were retrieved;
- the deterministic discovery code found the declared candidates;
- the chosen bridge was independently checked by Lean;
- the qualified consequence can be reused without copying the source proof.

Still UNKNOWN:

- completeness of discovery;
- universal theorem equivalence;
- arbitrary bridge synthesis;
- transport across incompatible Lean/Mathlib versions without a common
  qualifying environment;
- global minimality of the chosen semantic interface.

The next scaling experiment is corpus-wide declaration export plus top-k
candidate qualification, while preserving typed UNKNOWN for every unqualified
route.


## Qualified authority

The end-to-end automatic discovery and Lean qualification gate is GitHub Actions
run `36513233235` at head
`8c9af10d40f6f17e9fa2344fb4822690556cec98`.

It scanned 88 pinned declarations, learned one transparent alias, found one
three-corpus semantic-head convergence and four implication candidates, then
selected and qualified the Anthropic `IsRegular` to Imperial
`IsWeaklyRegular` route. Lean completed 8,713 build jobs successfully.
The promoted discovery artifact is `11009257816`, digest
`sha256:2fd4eac43876f48356f25c728839086ba5f24435b80b2c10658149392ec53aba`.

The warranted route was then compiled into Crystal semantic memory by run
`36513582132`, producing:

- semantic object: `semantic:8e5851f2733eab2459f9eb5c82abb468424a6186d5143404e88e24ef42db0748`
- adapter contract: `adapter:2e21c11aec8188e93056a1e96cb116fd00da7de0cc5fbb339aa91c6ada2781d4`
- interface: `lean.consequence.is-weakly-regular@1`
- capability artifact: `11009302901`
- artifact digest: `sha256:60d8034aecedb3e17edd34e2f8d5534018bfb77be0505201867ef3bc5b2b95e2`

The compiler rejects unwarranted candidates and the resulting adapter returns
typed UNKNOWN outside its qualified consequence boundary.
