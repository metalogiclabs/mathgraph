# Aerospace correspondence case study

**Preserving meaning across aerospace software boundaries**  
Heath Sanchez, Metalogic Labs · 22 November 2026 · Technical working draft

[Read the case study](case-study.md).

This package makes a specific aerospace assurance question reproducible: does
the meaning needed by the downstream engineering conclusion survive the
representation boundary?

It combines an accepted Nyx trajectory-frame correction with a fresh native
FRET/C2PO/R2U2 interpretation experiment. A short L4YAML interface example
supplies supporting evidence. These are separate case studies, not an
implemented integration between Nyx and R2U2.

## Main result

The authentic FRET export `BOOST -> F[0,7] COAST` accepts a COAST observation
at the same sample as BOOST. A constructed `[1,7]` comparison requires a
later observation. An additional control establishes that `[1,7]` still
allows phase overlap: both formulas accept COAST at samples 0 and 1 when
BOOST occurs at 0.

The experiment distinguishes **bounded response timing** from **mutual
exclusion**. It does not select the operational requirement for a mission
owner or identify an upstream FRET/R2U2 defect.

## Reproduce

For the native monitor case, use Python 3.12+, Node.js 24+, npm, Git, GCC,
Make, and public access to GitHub/npm:

```sh
python3 rocket/reproduce.py --work-dir /tmp/mathgraph-aerospace-replay
```

Choose a new or empty work directory. Expected observations are:

- 11 existing contract controls pass.
- 64/64 native verdict values agree with a separately implemented oracle.
- A clean rebuild and separate assessor replay those same 64 values.
- Five actual generated-artifact mutations are refused.
- A separate 16-value control demonstrates that a later response does not
  enforce non-overlap.

Read [the detailed monitor boundary](rocket/README.md) and inspect the
[compact result manifest](rocket/results.json). The logical sample indices
have not been bound to an operational sampling period.

For the Nyx pinned-source and historical-receipt recheck:

```sh
python3 nyx/verify_evidence.py
```

Expected result: `PASS_SOURCE_AND_RECORDED_CI_RECHECK`, with native Nyx
execution explicitly `NOT_RUN` in this preparation session. This check
verifies nine original source/license blobs, exact repair correspondence,
historical test results and the executed/accepted source-tree identity.
Read [the Nyx evidence boundary](nyx/evidence.md).

The repository workflow `Aerospace correspondence replay` executes the
native monitor reproduction and Nyx receipt check and retains complete
generated replay outputs as an Actions artifact. [Hosted run #44990487041](https://github.com/metalogiclabs/mathgraph/actions/runs/44990487041)
succeeded at publication commit `42d429409a0ca63ad01d5dcf993f4efc2ae6cd09`.
The run records the native replay and the source/receipt recheck with their
distinct verification boundaries.

## Evidence interpretation

| Case | Evidence class | Boundary |
| --- | --- | --- |
| Nyx frames | Accepted historical defect/repair; freshly rechecked source and receipts | Native Nyx was not rebuilt here; associated historical CI had a Lints failure |
| Runtime response | Fresh original-toolchain finite experiment | Constructed alternative, unresolved operational intent; no superiority claim |
| L4YAML NUL | Accepted historical interface repair | Supporting public case; no fresh Lean/FFI replay here |

This sole-author working draft uses public sources and supplied reproduction
materials. A joint publication or operational adoption remains a separate
future outcome.

## Files and source notices

- `case-study.md`: complete working paper.
- `rocket/`: native reproduction wrapper, original pinned method, locked
  parser dependencies and small evidence manifests.
- `nyx/`: original source excerpts/files, source notices, historical log
  excerpts and the source/receipt verifier.

Nyx source retains its upstream AGPL-3.0-or-later notices and full license.
FRET and R2U2 are downloaded from their original repositories at replay time.
Existing source notices are preserved; no replacement blanket license is
asserted for the combined third-party material.
