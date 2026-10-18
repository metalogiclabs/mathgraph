# JPL PKC: refute-first verification of `@Checked.statement` (V3)

## Frozen source and claim

- Source: `nasa-jpl/PropertyKindCalculus@e0deb453e05ffa63297d9704ceb47d0855193824`, Lean `v4.34.0`, 17 October 2026 UTC.
- [DSL source](https://github.com/nasa-jpl/PropertyKindCalculus/blob/e0deb453e05ffa63297d9704ceb47d0855193824/sysml/PKC.sysml): `metadata def Checked` has both a `decl` and optional `statement`, and says citations identify the Lean type backing the annotated model element.
- [Neutral model source](https://github.com/nasa-jpl/PropertyKindCalculus/blob/e0deb453e05ffa63297d9704ceb47d0855193824/interchange/PropertyKindCalculus/Interchange/Model.lean): the `Checked.statement` field is described as the statement the author believes the declaration proves, "checked against the environment on import, never trusted".
- [Ingest source](https://github.com/nasa-jpl/PropertyKindCalculus/blob/e0deb453e05ffa63297d9704ceb47d0855193824/scripts/ingest-sysml.lean): ingestion calls `Harvest.unverifiedCitations` and refuses models containing an unverified citation.
- **Candidate failure:** `Harvest.unverifiedCitations` may validate whether `Checked.decl` denotes *some* theorem/proposition without checking whether the optionally declared `Checked.statement` matches that theorem. The source-code inspection identified this possibility, but no native outcome was opened before freezing the test.

## Exact experiments, controls, and verdicts

On the actual imported JPL `PropertyKindCalculus.Interchange` module construct three neutral `PkcModel` values:

1. **Positive:** `@Checked` cites the real `PropertyKindCalculus.Iso80000.Part3.Edge.width_length` proposition constructor with no statement. Citation should be accepted.
2. **Counterfactual:** cite that **same** proposition constructor but declare the optional statement `False`. `False` cannot be that constructor's actual type. If `unverifiedCitations` also accepts it, classify `CANDIDATE_UNCHECKED_STATEMENT_METADATA`.
3. **Control:** cite the same declaration with statement `True`, checking whether both incompatible strings receive identical treatment despite their different meaning.
4. **Negative gates:** a missing declaration, the non-proof `Nat.add`, and the axiom `propext` must be rejected. These ensure the importer is really enforcing *some* evidence policy.
5. **Emission:** check whether the generated Lean source carries the false statement only in a comment and still compiles. This demonstrates that a successful generated-module build does not establish the textual `statement` assertion.

Treat native build/environment failures as `UNKNOWN_APPARATUS`; do not infer a scientific defect. A native witness qualifies **a bounded metadata-claim semantic mismatch**, not Lean kernel unsoundness, a universal SysML failure, or a proof of what the original scientist intended. `statement` may be intended as non-normative metadata; if so the proper resolution is an explicit trust-boundary qualification rather than silently claiming statement checking.

## Independence and controls

This is a **source-aware first-execution falsifier**, not an untouched-future black-box prediction. The claim and adversarial cases are frozen before the first native Lean run. The comparator exercises the real JPL `Harvest.unverifiedCitations`, not a toy reimplementation, and archives the exact source, logs and generated file.

No JPL repository mutations, upstream PRs, private FGM source access, or external communication are authorized.
