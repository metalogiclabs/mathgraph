# Orekit CCSDS attitude correspondence audit

Status: WARRANTED / FINITE_COUNTERMODEL within the boundary below. Native run and
the actual downloaded artifact have been independently inspected.

## Verified results

Primary run: https://github.com/metalogiclabs/mathgraph/actions/runs/45343425804
Experiment commit: `041bc021d5d28956cb786f5a2a431248f3270549`.
Artifact: `14896544461`, 40 files, ZIP SHA-256
`0287e676887f493f637a6d9336a5e6b34455914604a052fc2cea874ac0245d23`.
The ZIP digest, ZIP CRC integrity and all 39 manifest entries were checked after
download. Native JUnit XML and per-case CSV were read independently of the CI badge.

| Check | Upstream | Diagnostic repair | Repair withdrawn |
| --- | --- | --- | --- |
| Selected original author tests | 138/138 pass | 138/138 pass | Not repeated |
| Independent orientation/derivative controls | 1,536/1,536 pass | 1,536/1,536 pass | 1,536/1,536 pass |
| AEM parsed angular-velocity cases | 192/384 discrepant | 0/384 discrepant | 192/384 discrepant |
| Direct ANGVEL conversion cases | 384/768 discrepant | 0/768 discrepant | 384/768 discrepant |
| Author AEMExample14 body-rate witness | Fails | Passes | Fails |
| Valid default-direction endpoint compatibility | Two NPEs and one false result | Passes | Same failures |

All 384 parsed physical orientations were correct to the stated tolerance. All
192 body-frame-rate cases were discrepant; all 192 external-frame-rate controls
passed at this source. Direct conversion failures were the 384 reversed-direction
cases; forward-direction controls passed. These counts are bounded samples.

In the author's unchanged fourth AEMExample14 segment, expected body rates in
deg/s are `[-0.021029, 0.023643, 18.288407]`. Native output is approximately
`[-4.551055667, -6.310852590, 16.550766258]`: vector difference
`0.13926193220917846 rad/s` (about `7.979120962 deg/s`). The diagnostic patch
returns the expected vector exactly in this case.

Source observations: AemMetadata's rate-frame selection ignores ANGVEL_FRAME;
the Optional migration at `ff16b8c45d36e5608e0f245d9410a769975dd0db` changed
the former null check into isPresent, reversing that predicate. AttitudeType's
ANGVEL helpers additionally assume the message destination frame is the physical
body when the transformation is reversed. The diagnostic patch changes these
two mechanisms, plus the separate null-default endpoint compatibility API.
The patch is a causal diagnostic for this matrix, not a production-qualified fix.
The relative contribution of each patch hunk has not been isolated by ablation.

The endpoint exception is secondary: there is no internal isCompatibleWith caller
at this source. No AEM parser exception or operational failure is inferred from it.
No issue or merge request has been submitted. See ISSUE_DRAFT.md for the primary
rate-frame finding in the project's Java bug template.

Pin: CS-SI/Orekit `48d3dad9619f7c5627f89c80878b3c1b2e1bd257`.
Dependency: Hipparchus snapshot `5.0-20261122.181226-3`, selected by the pinned
Orekit POM's `5.0-SNAPSHOT` on 2026-11-24. The run fixes that timestamp and records
SHA-256 hashes of the actual JARs. Java 21, Maven; environment versions in artifact.

The independent oracle is CCSDS 504.0-B-2 Annex F1-F4:
https://ccsds.org/Pubs/504x0b2.pdf
Passive elementary matrices, Hamilton quaternion products and a five-point matrix
derivative are implemented directly. No Orekit Euler constructor/extractor is used
as the expected result. Both endpoint orders, rate frames, scalar positions, all 12
Euler sequences and four nondegenerate mixed-axis angle triples are exercised.
The author's unchanged AEMExample14 fixture provides an additional minimal witness.

The experiment runs original scoped tests, five probe tests, a diagnostic repair,
the author tests after repair, and a repair withdrawal. Native JUnit XML, per-case
CSV, complete logs, patch, dependency hashes and a file integrity manifest are
uploaded to Actions. A successful workflow is insufficient by itself: inspect the
native reports and phase counts. Generated evidence is not committed to this repo.

Claim boundaries: only the pinned source/dependencies and listed cases. No complete
Orekit qualification, released-version conclusion, operational effect, owner
confirmation or duplicate-free finding is established. The diagnostic rate-frame
repair covers frames matching endpoint A or B; arbitrary third-frame handling is
outside this experiment. The endpoint compatibility API has no internal caller at
this pin, so no internal processing failure is inferred from its exception.

Upstream norms: GitHub is a mirror. Reports and merge requests belong at
https://gitlab.orekit.org/orekit/orekit . Contributing instructions were read from
the pinned repository. Full issue-history access was blocked by the site's bot
gate in this session; duplication remains UNKNOWN. Nothing is submitted upstream
by this experiment.
