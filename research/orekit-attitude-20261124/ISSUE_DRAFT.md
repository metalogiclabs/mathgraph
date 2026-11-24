# AEM angular velocity vectors interpreted in the wrong frame

## Summary

At develop commit `48d3dad9619f7c5627f89c80878b3c1b2e1bd257`, parsing the
repository's own AEMExample14 fixture changes the body-frame angular velocity
vector even though its fourth segment explicitly declares `ANGVEL_FRAME = SC_BODY_1`.
The quaternion orientation is preserved; the rate vector is expressed incorrectly.

## Steps to reproduce

Add this test to AEMParserTest (which already configures the regular-data fixture):

```java
@Test
public void testDeclaredBodyAngularVelocity() {
    final String ex = "/ccsds/adm/aem/AEMExample14.txt";
    final Aem file = new ParserBuilder().buildAemParser().parseMessage(
            new DataSource(ex, () -> getClass().getResourceAsStream(ex)));
    final Vector3D expected = new Vector3D(Math.toRadians(-0.021029),
            Math.toRadians(0.023643), Math.toRadians(18.288407));
    final Vector3D actual = file.getSegments().get(3)
            .getAngularCoordinates().getFirst().getRotationRate();
    Assertions.assertEquals(0.0, expected.distance(actual), 1.0e-14);
}
```

The input is the unmodified fixture already in src/test/resources/ccsds/adm/aem.
The field order is scalar-last; frame A is EME2000 and frame B is SC_BODY_1.

## Expected behavior

The first body-frame rate vector should remain `[-0.021029, 0.023643, 18.288407]`
deg/s, with normal conversion to rad/s. CCSDS 504.0-B-2 table 4-3 and Annex F4
specify the role of ANGVEL_FRAME and the relative angular velocity:
https://ccsds.org/Pubs/504x0b2.pdf

## Actual behavior

The returned vector, converted back to deg/s, is approximately
`[-4.551055667, -6.310852590, 16.550766258]`. The vector error is
`0.13926193220917846 rad/s`. This matches treating the supplied body components as
external-frame components and applying the quaternion rotation to them.

## Environment

- Orekit: 14.0-SNAPSHOT, commit `48d3dad9619f7c5627f89c80878b3c1b2e1bd257`.
- Hipparchus: timestamped 5.0 snapshot `5.0-20261122.181226-3`, selected by
  the pinned POM's 5.0-SNAPSHOT; dependency JAR hashes are in the artifact.
- Java: Temurin 21.0.13+9.
- OS: ubuntu-24.04 Actions runner.
- Maven: 3.10.1.

## Additional context

All 138 selected original attitude/AEM/APM tests pass unchanged. Independent
elementary-matrix checks pass for 1,536 orientation/derivative controls, including
all 12 Euler sequences, both endpoint directions and quaternion scalar positions.
Additional native parsing reproduces wrong rates in 192/384 selected AEM cases,
covering QUATERNION/ANGVEL and EULER_ANGLE/ANGVEL. In that matrix all 192 body-frame
rate cases fail and all 192 external-frame controls pass; orientations remain correct.

AemMetadata.isSpacecraftBodyRate() does not consult angvelFrame. Its predicate
also changed from a null check to Optional.isPresent in
`ff16b8c45d36e5608e0f245d9410a769975dd0db`. Direct ANGVEL conversion separately
shows 384/768 discrepancies when the transformation is reversed. A diagnostic
patch addressing rate-frame selection and reversed-direction handling makes all
these selected cases pass, while retaining the 138 original passing tests.
Withdrawing the patch restores the discrepancies. These are scoped diagnostics,
not a complete-project qualification or a claim about released versions.

Reproduction code, native reports, per-case data, diagnostic patch and hashes:
https://github.com/metalogiclabs/mathgraph/actions/runs/45343425804

The actual 40-file evidence ZIP was downloaded and independently checked against
its uploaded SHA-256 and 39-entry file manifest. Happy to contribute a focused
fix and regression tests if useful.

I could not complete the GitLab duplicate search because the site denied this
session's automated access; please point me to an existing report if this is known.
This investigation and draft were AI-assisted; native execution and the stated
independent oracles provide the evidence.

/label ~bug
