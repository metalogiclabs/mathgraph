# L4YAML observation ceiling — source-bound MathGraph Check case

**Outcome:** reusable *bounded* case adapter and neutral Check preview. This is
not a deployed check, a fresh Lean replay, or the complete Group 7.7 capstone.

## Exact consequential distinction

Frozen production source: `metalogiclabs/L4YAML@64795a8db28ccfdae85082c93b6453001ae9d3e4`.
Actual public observation: `TokenParser.parseYaml input = .ok ...`.
Necessary normative requirement: `NoRawSOH input` (raw U+0001 is forbidden).

| Input | Public parser success | NoRawSOH |
|---|---|---|
| `#a` | true | true |
| `#` followed by raw U+0001 | true | false |

Both inputs produce the same *success-bit* observation, yet the protected
requirement differs. Therefore there is no function of **only the parser
success bit** that decides `NoRawSOH` on a domain containing both inputs. A
single qualified pair refutes that implication universally for the frozen
observation, while a finite collision-free set could never prove global
sufficiency. This is not an argument that source inspection cannot find the
defect: source inspection supplies a **stronger observation**.

The separate Lean theorem `MathGraph.WholeSource.CapstoneCommentBoundary.
no_normative_iff_on_frozen_runtime` refutes *any* all-input equivalence between
the frozen parser's acceptance and a proposed language satisfying the necessary
raw-character exclusion. Fixing only a downstream proof or definition cannot
make the unchanged parser conform. Changing the parser and requalifying it is
necessary to close the intended normative iff.

## Evidence authority and scope

- Original Lean proof commit:
  [b882e5b2](https://github.com/metalogiclabs/L4YAML/commit/b882e5b298b30b094f4154da7108a45e196cfcd3).
- Native qualification:
  [run 42420433923](https://github.com/metalogiclabs/L4YAML/actions/runs/42420433923),
  job `128547467405`, `directive-proofs=success`, artifact `13593491176`,
  SHA-256 `f60e48bc7a9df0e618c9ce6398644a9bbc5da4d4022010528f662f0566a536f3`.
  These metadata and the head SHA were checked against GitHub on 8 Nov 2026.
  Later on 8 Nov the actual ZIP bytes were downloaded from GitHub; their
  SHA-256 matched the published artifact digest. The byte-corroboration gate
  checked the historical source head, Lean build identity, theorem type,
  qualified axiom list, source witness and expected-failure control. It
  returned `CORROBORATED` with `proof_replay=NOT_PERFORMED`. This can be
  reproduced using `node corroborate-artifact.mjs path/to/artifact.zip` after
  downloading the named Actions artifact; neither that CLI nor a CI badge
  constitutes a fresh independent kernel replay.
  The job included source-identity guards, fixed controls, exact Lean proof
  qualification and the permitted-axiom gate. The full production job was
  **skipped**. Artifact metadata are not a replacement for opening each proof
  log or rerunning Lean in this current workspace.
- Independently enumerated direct inputs are in `case.mjs`. The pure
  `auditL4CommentObservation` adapter requires an **out-of-band trusted host**
  to admit all of: exact table SHA-256, frozen source SHA, original Lean proof
  receipt identity, and the qualified artifact digest. The table and its
  computed hash cannot admit themselves. Missing or changed authority yields
  `UNKNOWN`.
- The preview reuses the existing MathGraph Check advisory Check Run builder.
  It is neutral and emits **no GitHub write**. No native App webhook/deployment
  has been installed for this case.

## Status ledger

| Claim | State | Reason |
|---|---|---|
| Frozen parser permits raw SOH; no normative iff on this production SHA | **WARRANTED** | Pinned native Lean proof and controls |
| Downstream parser-success bit decides NoRawSOH | **REJECTED** | Two admissible source inputs collide on observation, differ on target |
| Typed finite quotient consumer and neutral Check preview | **REUSABLE in bounded adapter** | RED→GREEN tests, no authority escalation |
| Complete independent YAML 1.2.2 grammar `L` and both acceptance directions | **UNKNOWN** | `L4-EXACT-GRAMMAR`, producer and strictness still open |
| New normative parser implementation, full regression and source-qualified iff | **UNKNOWN** | Requires changed production source and proof |

## Verification commands

```bash
node --test integrations/mathgraph-check-github/finite-warrant-quotient-v1.test.mjs \
  experiments/check-l4-observation-ceiling-v1/case.test.mjs \
  integrations/mathgraph-check-github/advisory-publisher-v1.test.mjs
```

The intentional regression checks were first run RED for the missing
decision-ceiling fields, then for the masked claim-verdict collision, and for
the absence of the exact L4 adapter and trusted artifact pin. They were then
made GREEN. This case is a consumer of an existing qualified L4YAML proof, not
an independent discovery of the old comment policy.

## Smallest next experiment

Complete the independent source-only exact comment/quoted-character relations
on the L4YAML research branch, consuming the already qualified
`ExactCharacters` layer. Retain raw-control exclusion and escaped-control
admission as separate controls. Do **not** promote the full language claim
until the recursive grammar and requirement map are complete; then repair the
actual runtime and rerun both theorem directions at the changed source.
