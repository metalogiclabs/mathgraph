# AEM parser ignores ANGVEL_FRAME in angular-velocity conversion

## Summary

In Orekit 13.1.10, two otherwise identical AEM messages produce the same body-frame angular velocity when ANGVEL_FRAME changes between SC_BODY_1 and EME2000. The declared rate frame should change the required coordinate conversion.

This is independently reproduced using the published Maven Central 13.1.10 binary with Hipparchus 4.0.3. A separately source-pinned native matrix covers release-13.1 and develop; the development refactor reverses which rate-frame cases fail.

## Steps to reproduce

Use this synthetic AEM, first with ANGVEL_FRAME = SC_BODY_1, then change only that line to ANGVEL_FRAME = EME2000:

```text
CCSDS_AEM_VERS = 2.0
CREATION_DATE = 2023-01-01T00:00:00
ORIGINATOR = MATHGRAPH
META_START
OBJECT_NAME = SYNTHETIC
OBJECT_ID = 2023-001A
CENTER_NAME = EARTH
REF_FRAME_A = EME2000
REF_FRAME_B = SC_BODY_1
TIME_SYSTEM = TAI
START_TIME = 2023-01-01T00:00:00
STOP_TIME = 2023-01-01T00:00:01
ATTITUDE_TYPE = QUATERNION/ANGVEL
ANGVEL_FRAME = SC_BODY_1
META_STOP
DATA_START
2023-01-01T00:00:00 0 0 0.7071067811865476 0.7071067811865476 1 0 0
2023-01-01T00:00:01 0 0 0.7071067811865476 0.7071067811865476 1 0 0
DATA_STOP
```

After standard Orekit data initialization, parse with ParserBuilder.buildAemParser() and inspect the first segment's first AngularCoordinates.getRotationRate(). The standalone MinimalAemRate.java and checksum-pinned replay.py are included here: https://github.com/metalogiclabs/mathgraph/tree/experiment/orekit-attitude-20261124/research/orekit-attitude-20261124/minimal .

## Expected behavior

The scalar-last quaternion is a passive 90-degree Z rotation: external X maps to body -Y. The payload is (1,0,0) deg/s in the declared frame.

| ANGVEL_FRAME | Expected body rates, deg/s |
| --- | --- |
| SC_BODY_1 | (1, 0, 0) |
| EME2000 | (0, -1, 0) |

CCSDS 504.0-B-2 table 4-3 defines ANGVEL_FRAME; Annex F4 defines angular velocity and its component frame: https://ccsds.org/Pubs/504x0b2.pdf

## Actual behavior

Both messages return body rates (1,0,0) deg/s. The external-frame case differs from the expected vector by approximately 1.414213562373 deg/s; the body-frame case is a passing control. Orientations agree with the independent matrix.

## Environment

- Published Orekit 13.1.10 JAR from Maven Central, SHA-256 fa1bce7ce87ee53764597b139cd7f4cef0e6be851fd0e81878b4432853832f53.
- Hipparchus 4.0.3; all dependency JAR hashes and published checksum checks recorded.
- Local binary replay: Debian OpenJDK 21.0.13, ECJ 3.42.0 compilation to Java 8 bytecode.
- Source qualification: release-13.1 at cf611eab6b30a1fc2ccc7e6f2d1991e029b30568 (13.1.10) and develop at 48d3dad9619f7c5627f89c80878b3c1b2e1bd257 (14.0-SNAPSHOT), with their declared Hipparchus versions. These are independent source and binary checks; byte-for-byte build equivalence is not claimed.

## Additional context

AemMetadata stores angvelFrame but isSpacecraftBodyRate() does not consult it. The Optional migration at ff16b8c45d36e5608e0f245d9410a769975dd0db also reversed its former null-check predicate. Reverting that one line fixes the existing author body-rate fixture on develop, while leaving the external-frame cases wrong.

Native evidence and isolated patch/withdrawal controls: https://github.com/metalogiclabs/mathgraph/actions/runs/45348010765

All original CCSDS tests pass before and after the diagnostic rate repair: 523/523 on release and 506/506 on develop. In the selected native AEM matrix, rates are wrong in 192/384 cases on each branch: release fails the external-rate cases, while develop fails the body-rate cases. Independent orientation/derivative controls pass 1,536/1,536 on both.

The metadata-only diagnostic fixes every forward-direction parsed case while leaving reversed-direction discrepancies. A separate direction-only diagnostic fixes direct read/write conversion while leaving metadata-related parsing errors. The combined two-file rate repair clears all 384 parsed, 768 direct-read and 768 direct-write cases; withdrawing it restores the original results on each branch. That patch is a diagnostic for endpoint A/B rate frames, not a whole-project qualification or a solution for arbitrary third frames.

The actual 296-file native evidence ZIP was downloaded. Its uploaded SHA-256, ZIP integrity, all 295 manifest entries, native JUnit XML totals and per-case CSV data were independently verified. Artifact SHA-256: 1472b14a72212c4b475accd6eb73f75d6a57edf29e26496cf56b972a8cbc1eee.

Happy to contribute a focused fix and regression tests if useful. The reproduction is synthetic and offline. The investigation and draft were AI-assisted; native execution and independent matrix oracles supply the evidence.

The GitLab duplicate search could not be completed from this session; please point me to an existing report if this is known.

/label ~bug
