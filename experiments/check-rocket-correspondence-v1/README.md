# Rocket correspondence profile v1 — source-only, no operational authorization

**Research candidate, isolated from production MathGraph Check.** This profile is deliberately small: one public paper-inspired sounding-rocket requirement, two finite interpretations, four eight-tick scenarios, one source-only bundle and no automatic repair.

## Upstream and exact evidence scope

- Original NASA FRET source: [NASA-SW-VnV/fret@cf0f913](https://github.com/NASA-SW-VnV/fret/commit/cf0f913cc15c41705e803593297e89cd6056b839).
- Native C2PO/R2U2 source: [R2U2/r2u2@2875a1d](https://github.com/R2U2/r2u2/commit/2875a1dfc0b8cb27c4c4f14bece6b95c3afff91a).
- Original requirement: "whenever BOOST, the sounding_rocket shall within 7 seconds satisfy COAST".
- Actual FRETish-exported stream formula **in the source packet**: BOOST -> F[0,7] COAST.
- Constructed comparison, NOT a second FRET output or owner-approved repair: BOOST -> F[1,7] COAST.
- Evidence source: owner-provided private source-only archive mathgraph_fretish_rocket_r2u2_source_receipt_pilot_v4_20261118.zip, SHA-256 fc055bc03c34fd8b7ca90242b71a400d30e4376e4c2e262d744a7aaa8d5b9d1f. **The ZIP and the private PDF are not committed to this public repo.**
- Previously reported native replay: 64 decoded verdicts from four complete eight-tick scenarios and two candidate formulas matched a separate oracle. This profile does NOT rerun FRET, C2PO or native R2U2 and does not requalify that historical claim. Compiled native binaries are absent from the supplied archive.
- The [ISoLA 2026 paper](https://link.springer.com/chapter/10.1007/978-3-032-40124-3_8) discusses simultaneous BOOST/COAST as unintended within its illustrative FPROGG example. This is NOT authenticated operational mission approval.

## Output contract

rocket_profile.py checks exact ZIP digest, whitelisted C2PO source/map, frozen signal order, four synchronized CSV/JSON traces, the FRETish-export declaration and unsigned source/map receipt bindings. It computes 64 **expected** finite Boolean verdicts and exhaustively checks the unique minimal two-true-event separator in 65,536 eight-tick traces.

| Layer | Scoped result |
| --- | --- |
| Byte identity of the source-only ZIP | EXACT_ARCHIVE_AND_MEMBER_BYTES_MATCH |
| Finite source [0,7] versus comparison [1,7] | WARRANTED_BOUNDED_FINITE_ORACLE |
| Actual FRET parser/export rerun | UNKNOWN_NOT_REPLAYED_BY_THIS_PROFILE |
| Compiled monitor/native comparison | UNKNOWN_BINARIES_NOT_IN_BUNDLE |
| Operational owner interpretation and permission to repair | UNKNOWN / DENIED |
| Overall purpose-to-deployment correctness | **UNKNOWN** |

This module never executes code extracted from the ZIP, never treats unsigned hashes or an in-band owner_approved flag as authority, never publishes a GitHub Check, and never authorizes a repair. This source-only report is a candidate for MathGraph's existing BoundaryWarrant carrier (Subject, Obligation, Relation, Verification, Conclusion, Dependencies), NOT an authenticated native Receipt.

### Reproduce locally

Keep the original ZIP out of Git. From the repo root, run the profile with the path to the supplied ZIP, adding --out for a JSON report, then run Python unittest discovery on the directory.

- python3 experiments/check-rocket-correspondence-v1/rocket_profile.py /path/to/original-v4.zip --out rocket-source-assessment.json
- python3 -m unittest discover -s experiments/check-rocket-correspondence-v1 -p test_rocket_profile.py -v

CLI exit 0 means the bounded source-only check completed; it **does not mean operational intent or monitor correctness was established**. Unit tests generate only the small public example inputs in memory; no private source bundle is uploaded to GitHub. The original archive's EVIDENCE.md documents full separate native replay requiring pinned external checkout sources and dependencies.

## Missing authority, explicit next experiment

**Does COAST at the same instant as BOOST satisfy the actual operational requirement?**

If immediate COAST is permitted, the [0,7] interpretation accepts it; [1,7] rejects potentially permitted behavior. If immediate COAST is prohibited, [1,7] is at most a candidate, requiring protected examples, an actual owner decision and new source/map/binary receipts. Without authoritative interpretation, the answer is UNKNOWN and no repair is permitted.

Lineage: [MathGraph Check aerospace RC1 #279](https://github.com/metalogiclabs/mathgraph/pull/279), an independently qualified six-job source-frozen pilot. This feature remains a separate stacked research draft. It does not touch the live Worker, app privileges, scheduler, upstream software or RC1.

Next gate: authenticate one genuine aerospace owner decision, requalify native FRET/C2PO/R2U2 replay with an independently admitted source-map-binary receipt, prove selective withdrawal on source or approval change, and benchmark against an equally informed expert on a fresh claim. The older FRET/R2U2 paired-authority study tied a strong baseline; we do NOT claim discovery superiority.
