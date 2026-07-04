# finite_htilt_spectrum_coordinate_envelope_v1

Status: VERIFIED_PROOF

Lean file:

`examples/verifier_fixtures/lean/htilt_spectrum_coordinate_envelope.lean`

Verified declarations:

- `HTiltSpectrumCoordinateEnvelope.Coord`
- `HTiltSpectrumCoordinateEnvelope.shiftedSqMod`
- `HTiltSpectrumCoordinateEnvelope.residual`
- `HTiltSpectrumCoordinateEnvelope.ResidualEnvelope`
- `HTiltSpectrumCoordinateEnvelope.PositiveGapEnvelope`
- `HTiltSpectrumCoordinateEnvelope.shiftedSqMod_sub_eq`
- `HTiltSpectrumCoordinateEnvelope.shiftedSqMod_gt_of_bound`
- `HTiltSpectrumCoordinateEnvelope.shiftedSqMod_gt_for_all_coords_of_envelopes`
- `HTiltSpectrumCoordinateEnvelope.shiftedSqMod_gt_for_all_coords_of_explicit_c_envelopes`

## Claim

For a finite list of real coordinate pairs `(u,v)`, target coordinate `(a,b)`, residual envelope `B`, and positive-gap envelope `δ`:

If

`ResidualEnvelope a b B coords`,

`PositiveGapEnvelope a δ coords`,

`0 < δ`,

`0 <= c`,

and

`B / (2*δ) < c`,

then every coordinate in the list has strictly smaller shifted squared modulus:

`shiftedSqMod c u v < shiftedSqMod c a b`.

## Boundary

This artifact treats “spectrum” only as a finite list of coordinate pairs. It does not prove that the list is a matrix spectrum, does not extract eigenvalues, does not construct `B` or `δ` from spectral data, does not prove strict spectral abscissa, does not prove Perron-root alignment, and does not invoke Perron-Frobenius.
