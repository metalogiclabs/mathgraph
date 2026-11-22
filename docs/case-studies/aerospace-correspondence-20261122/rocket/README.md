# Aerospace requirement-to-monitor replay

This runnable case follows one illustrative requirement through the authentic
FRET parser/exporter, C2PO compiler and native R2U2 C monitor. It shows a
reproducible semantic distinction and a second control that prevents an
overstated repair claim.

The source requirement is:

> whenever BOOST, the sounding_rocket shall within 7 seconds satisfy COAST

The pinned FRET parser exports `BOOST -> F[0,7] COAST`. A deliberately
constructed comparison uses `BOOST -> F[1,7] COAST`. The comparison is not a
second FRET translation or an approved repair.

## Run

Prerequisites: Python 3.12 or newer, Node.js 24 or newer, npm, Git, GCC, Make,
and network access to public GitHub and npm.

```sh
python3 reproduce.py --work-dir reproduction
```

Use a new or empty work directory. The command fetches exact upstream Git
revisions, installs the locked parser dependencies, verifies the retained
MathGraph method files, builds the actual monitor, and runs the tests. It
then cleans and rebuilds the monitor and invokes the artifact assessor in a
separate process. It does not contact project maintainers or publish anything.

Expected result:

- 11 existing artifact/interpretation contract controls pass.
- All 64 decoded verdicts agree with the finite reference on the original
  four scenarios: 4 traces × 2 formulas × 8 indices.
- The separate assessor replays those same 64 values after a fresh native
  rebuild. This is additional qualification, not 64 additional cases.
- Five mutations of actual produced artifacts are refused.
- A separate, additional 16-value control shows that both formulas accept
  COAST at the trigger tick when COAST is also present at the next tick.

`results.json` is the compact result manifest: it records the execution
environment, four original scenarios, raw compressed verdict text, assessor
result, mutation refusals and the additional overlap control. A fresh run writes
its complete outputs under the chosen work directory; the accompanying hosted
workflow preserves those generated outputs as an artifact. The software records the stronger
operational-intent claim as `UNKNOWN` throughout.

## Result at the trigger index

| Trace | FRET source `[0,7]` | Constructed `[1,7]` | What it distinguishes |
|---|---|---|---|
| BOOST and COAST only at index 0 | True | False | Same-index response counts for the source formula |
| BOOST at 0, COAST only at 1 | True | True | Ordinary later-response control |
| BOOST at 0, no COAST | False | False | Missing-response control |
| No BOOST, no COAST | True | True | No-trigger/vacuity control |
| BOOST at 0, COAST at both 0 and 1 | True | True | A later-response requirement does not forbid overlap |

Each trace has eight Boolean samples. The final row was freshly added in this
package; it is not part of the historical four-scenario CI result. Values are
verdicts attributed to the trigger index, not a claim that the streaming
monitor emits the result at wall-clock time zero. The pinned native output
compresses adjacent equal verdicts; the retained decoder checks and expands
that representation.

## The consequential interpretation question

**Is the intended obligation bounded response timing, mutual exclusion of
BOOST and COAST phases, or both?**

The `[0,7]`/`[1,7]` separator can ask whether the same sample counts as a
response. Neither formula enforces mutual exclusion. Changing the lower
bound cannot alone establish a phase-nonoverlap requirement: the fifth trace
is a concrete counterexample to that stronger interpretation.

These are logical sample indices. Connecting the FRETish word “seconds” to
physical time additionally requires a justified sampling/time interpretation.
No real telemetry, mission owner acceptance, or deployment approval is present.

## Evidence boundary

This is a finite, source-native example, not an upstream defect in FRET or
R2U2, a full flight-system assessment, or a finding that their published
verification is unsound. There are four original scenarios and one additional
scenario, not 80 independent defects. Most later-index implication verdicts
have a false BOOST antecedent.

The local assessor is a separate program/process run by the same agent on the
same machine. It uses a separately written direct oracle and rebuilt native
monitor; it is not a new independent institution or human domain review.

An earlier equally informed interval-comparison baseline tied the MathGraph
witness search on the recorded finite task. This package does not rerun that
comparison and claims no discovery or cost advantage.

## Exact source and lineage

- FRET: [`cf0f913cc15c41705e803593297e89cd6056b839`](https://github.com/NASA-SW-VnV/fret/tree/cf0f913cc15c41705e803593297e89cd6056b839).
- R2U2/C2PO: [`2875a1dfc0b8cb27c4c4f14bece6b95c3afff91a`](https://github.com/R2U2/r2u2/tree/2875a1dfc0b8cb27c4c4f14bece6b95c3afff91a).
- Original MathGraph method: [`2b0e21e94e64ca54ff35c1d4572c60b3b6049720`](https://github.com/metalogiclabs/mathgraph/tree/2b0e21e94e64ca54ff35c1d4572c60b3b6049720/experiments/check-rocket-native-v1).
- Current source PR: [MathGraph #282](https://github.com/metalogiclabs/mathgraph/pull/282), observed open and draft on 22 November 2026.
- Historical source-qualified CI: [run 44611662927](https://github.com/metalogiclabs/mathgraph/actions/runs/44611662927), observed completed/success with two successful jobs at the exact method commit.

The retained method files are byte-identical to their source Git blobs.
`method-source-manifest.json` records Git blob and SHA-256 identities. The
new `reproduce.py` wrapper, local-context assessor wrapper and fifth scenario
belong to this package. FRET and R2U2 source is downloaded from the original
repositories at replay time, under those repositories’ own licensing terms;
it is not redistributed here. npm dependencies are pinned by the included
lockfile. The compact observed result is included; generated binaries and full run logs
are produced by the reproduction command and retained in the hosted artifact.

The historical run status in `evidence.json` is provider-reported metadata;
the historical artifact ZIPs were not downloaded and rehashed in this run.
The fresh local native build and replay has its own recorded outputs.
