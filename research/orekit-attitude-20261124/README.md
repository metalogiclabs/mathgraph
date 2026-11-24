# Orekit CCSDS attitude correspondence audit

Status: CANDIDATE until the native run and emitted receipts have been inspected.

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
