# PKC V7 — physical type mutation, selective withdrawal and native restoration

**FROZEN BEFORE execution. CANDIDATE.** No mutation of any NASA/JPL repository on GitHub.

## Authority and immutable method

- Original PKC source: `nasa-jpl/PropertyKindCalculus@e0deb453e05ffa63297d9704ceb47d0855193824`, `leanprover/lean4:v4.34.0`. Exact source file `iso80000/PropertyKindCalculus/Iso80000/Part3.lean`, Git blob SHA `9d3359e126fd76298c99e8f9ff5bd3658ebcf5d4`.
- Prior source-native positive run [V6 #39192976898](https://github.com/metalogiclabs/mathgraph/actions/runs/39192976898), at MathGraph commit `784b9b59bc3b036e0e9f7a6e97d506979a0da174`; original [artifact #12160348478](https://github.com/metalogiclabs/mathgraph/actions/runs/39192976898/artifacts/12160348478) ZIP digest `sha256:83e601483fe442a68ec139fb569295dba6256065638049159e724039f4d07740`.
- The interpretation and native declaration-type comparison MUST be copied **byte-for-byte** from the `private def tokenExpr` ... `private def expected` boundary of V6 `Check.lean`, without modifications. Only the unconditional V6 *test-specific* `example` and expected-result assertions are replaced with lane-recording and an independently frozen, outside-the-interpreter oracle. No general autoformalization.
- Warrant evaluator MUST use unchanged `research/cross_domain_correspondence_v1/protocol.py` from V6's original branch. Archive and assert Git blob SHAs of both.

## Exact mutation in an isolated working copy (not upstream)

Original source declares `Edge.width_length : Edge width.kind length.kind`. In its own local file only, change its codomain to `Edge width.kind height.kind`. To retain the three independently established downstream facts, add `Edge.width_length_original : Edge width.kind length.kind`, and substitute this constructor **only** in the three local proof uses `Specializes.of_edge Edge.width_length`. This is a deliberately synthetic, destructive declaration-type intervention, *not* a candidate PKC repair or a meaningful new ISO 80000 definition. No changes to any other checked-out source file. Source must be recognized as a modified original checkout with `git diff` and exact blob hashes.

## Frozen lane sequence

1. **BASE:** unchanged JPL source. Independently compile the original `Part3`/interchange code and evaluate all seven source-native V6 API JSON inputs (authenticated from artifact #12160348478). Check `MATCH, MISMATCH, MISMATCH, MISMATCH, UNKNOWN_UNSUPPORTED, UNKNOWN_UNSUPPORTED, NO_ASSERTION` in V6 order.
2. **MUTANT:** apply exactly the declared file mutation; fail closed if the source blob, edit count, or changed paths differ. Rebuild the modified **real Lean module**, re-execute the identical frozen seven inputs through the identical copied interpretation+Lean Meta declaration-type comparator. Expected changed verdicts: `typed_match` MATCH→MISMATCH and `typed_mismatch` MISMATCH→MATCH. All other five expected unchanged. Require declaration `width_length` to stay present and proof-bearing. No test adaptation after outcome.
3. **RESTORED:** physically `git checkout --` the single modified source file, confirm identical original file SHA and clean Git tree, rebuild original Lean artifacts and re-run exact seven inputs. Require byte-for-byte baseline decision vector.
4. **Independent provenance:** outside the Lean script, re-check immutable V6 raw input hashes, source blobs, actual native compiler log success and declaration-type change. Check that no leaked stale old .olean or cached type can account for observed reversal. Verify a separate same-original-type successor witness `width_length_original` exists in MUTANT and the unaffected `height_length` type remains its original one.
5. **Selective lineage:** old source-wide evidence becomes UNKNOWN on revision change until independent replay; after replay only the two type-sensitive verdicts switch. Unchanged five decisions may be **requalified**, not assumed to be valid on the changed revision by fiat. Withdrawal without a matching pinned type evidence yields `UNKNOWN_WITHDRAWN_OR_CHANGED` via the unchanged V1 evaluator; after true restoration it requalifies by actual compiler replay. The independent `height_length` citation remains type-stable, but the full source pin changes.

## Risk boundary

A failed mutant build is UNKNOWN_APPARATUS/DEPENDENCY (not proof of semantic change). If the modified type is inaccessible to `Meta.getConstInfo`, do not classify. Stop rather than adjust mutation based on outcome. If the source-native matrix differs, record scientific RED and do not retune. The original JPL importer accepts citations as names, not necessarily their free-text meaning.

A qualifying GREEN supports **WARRANTED_BOUNDED_PHYSICAL_DECLARATION_TYPE_REVERSAL_AND_REQUALIFICATION**, with explicit source-local controlled mutation and frozen human-authored interpretation. It does **not** prove universal statement fidelity, source-neutral discovery, autonomous learning, semantic equivalence for arbitrary Lean expressions, or Nicolas's intended `@Checked.statement` contract. No upstream contact, JPL modification, endorsement, or paper submission.
