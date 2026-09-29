# Crystal Automatic Lean Bridge Discovery V1

Status: bounded candidate pipeline; promotion requires the workflow qualification gate.

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
